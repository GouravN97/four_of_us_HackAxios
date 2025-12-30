"""
ICU API endpoints for ICU management and load prediction integration.
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.services.icu_service import ICUService
from src.utils.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icu", tags=["ICU"])


class ICUPatient(BaseModel):
    admission_id: str
    patient_id: str
    bed_number: Optional[str]
    admission_time: str
    risk_score_at_admission: float
    current_risk_score: Optional[float]
    current_risk_category: Optional[str]
    admission_reason: Optional[str]
    acuity_level: Optional[int]


class ICUCapacity(BaseModel):
    total_beds: int
    beds_occupied: int
    beds_available: int
    occupancy_percentage: float
    high_risk_patients: int
    timestamp: str


class OccupancyRecord(BaseModel):
    timestamp: str
    count: int
    beds_occupied: int
    beds_total: int
    high_risk_count: int
    new_admissions: int
    discharges: int


class AdmitPatientRequest(BaseModel):
    patient_id: str
    risk_score: float
    risk_category: str
    reason: Optional[str] = None


class DischargePatientRequest(BaseModel):
    patient_id: str


@router.get("/patients", response_model=List[ICUPatient])
async def get_icu_patients(db: Session = Depends(get_db)):
    """Get all patients currently in ICU."""
    try:
        icu_service = ICUService(db)
        patients = icu_service.get_current_icu_patients()
        return patients
    except Exception as e:
        logger.error(f"Error getting ICU patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity", response_model=ICUCapacity)
async def get_icu_capacity(db: Session = Depends(get_db)):
    """Get current ICU capacity metrics."""
    try:
        icu_service = ICUService(db)
        capacity = icu_service.get_icu_capacity()
        return capacity
    except Exception as e:
        logger.error(f"Error getting ICU capacity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/occupancy-history", response_model=List[OccupancyRecord])
async def get_occupancy_history(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get ICU occupancy history for load prediction.
    Returns hourly occupancy data for the specified number of hours.
    """
    try:
        icu_service = ICUService(db)
        history = icu_service.get_occupancy_history(hours=hours)
        return history
    except Exception as e:
        logger.error(f"Error getting occupancy history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admit")
async def admit_patient(
    request: AdmitPatientRequest,
    db: Session = Depends(get_db)
):
    """Manually admit a patient to ICU."""
    try:
        icu_service = ICUService(db)
        admission = icu_service.admit_patient(
            patient_id=request.patient_id,
            risk_score=request.risk_score,
            risk_category=request.risk_category,
            reason=request.reason
        )
        return {
            "success": True,
            "admission_id": admission.id,
            "patient_id": admission.patient_id,
            "bed_number": admission.bed_number,
            "message": f"Patient {request.patient_id} admitted to ICU"
        }
    except Exception as e:
        logger.error(f"Error admitting patient: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discharge")
async def discharge_patient(
    request: DischargePatientRequest,
    db: Session = Depends(get_db)
):
    """Discharge a patient from ICU."""
    try:
        icu_service = ICUService(db)
        admission = icu_service.discharge_patient(request.patient_id)
        if admission:
            return {
                "success": True,
                "patient_id": request.patient_id,
                "message": f"Patient {request.patient_id} discharged from ICU"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Patient {request.patient_id} not found in ICU")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discharging patient: {e}")
        raise HTTPException(status_code=500, detail=str(e))
