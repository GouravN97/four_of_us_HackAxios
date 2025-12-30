"""
Risk assessment service for business logic related to ML model integration.
Handles risk assessment calculations, model integration, and error handling.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.db_models import RiskAssessment, VitalSigns, Patient
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.repositories.patient_repository import PatientRepository
from src.utils.patient_risk_ml_client import (
    PatientRiskMLClient,
    PatientRiskMLError,
    ModelLoadError,
    ModelPredictionError
)
from src.utils.ml_client import (
    MLModelError,
    MLModelTimeoutError,
    MLModelValidationError,
    MLModelResponseError
)
from src.utils.error_handling import (
    handle_service_error,
    error_context,
    monitor_external_service,
    log_performance_warning,
    ErrorCategory,
    ErrorSeverity,
    global_error_handler
)

# Import ICU service for automatic admission
try:
    from src.services.icu_service import ICUService
    ICU_SERVICE_AVAILABLE = True
except ImportError:
    ICU_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)


class RiskAssessmentServiceError(Exception):
    """Base exception for risk assessment service errors."""
    pass


class PatientNotFoundError(RiskAssessmentServiceError):
    """Raised when a patient is not found."""
    pass


class VitalSignsNotFoundError(RiskAssessmentServiceError):
    """Raised when vital signs are not found."""
    pass


class ModelUnavailableError(RiskAssessmentServiceError):
    """Raised when the ML model is unavailable."""
    pass


class RiskAssessmentService:
    """
    Service for risk assessment business logic operations.
    
    Handles ML model integration, risk assessment calculations, and error handling.
    Implements Requirements 3.1, 3.2, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5.
    """
    
    # Maximum time allowed for risk assessment (Requirement 3.5)
    MAX_ASSESSMENT_TIME_SECONDS = 5
    
    # Expected input format for the Risk Model (Requirement 5.1)
    RISK_MODEL_INPUT_FORMAT = {
        "heart_rate": "float (30-200 bpm)",
        "systolic_bp": "float (50-300 mmHg)",
        "diastolic_bp": "float (20-200 mmHg)",
        "respiratory_rate": "float (5-60 breaths/min)",
        "oxygen_saturation": "float (50-100%)",
        "temperature": "float (30-45°C)",
        "arrival_mode": "string ('Ambulance' or 'Walk-in')",
        "acuity_level": "int (1-5)"
    }
    
    def __init__(self, db: Session, model_path: Optional[str] = None):
        """
        Initialize service with database session and ML model configuration.
        
        Args:
            db: SQLAlchemy database session
            model_path: Path to the ML model directory (defaults to ML_models/Patient_risk_classification)
        """
        self.db = db
        self.risk_repo = RiskAssessmentRepository(db)
        self.vital_signs_repo = VitalSignsRepository(db)
        self.patient_repo = PatientRepository(db)
        
        # Initialize Patient Risk ML model client
        try:
            self.ml_client = PatientRiskMLClient(model_path=model_path)
            logger.info(f"RiskAssessmentService initialized with Patient Risk ML model")
        except ModelLoadError as e:
            logger.error(f"Failed to load Patient Risk ML model: {e}")
            # Fall back to mock mode for development
            from src.utils.ml_client import RiskModelClient
            self.ml_client = RiskModelClient(model_endpoint=None)
            logger.warning("Falling back to mock ML client due to model load error")
    
    @handle_service_error(
        category=ErrorCategory.BUSINESS_LOGIC,
        severity=ErrorSeverity.MEDIUM,
        user_message="Failed to perform risk assessment"
    )
    def assess_risk_for_patient(self, patient_id: str, vital_signs_id: Optional[str] = None) -> RiskAssessment:
        """
        Perform risk assessment for a patient using their latest or specified vital signs.
        
        Args:
            patient_id: Patient identifier
            vital_signs_id: Specific vital signs record ID (uses latest if None)
            
        Returns:
            Created risk assessment record
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            VitalSignsNotFoundError: If vital signs are not found
            ModelUnavailableError: If ML model is unavailable
            RiskAssessmentServiceError: For other errors
        """
        with error_context(
            f"risk_assessment_for_patient_{patient_id}",
            ErrorCategory.BUSINESS_LOGIC,
            context={"patient_id": patient_id, "vital_signs_id": vital_signs_id}
        ):
            # Validate patient exists
            patient = self.patient_repo.get_by_id(patient_id)
            if not patient:
                raise PatientNotFoundError(f"Patient {patient_id} not found")
            
            # Get vital signs (latest or specific)
            if vital_signs_id:
                vital_signs = self.vital_signs_repo.get_by_id(vital_signs_id)
                if not vital_signs or vital_signs.patient_id != patient_id:
                    raise VitalSignsNotFoundError(f"Vital signs {vital_signs_id} not found for patient {patient_id}")
            else:
                vital_signs = self.vital_signs_repo.get_latest_for_patient(patient_id)
                if not vital_signs:
                    raise VitalSignsNotFoundError(f"No vital signs found for patient {patient_id}")
            
            # Perform risk assessment
            risk_assessment = self._perform_risk_assessment(patient, vital_signs)
            
            logger.info(f"Risk assessment completed for patient {patient_id}: "
                       f"score={risk_assessment.risk_score}, flag={risk_assessment.risk_flag}")
            
            return risk_assessment
    
    @handle_service_error(
        category=ErrorCategory.BUSINESS_LOGIC,
        severity=ErrorSeverity.MEDIUM,
        user_message="Failed to perform risk assessment for vital signs"
    )
    def assess_risk_for_vital_signs(self, vital_signs: VitalSigns) -> RiskAssessment:
        """
        Perform risk assessment for specific vital signs record.
        
        Args:
            vital_signs: Vital signs record
            
        Returns:
            Created risk assessment record
            
        Raises:
            PatientNotFoundError: If associated patient doesn't exist
            ModelUnavailableError: If ML model is unavailable
            RiskAssessmentServiceError: For other errors
        """
        with error_context(
            f"risk_assessment_for_vitals_{vital_signs.id}",
            ErrorCategory.BUSINESS_LOGIC,
            context={"vital_signs_id": str(vital_signs.id), "patient_id": vital_signs.patient_id}
        ):
            # Get patient information
            patient = self.patient_repo.get_by_id(vital_signs.patient_id)
            if not patient:
                raise PatientNotFoundError(f"Patient {vital_signs.patient_id} not found")
            
            # Perform risk assessment
            risk_assessment = self._perform_risk_assessment(patient, vital_signs)
            
            logger.info(f"Risk assessment completed for vital signs {vital_signs.id}: "
                       f"score={risk_assessment.risk_score}, flag={risk_assessment.risk_flag}")
            
            return risk_assessment
    
    @handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.LOW,
        user_message="Failed to retrieve risk assessment"
    )
    def get_latest_risk_assessment(self, patient_id: str) -> Optional[RiskAssessment]:
        """
        Get the most recent risk assessment for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest risk assessment record if found, None otherwise
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            RiskAssessmentServiceError: For other errors
        """
        # Validate patient exists
        if not self.patient_repo.exists(patient_id):
            raise PatientNotFoundError(f"Patient {patient_id} not found")
        
        risk_assessment = self.risk_repo.get_latest_for_patient(patient_id)
        
        if risk_assessment:
            logger.debug(f"Retrieved latest risk assessment for patient {patient_id}")
        else:
            logger.debug(f"No risk assessments found for patient {patient_id}")
        
        return risk_assessment
    
    @handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.LOW,
        user_message="Failed to retrieve risk assessment history"
    )
    def get_risk_assessment_history(self, patient_id: str, limit: Optional[int] = None) -> List[RiskAssessment]:
        """
        Get risk assessment history for a patient.
        
        Args:
            patient_id: Patient identifier
            limit: Maximum number of records to return
            
        Returns:
            List of risk assessment records in chronological order (newest first)
            
        Raises:
            PatientNotFoundError: If patient doesn't exist
            RiskAssessmentServiceError: For other errors
        """
        # Validate patient exists
        if not self.patient_repo.exists(patient_id):
            raise PatientNotFoundError(f"Patient {patient_id} not found")
        
        assessments = self.risk_repo.get_for_patient(patient_id, limit=limit)
        
        logger.debug(f"Retrieved {len(assessments)} risk assessments for patient {patient_id}")
        return assessments
    
    @handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.LOW,
        user_message="Failed to retrieve high-risk patients"
    )
    def get_high_risk_patients(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of patient IDs who are currently flagged as high risk.
        
        Args:
            limit: Maximum number of patient IDs to return
            
        Returns:
            List of patient IDs with high risk flags
            
        Raises:
            RiskAssessmentServiceError: For database errors
        """
        patient_ids = self.risk_repo.get_high_risk_patients(limit=limit)
        
        logger.debug(f"Found {len(patient_ids)} high-risk patients")
        return patient_ids
    
    @handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.LOW,
        user_message="Failed to retrieve patients by risk range"
    )
    def get_patients_by_risk_range(self, min_score: float, max_score: float,
                                  limit: Optional[int] = None) -> List[str]:
        """
        Get patient IDs whose latest risk scores fall within a specified range.
        
        Args:
            min_score: Minimum risk score (0.0-1.0)
            max_score: Maximum risk score (0.0-1.0)
            limit: Maximum number of patient IDs to return
            
        Returns:
            List of patient IDs with risk scores in the specified range
            
        Raises:
            ValueError: If score range is invalid
            RiskAssessmentServiceError: For database errors
        """
        if not (0.0 <= min_score <= 1.0) or not (0.0 <= max_score <= 1.0):
            raise ValueError("Risk scores must be between 0.0 and 1.0")
        
        if min_score > max_score:
            raise ValueError("Minimum score cannot be greater than maximum score")
        
        patient_ids = self.risk_repo.get_patients_by_risk_score_range(min_score, max_score, limit=limit)
        
        logger.debug(f"Found {len(patient_ids)} patients with risk scores between {min_score} and {max_score}")
        return patient_ids
    
    @handle_service_error(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.LOW,
        user_message="Failed to retrieve assessment statistics"
    )
    def get_assessment_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about risk assessments.
        
        Returns:
            Dictionary with assessment statistics
            
        Raises:
            RiskAssessmentServiceError: For database errors
        """
        stats = self.risk_repo.get_assessment_statistics()
        
        logger.debug(f"Retrieved assessment statistics: {stats}")
        return stats
    
    def check_model_health(self) -> Dict[str, Any]:
        """
        Check the health status of the ML model.
        
        Returns:
            Dictionary with model health information
        """
        try:
            health_status = self.ml_client.health_check()
            
            logger.debug(f"ML model health check: {health_status}")
            return health_status
            
        except Exception as e:
            # Handle model health check errors gracefully
            global_error_handler.handle_error(
                exception=e,
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "model_health_check"},
                user_message="ML model health check failed"
            )
            
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_model_input_format(self) -> Dict[str, str]:
        """
        Get the expected input format for the Risk Model.
        
        Implements Requirement 5.1: THE Patient_Risk_System SHALL interface with 
        the Risk_Model using the specified input format.
        
        Returns:
            Dictionary describing the expected input format
        """
        return self.RISK_MODEL_INPUT_FORMAT.copy()
    
    def validate_model_inputs(self, heart_rate: float, systolic_bp: float, 
                             diastolic_bp: float, respiratory_rate: float,
                             oxygen_saturation: float, temperature: float,
                             arrival_mode: str, acuity_level: int) -> Dict[str, Any]:
        """
        Validate inputs before sending to the Risk Model.
        
        Implements Requirement 5.4: THE Patient_Risk_System SHALL validate that 
        Risk_Model inputs are within expected ranges before processing.
        
        Args:
            heart_rate: Heart rate in bpm
            systolic_bp: Systolic blood pressure in mmHg
            diastolic_bp: Diastolic blood pressure in mmHg
            respiratory_rate: Respiratory rate in breaths/min
            oxygen_saturation: Oxygen saturation percentage
            temperature: Body temperature in Celsius
            arrival_mode: Patient arrival mode
            acuity_level: Clinical severity rating
            
        Returns:
            Dictionary with validation result:
            - valid: bool indicating if all inputs are valid
            - errors: list of validation error messages (empty if valid)
            - warnings: list of warning messages for edge cases
        """
        errors = []
        warnings = []
        
        # Validate vital signs ranges
        if not (30 <= heart_rate <= 200):
            errors.append(f"Heart rate must be between 30-200 bpm, got {heart_rate}")
        elif heart_rate > 150 or heart_rate < 50:
            warnings.append(f"Heart rate {heart_rate} is in critical range")
        
        if not (50 <= systolic_bp <= 300):
            errors.append(f"Systolic BP must be between 50-300 mmHg, got {systolic_bp}")
        elif systolic_bp > 180 or systolic_bp < 80:
            warnings.append(f"Systolic BP {systolic_bp} is in critical range")
        
        if not (20 <= diastolic_bp <= 200):
            errors.append(f"Diastolic BP must be between 20-200 mmHg, got {diastolic_bp}")
        elif diastolic_bp > 120 or diastolic_bp < 50:
            warnings.append(f"Diastolic BP {diastolic_bp} is in critical range")
        
        if not (5 <= respiratory_rate <= 60):
            errors.append(f"Respiratory rate must be between 5-60 breaths/min, got {respiratory_rate}")
        elif respiratory_rate > 30 or respiratory_rate < 10:
            warnings.append(f"Respiratory rate {respiratory_rate} is in critical range")
        
        if not (50 <= oxygen_saturation <= 100):
            errors.append(f"Oxygen saturation must be between 50-100%, got {oxygen_saturation}")
        elif oxygen_saturation < 90:
            warnings.append(f"Oxygen saturation {oxygen_saturation}% is critically low")
        
        if not (30 <= temperature <= 45):
            errors.append(f"Temperature must be between 30-45°C, got {temperature}")
        elif temperature > 39 or temperature < 35:
            warnings.append(f"Temperature {temperature}°C is in critical range")
        
        # Validate blood pressure relationship
        if diastolic_bp >= systolic_bp:
            errors.append(f"Diastolic BP ({diastolic_bp}) must be less than systolic BP ({systolic_bp})")
        
        # Validate arrival mode
        if arrival_mode not in ["Ambulance", "Walk-in"]:
            errors.append(f"Arrival mode must be 'Ambulance' or 'Walk-in', got '{arrival_mode}'")
        
        # Validate acuity level
        if not (1 <= acuity_level <= 5):
            errors.append(f"Acuity level must be between 1-5, got {acuity_level}")
        elif acuity_level >= 4:
            warnings.append(f"High acuity level {acuity_level} indicates critical patient")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def prepare_model_input(self, patient: Patient, vital_signs: VitalSigns) -> Dict[str, Any]:
        """
        Prepare and validate input data for the Risk Model.
        
        Implements Requirements 5.1 and 5.4: Interface with Risk_Model using 
        specified input format and validate inputs before processing.
        
        Args:
            patient: Patient record
            vital_signs: Vital signs record
            
        Returns:
            Dictionary with model input data in the correct format
            
        Raises:
            MLModelValidationError: If input validation fails
        """
        # Prepare input in the specified format (Requirement 5.1)
        model_input = {
            "heart_rate": vital_signs.heart_rate,
            "systolic_bp": vital_signs.systolic_bp,
            "diastolic_bp": vital_signs.diastolic_bp,
            "respiratory_rate": vital_signs.respiratory_rate,
            "oxygen_saturation": vital_signs.oxygen_saturation,
            "temperature": vital_signs.temperature,
            "arrival_mode": patient.arrival_mode.value,
            "acuity_level": patient.acuity_level
        }
        
        # Validate inputs before processing (Requirement 5.4)
        validation_result = self.validate_model_inputs(**model_input)
        
        if not validation_result["valid"]:
            error_msg = "Model input validation failed: " + "; ".join(validation_result["errors"])
            logger.error(error_msg)
            raise MLModelValidationError(error_msg)
        
        # Log warnings for critical values
        for warning in validation_result["warnings"]:
            logger.warning(f"Patient {patient.patient_id}: {warning}")
        
        return model_input
    
    @monitor_external_service("ml_risk_model", timeout_seconds=5.0, retry_attempts=2)
    def _perform_risk_assessment(self, patient: Patient, vital_signs: VitalSigns) -> RiskAssessment:
        """
        Perform the actual risk assessment using the ML model.
        
        Implements Requirements:
        - 3.1: Invoke Risk_Model with current vital signs, arrival mode, and acuity level
        - 3.2: Store both numerical risk score and boolean risk flag
        - 3.4: Log error and maintain previous risk status on failure
        - 5.2: Extract risk score and risk flag from response
        - 5.3: Handle Risk_Model errors gracefully
        - 5.5: Log issue and continue storing vital signs when model unavailable
        
        Args:
            patient: Patient record
            vital_signs: Vital signs record
            
        Returns:
            Created risk assessment record
            
        Raises:
            ModelUnavailableError: If ML model is unavailable
            RiskAssessmentServiceError: For other errors
        """
        assessment_time = datetime.utcnow()
        error_message = None
        risk_score = 0.0
        risk_flag = False
        processing_time_ms = 0
        model_available = True
        
        try:
            # Prepare and validate model input (Requirements 5.1, 5.4)
            model_input = self.prepare_model_input(patient, vital_signs)
            
            # Call ML model for prediction (Requirement 3.1)
            if hasattr(self.ml_client, 'predict_risk') and callable(getattr(self.ml_client, 'predict_risk')):
                # Use Patient Risk ML Client
                risk_score, risk_category, processing_time_ms = self.ml_client.predict_risk(
                    **model_input
                )
                # Convert risk category to boolean flag for backward compatibility
                risk_flag = risk_category == "HIGH"
            else:
                # Fallback to old ML client (returns different format)
                risk_score_normalized, risk_flag, processing_time_ms = self.ml_client.predict_risk(
                    **model_input
                )
                # Convert normalized score (0-1) to percentage (0-100)
                risk_score = risk_score_normalized * 100
                # Map to risk category
                if risk_score < 45:
                    risk_category = "LOW"
                elif risk_score < 65:
                    risk_category = "MODERATE"
                else:
                    risk_category = "HIGH"
            
            # Extract risk score and flag from response (Requirement 5.2)
            logger.debug(f"ML model prediction successful: score={risk_score}, category={risk_category}, "
                        f"flag={risk_flag}, time={processing_time_ms}ms")
            
            # Log performance warning if assessment took too long (Requirement 3.5)
            log_performance_warning(
                f"risk_assessment_patient_{patient.patient_id}",
                processing_time_ms / 1000.0,  # Convert to seconds
                self.MAX_ASSESSMENT_TIME_SECONDS,
                {"patient_id": patient.patient_id, "vital_signs_id": str(vital_signs.id)}
            )
            
        except (PatientRiskMLError, ModelPredictionError) as e:
            # Requirement 5.5: Log issue when model unavailable
            error_message = f"Patient Risk ML model error: {str(e)}"
            logger.error(error_message)
            model_available = False
            # Requirement 3.4: Use fallback to maintain risk status
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
            
        except MLModelTimeoutError as e:
            # Requirement 5.5: Log issue when model unavailable
            error_message = f"ML model timeout: {str(e)}"
            logger.error(error_message)
            model_available = False
            # Requirement 3.4: Use fallback to maintain risk status
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
            
        except MLModelValidationError as e:
            # Requirement 5.4: Input validation failed
            error_message = f"ML model input validation failed: {str(e)}"
            logger.error(error_message)
            # Use fallback risk assessment
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
            
        except MLModelResponseError as e:
            # Requirement 5.3: Handle model errors gracefully
            error_message = f"ML model response error: {str(e)}"
            logger.error(error_message)
            model_available = False
            # Use fallback risk assessment
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
            
        except MLModelError as e:
            # Requirement 5.3: Handle model errors gracefully
            # Requirement 5.5: Log issue and continue
            error_message = f"ML model error: {str(e)}"
            logger.error(error_message)
            model_available = False
            # Use fallback risk assessment
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
            
        except Exception as e:
            # Requirement 5.3: Handle unexpected errors gracefully
            error_message = f"Unexpected error during ML model prediction: {str(e)}"
            logger.error(error_message)
            model_available = False
            # Use fallback risk assessment
            risk_score, risk_flag = self._fallback_risk_assessment(patient, vital_signs)
            risk_category = "HIGH" if risk_flag else ("MODERATE" if risk_score > 50 else "LOW")
        
        # Log model availability status (Requirement 5.5)
        if not model_available:
            logger.warning(f"ML model unavailable for patient {patient.patient_id}, "
                          f"using fallback assessment. Vital signs data preserved.")
        
        # Create risk assessment record (Requirement 3.2: Store risk score and flag)
        try:
            risk_assessment = self.risk_repo.create(
                patient_id=patient.patient_id,
                vital_signs_id=vital_signs.id,
                risk_score=risk_score,
                risk_category=risk_category,
                risk_flag=risk_flag,
                assessment_time=assessment_time,
                model_version=getattr(self.ml_client, 'model_version', 'v1.0.0'),
                processing_time_ms=processing_time_ms,
                error_message=error_message
            )
            
            return risk_assessment
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating risk assessment: {e}")
            raise RiskAssessmentServiceError(f"Failed to store risk assessment: {str(e)}") from e
        
        finally:
            # Check if patient should be admitted to ICU (HIGH risk)
            if ICU_SERVICE_AVAILABLE and risk_category == "HIGH":
                try:
                    icu_service = ICUService(self.db)
                    icu_service.check_and_admit_high_risk(
                        patient_id=patient.patient_id,
                        risk_score=risk_score,
                        risk_category=risk_category
                    )
                except Exception as e:
                    logger.warning(f"Failed to check ICU admission for patient {patient.patient_id}: {e}")
    
    def _fallback_risk_assessment(self, patient: Patient, vital_signs: VitalSigns) -> tuple[float, bool]:
        """
        Provide fallback risk assessment when ML model is unavailable.
        
        Args:
            patient: Patient record
            vital_signs: Vital signs record
            
        Returns:
            Tuple of (risk_score, risk_flag) - risk_score is 0-100 scale
        """
        logger.warning(f"Using fallback risk assessment for patient {patient.patient_id}")
        
        # Simple rule-based fallback based on acuity level and vital signs
        risk_score = 0.0
        
        # Base risk from acuity level (converted to 0-100 scale)
        acuity_risk = {
            1: 10.0,
            2: 20.0,
            3: 40.0,
            4: 60.0,
            5: 80.0
        }
        risk_score += acuity_risk.get(patient.acuity_level, 50.0)
        
        # Additional risk from abnormal vital signs
        if vital_signs.heart_rate > 100 or vital_signs.heart_rate < 60:
            risk_score += 10.0
        
        if vital_signs.systolic_bp > 140 or vital_signs.systolic_bp < 90:
            risk_score += 10.0
        
        if vital_signs.oxygen_saturation < 95:
            risk_score += 20.0
        
        if vital_signs.temperature > 38.0 or vital_signs.temperature < 36.0:
            risk_score += 10.0
        
        if vital_signs.respiratory_rate > 20 or vital_signs.respiratory_rate < 12:
            risk_score += 10.0
        
        # Ambulance arrival adds risk
        if patient.arrival_mode.value == "Ambulance":
            risk_score += 10.0
        
        # Clamp to valid range (0-100)
        risk_score = min(100.0, max(0.0, risk_score))
        
        # Risk flag if score > 50 or acuity >= 4
        risk_flag = risk_score > 50.0 or patient.acuity_level >= 4
        
        logger.debug(f"Fallback risk assessment: score={risk_score}, flag={risk_flag}")
        
        return risk_score, risk_flag