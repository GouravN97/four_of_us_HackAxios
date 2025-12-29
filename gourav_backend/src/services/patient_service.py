"""
Patient service for business logic related to patient registration and management.
Handles patient registration, validation, and coordination with risk assessment.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.api_models import PatientRegistration, PatientStatus, ArrivalMode
from src.models.db_models import Patient, ArrivalModeEnum, VitalSigns
from src.repositories.patient_repository import PatientRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.repositories.risk_assessment_repository import RiskAssessmentRepository

logger = logging.getLogger(__name__)


class PatientServiceError(Exception):
    """Base exception for patient service errors."""
    pass


class PatientNotFoundError(PatientServiceError):
    """Raised when a patient is not found."""
    pass


class PatientAlreadyExistsError(PatientServiceError):
    """Raised when attempting to register a patient that already exists."""
    pass


class ValidationError(PatientServiceError):
    """Raised when patient data validation fails."""
    pass


class PatientService:
    """Service for patient business logic operations."""
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.vital_signs_repo = VitalSignsRepository(db)
        self.risk_assessment_repo = RiskAssessmentRepository(db)
    
    def register_patient(self, registration_data: PatientRegistration) -> Patient:
        """
        Register a new patient with initial vital signs.
        
        This method handles the complete patient registration process:
        1. Validates patient data and business rules
        2. Creates patient record
        3. Stores initial vital signs
        4. Triggers initial risk assessment (handled by RiskAssessmentService)
        
        Args:
            registration_data: Patient registration information
            
        Returns:
            Created patient record
            
        Raises:
            PatientAlreadyExistsError: If patient ID already exists
            ValidationError: If registration data is invalid
            PatientServiceError: For other business logic errors
        """
        try:
            # Validate business rules
            self._validate_registration_data(registration_data)
            
            # Check if patient already exists
            if self.patient_repo.exists(registration_data.patient_id):
                raise PatientAlreadyExistsError(
                    f"Patient with ID {registration_data.patient_id} already exists"
                )
            
            # Convert API model arrival mode to database enum
            arrival_mode_enum = self._convert_arrival_mode(registration_data.arrival_mode)
            
            # Create patient record
            patient = self.patient_repo.create(
                patient_id=registration_data.patient_id,
                arrival_mode=arrival_mode_enum,
                acuity_level=registration_data.acuity_level
            )
            
            # Store initial vital signs
            initial_vitals = self.vital_signs_repo.create(
                patient_id=patient.patient_id,
                heart_rate=registration_data.initial_vitals.heart_rate,
                systolic_bp=registration_data.initial_vitals.systolic_bp,
                diastolic_bp=registration_data.initial_vitals.diastolic_bp,
                respiratory_rate=registration_data.initial_vitals.respiratory_rate,
                oxygen_saturation=registration_data.initial_vitals.oxygen_saturation,
                temperature=registration_data.initial_vitals.temperature,
                timestamp=registration_data.initial_vitals.timestamp,
                recorded_by="REGISTRATION_SYSTEM"
            )
            
            logger.info(f"Successfully registered patient {patient.patient_id} with initial vitals")
            
            # Note: Risk assessment will be triggered by RiskAssessmentService
            # when it detects new vital signs (Requirements 1.3)
            
            return patient
            
        except IntegrityError as e:
            logger.error(f"Database integrity error during patient registration: {e}")
            raise PatientAlreadyExistsError(
                f"Patient with ID {registration_data.patient_id} already exists"
            ) from e
        except SQLAlchemyError as e:
            logger.error(f"Database error during patient registration: {e}")
            raise PatientServiceError(f"Failed to register patient: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during patient registration: {e}")
            raise PatientServiceError(f"Failed to register patient: {str(e)}") from e
    
    def get_patient_status(self, patient_id: str) -> PatientStatus:
        """
        Get current status of a patient including latest vitals and risk assessment.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Current patient status
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            PatientServiceError: For other errors
        """
        try:
            # Get patient record
            patient = self.patient_repo.get_by_id(patient_id)
            if not patient:
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            # Get latest vital signs
            latest_vitals = self.vital_signs_repo.get_latest_for_patient(patient_id)
            if not latest_vitals:
                raise PatientServiceError(f"No vital signs found for patient {patient_id}")
            
            # Get latest risk assessment
            latest_risk = self.risk_assessment_repo.get_latest_for_patient(patient_id)
            if not latest_risk:
                raise PatientServiceError(f"No risk assessment found for patient {patient_id}")
            
            # Convert to API models
            arrival_mode_api = self._convert_arrival_mode_to_api(patient.arrival_mode)
            
            # Build patient status response
            patient_status = PatientStatus(
                patient_id=patient.patient_id,
                arrival_mode=arrival_mode_api,
                acuity_level=patient.acuity_level,
                current_vitals={
                    "heart_rate": latest_vitals.heart_rate,
                    "systolic_bp": latest_vitals.systolic_bp,
                    "diastolic_bp": latest_vitals.diastolic_bp,
                    "respiratory_rate": latest_vitals.respiratory_rate,
                    "oxygen_saturation": latest_vitals.oxygen_saturation,
                    "temperature": latest_vitals.temperature,
                    "timestamp": latest_vitals.timestamp
                },
                current_risk={
                    "risk_score": latest_risk.risk_score,
                    "risk_flag": latest_risk.risk_flag,
                    "assessment_time": latest_risk.assessment_time,
                    "model_version": latest_risk.model_version
                },
                registration_time=patient.registration_time,
                last_updated=patient.last_updated
            )
            
            logger.debug(f"Retrieved patient status for {patient_id}")
            return patient_status
            
        except PatientNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patient status for {patient_id}: {e}")
            raise PatientServiceError(f"Failed to retrieve patient status: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error retrieving patient status for {patient_id}: {e}")
            raise PatientServiceError(f"Failed to retrieve patient status: {str(e)}") from e
    
    def patient_exists(self, patient_id: str) -> bool:
        """
        Check if a patient exists in the system.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if patient exists, False otherwise
        """
        try:
            return self.patient_repo.exists(patient_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error checking patient existence for {patient_id}: {e}")
            raise PatientServiceError(f"Failed to check patient existence: {str(e)}") from e
    
    def update_patient_last_updated(self, patient_id: str) -> bool:
        """
        Update the last_updated timestamp for a patient.
        
        This is typically called when vital signs are updated to maintain
        accurate tracking of when patient data was last modified.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if updated successfully, False if patient not found
            
        Raises:
            PatientServiceError: For database errors
        """
        try:
            return self.patient_repo.update_last_updated(patient_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error updating last_updated for {patient_id}: {e}")
            raise PatientServiceError(f"Failed to update patient timestamp: {str(e)}") from e
    
    def _validate_registration_data(self, registration_data: PatientRegistration) -> None:
        """
        Validate patient registration data according to business rules.
        
        Args:
            registration_data: Patient registration information
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate patient ID format (basic validation)
        if not registration_data.patient_id.strip():
            raise ValidationError("Patient ID cannot be empty")
        
        if len(registration_data.patient_id) > 50:
            raise ValidationError("Patient ID cannot exceed 50 characters")
        
        # Validate acuity level
        if not (1 <= registration_data.acuity_level <= 5):
            raise ValidationError(f"Acuity level must be between 1 and 5, got {registration_data.acuity_level}")
        
        # Validate initial vitals timestamp is not in the future
        if registration_data.initial_vitals.timestamp > datetime.utcnow():
            raise ValidationError("Initial vitals timestamp cannot be in the future")
        
        # Additional business rule: High acuity patients (4-5) arriving by walk-in should be flagged
        if (registration_data.acuity_level >= 4 and 
            registration_data.arrival_mode == ArrivalMode.WALK_IN):
            logger.warning(
                f"High acuity patient {registration_data.patient_id} (level {registration_data.acuity_level}) "
                f"arrived by walk-in - may need immediate attention"
            )
        
        logger.debug(f"Registration data validation passed for patient {registration_data.patient_id}")
    
    def _convert_arrival_mode(self, arrival_mode: ArrivalMode) -> ArrivalModeEnum:
        """
        Convert API arrival mode to database enum.
        
        Args:
            arrival_mode: API arrival mode
            
        Returns:
            Database arrival mode enum
        """
        if arrival_mode == ArrivalMode.AMBULANCE:
            return ArrivalModeEnum.AMBULANCE
        elif arrival_mode == ArrivalMode.WALK_IN:
            return ArrivalModeEnum.WALK_IN
        else:
            raise ValidationError(f"Invalid arrival mode: {arrival_mode}")
    
    def _convert_arrival_mode_to_api(self, arrival_mode: ArrivalModeEnum) -> ArrivalMode:
        """
        Convert database arrival mode enum to API model.
        
        Args:
            arrival_mode: Database arrival mode enum
            
        Returns:
            API arrival mode
        """
        if arrival_mode == ArrivalModeEnum.AMBULANCE:
            return ArrivalMode.AMBULANCE
        elif arrival_mode == ArrivalModeEnum.WALK_IN:
            return ArrivalMode.WALK_IN
        else:
            raise ValidationError(f"Invalid database arrival mode: {arrival_mode}")