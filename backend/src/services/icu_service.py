"""
ICU Service for managing ICU admissions and occupancy tracking.
Automatically admits HIGH risk patients to ICU.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.db_models import Patient, RiskAssessment, RiskCategoryEnum
from src.models.icu_models import ICUAdmission, ICUOccupancyLog, ICUAdmissionStatus

logger = logging.getLogger(__name__)


class ICUService:
    """Service for ICU admission and occupancy management."""
    
    TOTAL_ICU_BEDS = 15
    
    def __init__(self, db: Session):
        self.db = db
    
    def admit_patient(self, patient_id: str, risk_score: float, risk_category: str,
                     reason: Optional[str] = None) -> ICUAdmission:
        """
        Admit a patient to ICU.
        
        Args:
            patient_id: Patient identifier
            risk_score: Current risk score
            risk_category: Current risk category
            reason: Optional admission reason
            
        Returns:
            Created ICU admission record
        """
        # Check if patient is already admitted
        existing = self.db.query(ICUAdmission).filter(
            ICUAdmission.patient_id == patient_id,
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).first()
        
        if existing:
            logger.info(f"Patient {patient_id} already admitted to ICU")
            return existing
        
        # Assign bed number
        bed_number = self._get_next_available_bed()
        
        # Create admission record
        admission = ICUAdmission(
            id=str(uuid4()),
            patient_id=patient_id,
            admission_time=datetime.utcnow(),
            status=ICUAdmissionStatus.ADMITTED.value,
            risk_score_at_admission=risk_score,
            risk_category_at_admission=risk_category,
            bed_number=bed_number,
            admission_reason=reason or f"High risk classification (score: {risk_score:.1f})"
        )
        
        self.db.add(admission)
        self.db.commit()
        
        logger.info(f"Patient {patient_id} admitted to ICU, bed {bed_number}")
        
        # Update occupancy log
        self._log_occupancy_change(new_admissions=1)
        
        return admission
    
    def discharge_patient(self, patient_id: str) -> Optional[ICUAdmission]:
        """Discharge a patient from ICU."""
        admission = self.db.query(ICUAdmission).filter(
            ICUAdmission.patient_id == patient_id,
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).first()
        
        if not admission:
            logger.warning(f"Patient {patient_id} not found in ICU")
            return None
        
        admission.status = ICUAdmissionStatus.DISCHARGED.value
        admission.discharge_time = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Patient {patient_id} discharged from ICU")
        
        # Update occupancy log
        self._log_occupancy_change(discharges=1)
        
        return admission
    
    def check_and_admit_high_risk(self, patient_id: str, risk_score: float, 
                                   risk_category: str) -> Optional[ICUAdmission]:
        """
        Check if patient should be admitted to ICU based on risk.
        Automatically admits patients with HIGH risk classification.
        
        Args:
            patient_id: Patient identifier
            risk_score: Current risk score
            risk_category: Current risk category (LOW/MODERATE/HIGH)
            
        Returns:
            ICU admission record if admitted, None otherwise
        """
        if risk_category == "HIGH":
            logger.info(f"Patient {patient_id} has HIGH risk, admitting to ICU")
            return self.admit_patient(
                patient_id=patient_id,
                risk_score=risk_score,
                risk_category=risk_category,
                reason=f"Automatic admission due to HIGH risk classification (score: {risk_score:.1f})"
            )
        return None
    
    def get_current_icu_patients(self) -> List[Dict[str, Any]]:
        """Get list of all patients currently in ICU."""
        admissions = self.db.query(ICUAdmission).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).order_by(ICUAdmission.admission_time.desc()).all()
        
        result = []
        for admission in admissions:
            # Get patient info
            patient = self.db.query(Patient).filter(
                Patient.patient_id == admission.patient_id
            ).first()
            
            # Get latest risk assessment
            latest_risk = self.db.query(RiskAssessment).filter(
                RiskAssessment.patient_id == admission.patient_id
            ).order_by(RiskAssessment.assessment_time.desc()).first()
            
            result.append({
                "admission_id": admission.id,
                "patient_id": admission.patient_id,
                "bed_number": admission.bed_number,
                "admission_time": admission.admission_time.isoformat(),
                "risk_score_at_admission": admission.risk_score_at_admission,
                "current_risk_score": latest_risk.risk_score if latest_risk else None,
                "current_risk_category": latest_risk.risk_category.value if latest_risk else None,
                "admission_reason": admission.admission_reason,
                "acuity_level": patient.acuity_level if patient else None,
            })
        
        return result
    
    def get_icu_capacity(self) -> Dict[str, Any]:
        """Get current ICU capacity metrics."""
        occupied = self.db.query(ICUAdmission).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).count()
        
        high_risk_count = self.db.query(ICUAdmission).join(
            RiskAssessment, ICUAdmission.patient_id == RiskAssessment.patient_id
        ).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value,
            RiskAssessment.risk_category == RiskCategoryEnum.HIGH
        ).distinct(ICUAdmission.patient_id).count()
        
        return {
            "total_beds": self.TOTAL_ICU_BEDS,
            "beds_occupied": occupied,
            "beds_available": self.TOTAL_ICU_BEDS - occupied,
            "occupancy_percentage": round((occupied / self.TOTAL_ICU_BEDS) * 100, 2),
            "high_risk_patients": high_risk_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_occupancy_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get ICU occupancy history for load prediction.
        
        Args:
            hours: Number of hours of history to retrieve
            
        Returns:
            List of hourly occupancy records
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        logs = self.db.query(ICUOccupancyLog).filter(
            ICUOccupancyLog.timestamp >= start_time
        ).order_by(ICUOccupancyLog.timestamp.asc()).all()
        
        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "count": log.patient_count,
                "beds_occupied": log.beds_occupied,
                "beds_total": log.beds_total,
                "high_risk_count": log.high_risk_count,
                "new_admissions": log.new_admissions,
                "discharges": log.discharges
            }
            for log in logs
        ]
    
    def _get_next_available_bed(self) -> str:
        """Get next available ICU bed number."""
        occupied_beds = self.db.query(ICUAdmission.bed_number).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).all()
        occupied_set = {b[0] for b in occupied_beds if b[0]}
        
        for i in range(1, self.TOTAL_ICU_BEDS + 1):
            bed = f"ICU-{i:02d}"
            if bed not in occupied_set:
                return bed
        
        return f"ICU-OVERFLOW-{len(occupied_set) + 1}"
    
    def _log_occupancy_change(self, new_admissions: int = 0, discharges: int = 0):
        """Log current occupancy state."""
        # Get current hour (truncated)
        now = datetime.utcnow()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Check if we already have a log for this hour
        existing = self.db.query(ICUOccupancyLog).filter(
            ICUOccupancyLog.timestamp == current_hour
        ).first()
        
        # Get current counts
        patient_count = self.db.query(ICUAdmission).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value
        ).count()
        
        high_risk = self.db.query(ICUAdmission).filter(
            ICUAdmission.status == ICUAdmissionStatus.ADMITTED.value,
            ICUAdmission.risk_category_at_admission == RiskCategoryEnum.HIGH.value
        ).count()
        
        if existing:
            existing.patient_count = patient_count
            existing.beds_occupied = patient_count
            existing.high_risk_count = high_risk
            existing.new_admissions += new_admissions
            existing.discharges += discharges
        else:
            log = ICUOccupancyLog(
                id=str(uuid4()),
                timestamp=current_hour,
                patient_count=patient_count,
                beds_total=self.TOTAL_ICU_BEDS,
                beds_occupied=patient_count,
                high_risk_count=high_risk,
                new_admissions=new_admissions,
                discharges=discharges
            )
            self.db.add(log)
        
        self.db.commit()
