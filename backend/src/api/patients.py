"""
Patient API controller for patient registration and status endpoints.
Implements REST endpoints for patient management.

Requirements covered:
- 1.1: Patient registration with ID, arrival mode, and acuity level
- 1.2: Initial vital signs validation and storage
- 1.3: Initial risk assessment generation
- 4.1: Current patient status retrieval
- 4.3: Risk-based patient queries
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.models.api_models import (
    ArrivalMode,
    ErrorResponse,
    HighRiskPatient,
    HighRiskPatientsResponse,
    PatientRegistration,
    PatientStatus,
    RiskAssessment,
    VitalSignsWithTimestamp,
)
from src.models.db_models import ArrivalModeEnum
from src.repositories.patient_repository import PatientRepository
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.services.patient_service import (
    PatientAlreadyExistsError,
    PatientNotFoundError,
    PatientService,
    PatientServiceError,
    ValidationError,
)
from src.services.risk_assessment_service import (
    RiskAssessmentService,
    RiskAssessmentServiceError,
)
from src.utils.database import get_db
from src.utils.validation import validate_patient_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


def _convert_arrival_mode_to_api(arrival_mode: ArrivalModeEnum) -> ArrivalMode:
    """Convert database arrival mode enum to API model."""
    if arrival_mode == ArrivalModeEnum.AMBULANCE:
        return ArrivalMode.AMBULANCE
    elif arrival_mode == ArrivalModeEnum.WALK_IN:
        return ArrivalMode.WALK_IN
    else:
        raise ValueError(f"Invalid database arrival mode: {arrival_mode}")


@router.post(
    "",
    response_model=PatientStatus,
    status_code=201,
    responses={
        201: {"description": "Patient registered successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "Patient already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Register a new patient",
    description="""
    Register a new patient with initial vital signs and clinical information.
    
    This endpoint:
    - Validates patient data and vital signs against medical ranges
    - Creates patient record with unique identifier
    - Stores initial vital signs with timestamp
    - Automatically triggers initial risk assessment using ML model
    
    **Requirements:** 1.1, 1.2, 1.3
    """,
)
async def register_patient(
    registration: PatientRegistration,
    db: Session = Depends(get_db),
) -> PatientStatus:
    """
    Register a new patient with initial vital signs.
    
    Args:
        registration: Patient registration data including vital signs
        db: Database session
        
    Returns:
        Current patient status including risk assessment
        
    Raises:
        HTTPException: 400 for validation errors, 409 for duplicate patient
    """
    try:
        # Initialize services
        patient_service = PatientService(db)
        risk_service = RiskAssessmentService(db)
        vital_signs_repo = VitalSignsRepository(db)
        risk_repo = RiskAssessmentRepository(db)
        
        # Register patient (creates patient record and stores initial vitals)
        patient = patient_service.register_patient(registration)
        
        # Get the initial vital signs that were just stored
        latest_vitals = vital_signs_repo.get_latest_for_patient(patient.patient_id)
        
        # Trigger initial risk assessment (Requirement 1.3)
        risk_assessment = risk_service.assess_risk_for_patient(patient.patient_id)
        
        # Build response
        arrival_mode_api = _convert_arrival_mode_to_api(patient.arrival_mode)
        
        response = PatientStatus(
            patient_id=patient.patient_id,
            arrival_mode=arrival_mode_api,
            acuity_level=patient.acuity_level,
            current_vitals=VitalSignsWithTimestamp(
                heart_rate=latest_vitals.heart_rate,
                systolic_bp=latest_vitals.systolic_bp,
                diastolic_bp=latest_vitals.diastolic_bp,
                respiratory_rate=latest_vitals.respiratory_rate,
                oxygen_saturation=latest_vitals.oxygen_saturation,
                temperature=latest_vitals.temperature,
                timestamp=latest_vitals.timestamp,
            ),
            current_risk=RiskAssessment(
                risk_score=risk_assessment.risk_score,
                risk_category=risk_assessment.risk_category,
                risk_flag=risk_assessment.risk_flag,
                assessment_time=risk_assessment.assessment_time,
                model_version=risk_assessment.model_version,
            ),
            registration_time=patient.registration_time,
            last_updated=patient.last_updated,
        )
        
        logger.info(f"Patient {patient.patient_id} registered successfully")
        return response
        
    except PatientAlreadyExistsError as e:
        logger.warning(f"Patient registration failed - already exists: {e}")
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(f"Patient registration failed - validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except PatientServiceError as e:
        logger.error(f"Patient registration failed - service error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to register patient. Please try again later.",
        )
    except RiskAssessmentServiceError as e:
        logger.error(f"Risk assessment failed during registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Patient registered but risk assessment failed. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during patient registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


# NOTE: Static routes must be defined BEFORE /{patient_id} to avoid route conflicts

@router.get(
    "/all",
    responses={
        200: {"description": "All patient IDs retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get all patient IDs",
    description="Get a list of all registered patient IDs in the system.",
)
async def get_all_patient_ids(
    db: Session = Depends(get_db),
):
    """Get all patient IDs."""
    try:
        patient_repo = PatientRepository(db)
        patients = patient_repo.get_all()
        return {
            "patient_ids": [p.patient_id for p in patients],
            "total_count": len(patients),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting all patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/high-risk",
    response_model=HighRiskPatientsResponse,
    responses={
        200: {"description": "High-risk patients retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get high-risk patients",
    description="""
    Query patients who are currently flagged as high risk based on their latest risk assessment.
    
    This endpoint returns:
    - List of patients with high risk flags
    - Current risk scores and assessment times
    - Patient demographic information
    
    Optional parameters allow filtering by minimum risk score and limiting results.
    
    **Requirements:** 4.3
    """,
)
async def get_high_risk_patients(
    min_risk_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum risk score filter (0.0-1.0)",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=1000,
        description="Maximum number of patients to return",
    ),
    db: Session = Depends(get_db),
) -> HighRiskPatientsResponse:
    """
    Get list of high-risk patients.
    
    Args:
        min_risk_score: Optional minimum risk score filter
        limit: Optional maximum number of results
        db: Database session
        
    Returns:
        List of high-risk patients with their current risk information
    """
    try:
        risk_service = RiskAssessmentService(db)
        patient_repo = PatientRepository(db)
        risk_repo = RiskAssessmentRepository(db)
        
        # Get high-risk patient IDs
        if min_risk_score is not None:
            # Filter by risk score range
            patient_ids = risk_service.get_patients_by_risk_range(
                min_score=min_risk_score,
                max_score=1.0,
                limit=limit,
            )
        else:
            # Get all patients with high risk flag
            patient_ids = risk_service.get_high_risk_patients(limit=limit)
        
        # Build response with patient details
        high_risk_patients = []
        for patient_id in patient_ids:
            patient = patient_repo.get_by_id(patient_id)
            if patient:
                latest_risk = risk_repo.get_latest_for_patient(patient_id)
                if latest_risk:
                    arrival_mode_api = _convert_arrival_mode_to_api(patient.arrival_mode)
                    
                    high_risk_patients.append(
                        HighRiskPatient(
                            patient_id=patient.patient_id,
                            arrival_mode=arrival_mode_api,
                            acuity_level=patient.acuity_level,
                            current_risk_score=latest_risk.risk_score,
                            last_assessment_time=latest_risk.assessment_time,
                            registration_time=patient.registration_time,
                        )
                    )
        
        response = HighRiskPatientsResponse(
            patients=high_risk_patients,
            total_count=len(high_risk_patients),
            query_time=datetime.utcnow(),
        )
        
        logger.info(f"Retrieved {len(high_risk_patients)} high-risk patients")
        return response
        
    except ValueError as e:
        logger.warning(f"Invalid parameters for high-risk query: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except RiskAssessmentServiceError as e:
        logger.error(f"Error retrieving high-risk patients: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve high-risk patients. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving high-risk patients: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/{patient_id}",
    response_model=PatientStatus,
    responses={
        200: {"description": "Patient status retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid patient ID format"},
        404: {"model": ErrorResponse, "description": "Patient not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get current patient status",
    description="""
    Retrieve the current status of a patient including latest vital signs and risk assessment.
    
    This endpoint returns:
    - Patient demographic information (arrival mode, acuity level)
    - Most recent vital signs with timestamp
    - Most recent risk assessment (score and flag)
    - Registration and last update timestamps
    
    **Requirements:** 4.1
    """,
)
async def get_patient_status(
    patient_id: str,
    db: Session = Depends(get_db),
) -> PatientStatus:
    """
    Get current status of a patient.
    
    Args:
        patient_id: Unique patient identifier
        db: Database session
        
    Returns:
        Current patient status including latest vitals and risk assessment
        
    Raises:
        HTTPException: 400 for invalid patient ID, 404 if patient not found
    """
    try:
        # Validate and sanitize patient ID (Requirement 6.2, 6.4)
        try:
            sanitized_patient_id = validate_patient_id(patient_id)
        except ValueError as e:
            logger.warning(f"Invalid patient ID format: {patient_id} - {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid patient ID format: {str(e)}",
            )
        
        patient_service = PatientService(db)
        
        # Get patient status (includes latest vitals and risk assessment)
        status = patient_service.get_patient_status(sanitized_patient_id)
        
        logger.debug(f"Retrieved status for patient {sanitized_patient_id}")
        return status
        
    except PatientNotFoundError as e:
        logger.warning(f"Patient not found: {sanitized_patient_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Patient {sanitized_patient_id} not found",
        )
    except PatientServiceError as e:
        logger.error(f"Error retrieving patient status for {sanitized_patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve patient status. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving patient status for {patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )
