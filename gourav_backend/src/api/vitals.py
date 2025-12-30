"""
Vital signs API controller for vital signs update and historical data endpoints.
Implements REST endpoints for vital signs management.

Requirements covered:
- 2.1: Vital signs validation against acceptable medical ranges
- 2.2: Vital signs storage with timestamps
- 2.3: Automatic risk assessment trigger on vital signs update
- 4.2: Historical data retrieval with time-ordered results
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.models.api_models import (
    ErrorResponse,
    HistoricalDataPoint,
    HistoricalDataResponse,
    RiskAssessment,
    SuccessResponse,
    VitalSignsUpdate,
    VitalSignsWithTimestamp,
)
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.services.risk_assessment_service import (
    RiskAssessmentService,
    RiskAssessmentServiceError,
)
from src.services.vital_signs_service import (
    PatientNotFoundError,
    ValidationError,
    VitalSignsService,
    VitalSignsServiceError,
)
from src.utils.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Vital Signs"])


@router.put(
    "/{patient_id}/vitals",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Vital signs updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid vital signs data"},
        404: {"model": ErrorResponse, "description": "Patient not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Update patient vital signs",
    description="""
    Update vital signs for an existing patient.
    
    This endpoint:
    - Validates vital signs against medical ranges
    - Stores new vital signs with timestamp
    - Automatically triggers risk assessment using ML model
    - Updates patient last_updated timestamp
    
    **Requirements:** 2.1, 2.2, 2.3
    """,
)
async def update_vital_signs(
    patient_id: str,
    vital_signs: VitalSignsUpdate,
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """
    Update vital signs for a patient.
    
    Args:
        patient_id: Unique patient identifier
        vital_signs: New vital signs measurements
        db: Database session
        
    Returns:
        Success response with confirmation message
        
    Raises:
        HTTPException: 404 if patient not found, 400 for validation errors
    """
    try:
        # Initialize services
        vital_signs_service = VitalSignsService(db)
        risk_service = RiskAssessmentService(db)
        
        # Update vital signs (Requirement 2.1, 2.2)
        vital_signs_record = vital_signs_service.update_vital_signs(
            patient_id=patient_id,
            vital_signs_data=vital_signs,
            recorded_by="API"
        )
        
        # Trigger risk assessment (Requirement 2.3)
        try:
            risk_assessment = risk_service.assess_risk_for_patient(patient_id)
            logger.info(
                f"Vital signs updated and risk assessed for patient {patient_id}: "
                f"risk_score={risk_assessment.risk_score}, risk_flag={risk_assessment.risk_flag}"
            )
        except RiskAssessmentServiceError as e:
            # Log error but don't fail the vital signs update
            logger.error(f"Risk assessment failed after vital signs update for patient {patient_id}: {e}")
            # Continue - vital signs were successfully stored
        
        response = SuccessResponse(
            success=True,
            message=f"Vital signs updated successfully for patient {patient_id}",
            data={
                "patient_id": patient_id,
                "vital_signs_id": vital_signs_record.id,
                "timestamp": vital_signs_record.timestamp.isoformat(),
            }
        )
        
        logger.info(f"Successfully updated vital signs for patient {patient_id}")
        return response
        
    except PatientNotFoundError as e:
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found",
        )
    except ValidationError as e:
        logger.warning(f"Vital signs validation failed for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except VitalSignsServiceError as e:
        logger.error(f"Error updating vital signs for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update vital signs. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error updating vital signs for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/{patient_id}/history",
    response_model=HistoricalDataResponse,
    responses={
        200: {"description": "Historical data retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        404: {"model": ErrorResponse, "description": "Patient not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get patient historical data",
    description="""
    Retrieve historical vital signs and risk assessments for a patient.
    
    This endpoint returns:
    - Time-ordered vital signs measurements
    - Corresponding risk assessments
    - Data within specified time range (optional)
    
    Results are returned in chronological order (oldest first) for time-series analysis.
    
    **Requirements:** 4.2
    """,
)
async def get_patient_history(
    patient_id: str,
    start_time: Optional[datetime] = Query(
        None,
        description="Start of time range (ISO 8601 format)",
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="End of time range (ISO 8601 format)",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=1000,
        description="Maximum number of data points to return",
    ),
    db: Session = Depends(get_db),
) -> HistoricalDataResponse:
    """
    Get historical vital signs and risk assessment data for a patient.
    
    Args:
        patient_id: Unique patient identifier
        start_time: Optional start of time range
        end_time: Optional end of time range
        limit: Optional maximum number of data points
        db: Database session
        
    Returns:
        Historical data response with chronologically ordered data points
        
    Raises:
        HTTPException: 404 if patient not found, 400 for invalid parameters
    """
    try:
        # Initialize services and repositories
        vital_signs_service = VitalSignsService(db)
        vital_signs_repo = VitalSignsRepository(db)
        risk_repo = RiskAssessmentRepository(db)
        
        # Validate time range parameters
        if start_time and end_time:
            if start_time >= end_time:
                raise HTTPException(
                    status_code=400,
                    detail="Start time must be before end time",
                )
        
        # Get vital signs history (Requirement 4.2)
        if start_time and end_time:
            vital_signs_list = vital_signs_service.get_vital_signs_history(
                patient_id=patient_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        else:
            vital_signs_list = vital_signs_service.get_vital_signs_history(
                patient_id=patient_id,
                limit=limit
            )
        
        # Build historical data points with corresponding risk assessments
        data_points = []
        for vitals in vital_signs_list:
            # Find the risk assessment closest to this vital signs timestamp
            # In practice, there should be a risk assessment for each vital signs record
            risk_assessments = risk_repo.get_for_patient_in_time_range(
                patient_id=patient_id,
                start_time=vitals.timestamp,
                end_time=vitals.timestamp
            )
            
            # If no exact match, get the next assessment after this timestamp
            if not risk_assessments:
                all_assessments = risk_repo.get_for_patient(patient_id)
                risk_assessment = None
                for assessment in reversed(all_assessments):  # Oldest first
                    if assessment.assessment_time >= vitals.timestamp:
                        risk_assessment = assessment
                        break
            else:
                risk_assessment = risk_assessments[0]
            
            # Only include data points that have both vitals and risk assessment
            if risk_assessment:
                data_point = HistoricalDataPoint(
                    vitals=VitalSignsWithTimestamp(
                        heart_rate=vitals.heart_rate,
                        systolic_bp=vitals.systolic_bp,
                        diastolic_bp=vitals.diastolic_bp,
                        respiratory_rate=vitals.respiratory_rate,
                        oxygen_saturation=vitals.oxygen_saturation,
                        temperature=vitals.temperature,
                        timestamp=vitals.timestamp,
                    ),
                    risk_assessment=RiskAssessment(
                        risk_score=risk_assessment.risk_score,
                        risk_flag=risk_assessment.risk_flag,
                        assessment_time=risk_assessment.assessment_time,
                        model_version=risk_assessment.model_version,
                    ),
                )
                data_points.append(data_point)
        
        # Determine actual time range from data
        if data_points:
            actual_start = data_points[0].vitals.timestamp
            actual_end = data_points[-1].vitals.timestamp
        else:
            # Use provided times or default to current time
            actual_start = start_time or datetime.utcnow()
            actual_end = end_time or datetime.utcnow()
        
        response = HistoricalDataResponse(
            patient_id=patient_id,
            start_time=actual_start,
            end_time=actual_end,
            data_points=data_points,
            total_count=len(data_points),
        )
        
        logger.info(f"Retrieved {len(data_points)} historical data points for patient {patient_id}")
        return response
        
    except PatientNotFoundError as e:
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found",
        )
    except ValidationError as e:
        logger.warning(f"Invalid parameters for history query: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except VitalSignsServiceError as e:
        logger.error(f"Error retrieving history for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve patient history. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving history for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        )
