"""
Vital signs service for business logic related to vital signs management.
Handles vital signs updates, validation, and coordination with risk assessment.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.api_models import VitalSignsUpdate, VitalSignsWithTimestamp
from src.models.db_models import VitalSigns
from src.repositories.patient_repository import PatientRepository
from src.repositories.vital_signs_repository import VitalSignsRepository

logger = logging.getLogger(__name__)


class VitalSignsServiceError(Exception):
    """Base exception for vital signs service errors."""
    pass


class PatientNotFoundError(VitalSignsServiceError):
    """Raised when a patient is not found."""
    pass


class ValidationError(VitalSignsServiceError):
    """Raised when vital signs data validation fails."""
    pass


class VitalSignsService:
    """Service for vital signs business logic operations."""
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.vital_signs_repo = VitalSignsRepository(db)
        self.patient_repo = PatientRepository(db)
    
    def update_vital_signs(self, patient_id: str, vital_signs_data: VitalSignsUpdate,
                          recorded_by: Optional[str] = None) -> VitalSigns:
        """
        Update vital signs for an existing patient.
        
        This method handles the complete vital signs update process:
        1. Validates patient exists
        2. Validates vital signs data and business rules
        3. Stores new vital signs record
        4. Updates patient last_updated timestamp
        5. Triggers risk assessment (handled by RiskAssessmentService)
        
        Args:
            patient_id: Patient identifier
            vital_signs_data: New vital signs measurements
            recorded_by: Who recorded the vital signs (optional)
            
        Returns:
            Created vital signs record
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            ValidationError: If vital signs data is invalid
            VitalSignsServiceError: For other business logic errors
        """
        try:
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            # Validate vital signs data
            self._validate_vital_signs_data(vital_signs_data)
            
            # Check for business rule violations
            self._validate_business_rules(patient_id, vital_signs_data)
            
            # Create new vital signs record with current timestamp (timezone-naive for consistency)
            current_time = datetime.utcnow()
            vital_signs = self.vital_signs_repo.create(
                patient_id=patient_id,
                heart_rate=vital_signs_data.heart_rate,
                systolic_bp=vital_signs_data.systolic_bp,
                diastolic_bp=vital_signs_data.diastolic_bp,
                respiratory_rate=vital_signs_data.respiratory_rate,
                oxygen_saturation=vital_signs_data.oxygen_saturation,
                temperature=vital_signs_data.temperature,
                timestamp=current_time,
                recorded_by=recorded_by or "SYSTEM"
            )
            
            # Update patient last_updated timestamp
            self.patient_repo.update_last_updated(patient_id)
            
            logger.info(f"Successfully updated vital signs for patient {patient_id}")
            
            # Note: Risk assessment will be triggered by RiskAssessmentService
            # when it detects new vital signs (Requirements 2.3)
            
            return vital_signs
            
        except PatientNotFoundError:
            raise
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error updating vital signs for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to update vital signs: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error updating vital signs for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to update vital signs: {str(e)}") from e
    
    def get_latest_vital_signs(self, patient_id: str) -> Optional[VitalSigns]:
        """
        Get the most recent vital signs for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest vital signs record if found, None otherwise
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            VitalSignsServiceError: For other errors
        """
        try:
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            vital_signs = self.vital_signs_repo.get_latest_for_patient(patient_id)
            
            if vital_signs:
                logger.debug(f"Retrieved latest vital signs for patient {patient_id}")
            else:
                logger.debug(f"No vital signs found for patient {patient_id}")
            
            return vital_signs
            
        except PatientNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving latest vital signs for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to retrieve vital signs: {str(e)}") from e
    
    def get_vital_signs_history(self, patient_id: str, start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None, limit: Optional[int] = None) -> List[VitalSigns]:
        """
        Get historical vital signs for a patient.
        
        Args:
            patient_id: Patient identifier
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            limit: Maximum number of records to return (optional)
            
        Returns:
            List of vital signs records in chronological order
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            ValidationError: If time range is invalid
            VitalSignsServiceError: For other errors
        """
        try:
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            # Validate time range
            if start_time and end_time and start_time >= end_time:
                raise ValidationError("Start time must be before end time")
            
            # Get vital signs based on parameters
            if start_time and end_time:
                vital_signs_list = self.vital_signs_repo.get_for_patient_in_time_range(
                    patient_id, start_time, end_time
                )
            else:
                vital_signs_list = self.vital_signs_repo.get_for_patient(
                    patient_id, limit=limit
                )
                # Reverse to get chronological order (oldest first)
                vital_signs_list.reverse()
            
            logger.debug(f"Retrieved {len(vital_signs_list)} vital signs records for patient {patient_id}")
            return vital_signs_list
            
        except PatientNotFoundError:
            raise
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving vital signs history for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to retrieve vital signs history: {str(e)}") from e
    
    def get_recent_vital_signs(self, patient_id: str, hours: int = 24) -> List[VitalSigns]:
        """
        Get recent vital signs for a patient within the last N hours.
        
        Args:
            patient_id: Patient identifier
            hours: Number of hours to look back (default 24)
            
        Returns:
            List of vital signs records in chronological order
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            ValidationError: If hours parameter is invalid
            VitalSignsServiceError: For other errors
        """
        try:
            # Validate parameters
            if hours <= 0:
                raise ValidationError("Hours must be a positive number")
            
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            vital_signs_list = self.vital_signs_repo.get_recent_for_patient(patient_id, hours)
            
            logger.debug(f"Retrieved {len(vital_signs_list)} recent vital signs for patient {patient_id}")
            return vital_signs_list
            
        except PatientNotFoundError:
            raise
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving recent vital signs for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to retrieve recent vital signs: {str(e)}") from e
    
    def get_vital_signs_count(self, patient_id: str) -> int:
        """
        Get count of vital signs records for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Number of vital signs records
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            VitalSignsServiceError: For other errors
        """
        try:
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            count = self.vital_signs_repo.get_count_for_patient(patient_id)
            
            logger.debug(f"Patient {patient_id} has {count} vital signs records")
            return count
            
        except PatientNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error counting vital signs for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to count vital signs: {str(e)}") from e
    
    def get_vital_signs_time_range(self, patient_id: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the time range (earliest to latest) of vital signs for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Tuple of (earliest_timestamp, latest_timestamp) or None if no records
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            VitalSignsServiceError: For other errors
        """
        try:
            # Validate patient exists
            if not self.patient_repo.exists(patient_id):
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            time_range = self.vital_signs_repo.get_time_range_for_patient(patient_id)
            
            if time_range:
                logger.debug(f"Patient {patient_id} vital signs range: {time_range[0]} to {time_range[1]}")
            else:
                logger.debug(f"No vital signs time range found for patient {patient_id}")
            
            return time_range
            
        except PatientNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting vital signs time range for patient {patient_id}: {e}")
            raise VitalSignsServiceError(f"Failed to get vital signs time range: {str(e)}") from e
    
    def _validate_vital_signs_data(self, vital_signs_data: VitalSignsUpdate) -> None:
        """
        Validate vital signs data according to business rules.
        
        Args:
            vital_signs_data: Vital signs data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Pydantic already handles basic range validation, but we can add
        # additional business rule validation here
        
        # Additional validation: Check for physiologically impossible combinations
        if vital_signs_data.heart_rate > 180 and vital_signs_data.temperature < 35:
            logger.warning("Unusual combination: very high heart rate with low temperature")
        
        if vital_signs_data.oxygen_saturation < 70 and vital_signs_data.respiratory_rate < 10:
            logger.warning("Critical combination: very low oxygen saturation with low respiratory rate")
        
        # Additional validation: Check blood pressure relationship
        # (This is also validated in Pydantic model, but we double-check here)
        if vital_signs_data.diastolic_bp >= vital_signs_data.systolic_bp:
            raise ValidationError(
                "Diastolic blood pressure must be less than systolic blood pressure"
            )
        
        logger.debug("Vital signs data validation passed")
    
    def _validate_business_rules(self, patient_id: str, vital_signs_data: VitalSignsUpdate) -> None:
        """
        Validate business rules for vital signs updates.
        
        Args:
            patient_id: Patient identifier
            vital_signs_data: Vital signs data to validate
            
        Raises:
            ValidationError: If business rules are violated
        """
        try:
            # Business rule: Check for rapid changes in vital signs
            latest_vitals = self.vital_signs_repo.get_latest_for_patient(patient_id)
            
            if latest_vitals:
                # Check for extreme changes that might indicate data entry errors
                heart_rate_change = abs(vital_signs_data.heart_rate - latest_vitals.heart_rate)
                if heart_rate_change > 50:
                    logger.warning(
                        f"Large heart rate change for patient {patient_id}: "
                        f"{latest_vitals.heart_rate} -> {vital_signs_data.heart_rate}"
                    )
                
                systolic_change = abs(vital_signs_data.systolic_bp - latest_vitals.systolic_bp)
                if systolic_change > 40:
                    logger.warning(
                        f"Large systolic BP change for patient {patient_id}: "
                        f"{latest_vitals.systolic_bp} -> {vital_signs_data.systolic_bp}"
                    )
                
                temp_change = abs(vital_signs_data.temperature - latest_vitals.temperature)
                if temp_change > 3.0:
                    logger.warning(
                        f"Large temperature change for patient {patient_id}: "
                        f"{latest_vitals.temperature} -> {vital_signs_data.temperature}"
                    )
            
            # Business rule: Prevent duplicate entries within short time window
            recent_vitals = self.vital_signs_repo.get_recent_for_patient(patient_id, hours=1)
            if recent_vitals:
                # Check if there's a very recent entry with identical values
                for recent in recent_vitals[-3:]:  # Check last 3 entries
                    if (recent.heart_rate == vital_signs_data.heart_rate and
                        recent.systolic_bp == vital_signs_data.systolic_bp and
                        recent.diastolic_bp == vital_signs_data.diastolic_bp and
                        recent.respiratory_rate == vital_signs_data.respiratory_rate and
                        recent.oxygen_saturation == vital_signs_data.oxygen_saturation and
                        recent.temperature == vital_signs_data.temperature):
                        
                        time_diff = datetime.utcnow() - recent.timestamp
                        if time_diff.total_seconds() < 300:  # 5 minutes
                            logger.warning(
                                f"Potential duplicate vital signs entry for patient {patient_id} "
                                f"within {time_diff.total_seconds()} seconds"
                            )
            
            logger.debug(f"Business rules validation passed for patient {patient_id}")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during business rules validation for patient {patient_id}: {e}")
            # Don't fail the update for validation database errors, just log
            pass