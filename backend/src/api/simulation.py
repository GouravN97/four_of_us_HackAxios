"""
Simulation API for time-synchronized data updates.
Manages simulated time where 1 real minute = 5 simulated minutes.
Starts from latest data in DB and continues generating new vitals.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.utils.database import get_db
from src.repositories.patient_repository import PatientRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.models.db_models import Patient, VitalSigns, RiskAssessment, ArrivalModeEnum, RiskCategoryEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["Simulation"])

# Global simulation state
class SimulationState:
    def __init__(self):
        self.start_real_time: Optional[datetime] = None
        self.start_sim_time: Optional[datetime] = None  # Latest timestamp from DB when started
        self.current_sim_time: Optional[datetime] = None
        self.is_running: bool = False
        self.time_scale: float = 5.0  # 5 min sim = 60 sec real -> 5x
        self.last_vitals_update: Optional[datetime] = None
    
    def get_simulated_time(self) -> datetime:
        """Get current simulated time based on real elapsed time since start."""
        if not self.is_running or not self.start_real_time or not self.start_sim_time:
            return self.current_sim_time or datetime.utcnow()
        
        real_elapsed = (datetime.utcnow() - self.start_real_time).total_seconds()
        sim_elapsed = real_elapsed * self.time_scale
        self.current_sim_time = self.start_sim_time + timedelta(seconds=sim_elapsed)
        return self.current_sim_time
    
    def should_update_vitals(self) -> bool:
        """Check if 60 real seconds have passed (generates 5 sim minutes of data)."""
        if not self.is_running:
            return False
        if not self.last_vitals_update:
            return True
        
        real_elapsed = (datetime.utcnow() - self.last_vitals_update).total_seconds()
        return real_elapsed >= 60.0  # 60 real seconds = 5 sim minutes

simulation_state = SimulationState()


class SimulationStartRequest(BaseModel):
    pass  # No parameters needed - starts from latest DB data


class SimulationTimeResponse(BaseModel):
    simulated_time: str
    real_time: str
    is_running: bool
    time_scale: float
    sim_minutes_elapsed: float


def generate_vitals_variation(base_vitals: Dict[str, float], risk_level: str) -> Dict[str, float]:
    """Generate slight variations in vitals based on risk level."""
    variation_range = {
        'HIGH': 0.08,
        'MODERATE': 0.05,
        'LOW': 0.03
    }
    var = variation_range.get(risk_level, 0.05)
    
    return {
        'heart_rate': max(40, min(180, base_vitals['heart_rate'] * (1 + random.uniform(-var, var)))),
        'systolic_bp': max(70, min(220, base_vitals['systolic_bp'] * (1 + random.uniform(-var, var)))),
        'diastolic_bp': max(40, min(140, base_vitals['diastolic_bp'] * (1 + random.uniform(-var, var)))),
        'respiratory_rate': max(8, min(40, base_vitals['respiratory_rate'] * (1 + random.uniform(-var, var)))),
        'oxygen_saturation': max(70, min(100, base_vitals['oxygen_saturation'] * (1 + random.uniform(-var/2, var/2)))),
        'temperature': max(35, min(41, base_vitals['temperature'] + random.uniform(-0.3, 0.3))),
    }


def calculate_risk_from_vitals(vitals: Dict[str, float], acuity: int, arrival_ambulance: bool) -> tuple:
    """Calculate risk score and category from vitals."""
    score = 0
    
    if vitals['oxygen_saturation'] < 88:
        score += 25
    elif vitals['oxygen_saturation'] < 92:
        score += 15
    elif vitals['oxygen_saturation'] < 95:
        score += 5
    
    if vitals['systolic_bp'] < 90 or vitals['systolic_bp'] > 180:
        score += 15
    elif vitals['systolic_bp'] < 100 or vitals['systolic_bp'] > 160:
        score += 8
    
    if vitals['heart_rate'] > 120 or vitals['heart_rate'] < 50:
        score += 12
    elif vitals['heart_rate'] > 100 or vitals['heart_rate'] < 60:
        score += 5
    
    if vitals['respiratory_rate'] > 24:
        score += 10
    elif vitals['respiratory_rate'] > 20:
        score += 5
    
    if vitals['temperature'] > 39 or vitals['temperature'] < 35.5:
        score += 10
    elif vitals['temperature'] > 38:
        score += 5
    
    if acuity >= 4:
        score += 20
    elif acuity >= 3:
        score += 10
    
    if arrival_ambulance:
        score += 5
    
    score = min(100, score + random.randint(5, 15))
    
    if score >= 65:
        category = 'HIGH'
    elif score >= 45:
        category = 'MODERATE'
    else:
        category = 'LOW'
    
    return score, category


@router.post("/start")
async def start_simulation(
    db: Session = Depends(get_db)
):
    """
    Start the time simulation from the latest data in the database.
    Continues from where it left off - no replay, just forward generation.
    """
    global simulation_state
    
    try:
        # Get the latest vital signs timestamp from the database
        latest_vital = db.query(func.max(VitalSigns.timestamp)).scalar()
        
        if not latest_vital:
            # No vitals in DB - start from now
            latest_vital = datetime.utcnow()
            logger.info("No vitals in database, starting simulation from current time")
        
        # Set simulation to start from the latest timestamp
        simulation_state.start_sim_time = latest_vital
        simulation_state.current_sim_time = latest_vital
        simulation_state.start_real_time = datetime.utcnow()
        simulation_state.is_running = True
        simulation_state.last_vitals_update = None  # Allow immediate first tick
        
        logger.info(f"Simulation started from latest data: {latest_vital}")
        
        return {
            "success": True,
            "message": "Simulation started from latest database data",
            "simulated_start_time": latest_vital.isoformat(),
            "current_time": latest_vital.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_simulation():
    """Stop the time simulation."""
    global simulation_state
    simulation_state.is_running = False
    return {"success": True, "message": "Simulation stopped"}


@router.get("/time", response_model=SimulationTimeResponse)
async def get_simulation_time():
    """Get current simulated time."""
    global simulation_state
    
    sim_time = simulation_state.get_simulated_time()
    
    sim_minutes = 0
    if simulation_state.is_running and simulation_state.start_sim_time:
        sim_minutes = (sim_time - simulation_state.start_sim_time).total_seconds() / 60
    
    return SimulationTimeResponse(
        simulated_time=sim_time.isoformat(),
        real_time=datetime.utcnow().isoformat(),
        is_running=simulation_state.is_running,
        time_scale=simulation_state.time_scale,
        sim_minutes_elapsed=sim_minutes
    )


@router.post("/tick")
async def simulation_tick(db: Session = Depends(get_db)):
    """
    Called every 60 real seconds to generate new vitals for all patients.
    This simulates 5 minutes passing in the hospital.
    New data is saved to the database and persists.
    """
    global simulation_state
    
    if not simulation_state.is_running:
        return {"success": False, "message": "Simulation not running"}
    
    if not simulation_state.should_update_vitals():
        return {"success": True, "message": "Not time for update yet", "updated": 0}
    
    try:
        # Get current simulated time (5 minutes ahead of last update)
        sim_time = simulation_state.get_simulated_time()
        
        patient_repo = PatientRepository(db)
        vital_signs_repo = VitalSignsRepository(db)
        risk_repo = RiskAssessmentRepository(db)
        
        patients = patient_repo.get_all()
        updated_count = 0
        
        for patient in patients:
            # Get latest vitals as base for generating new ones
            latest_vitals = vital_signs_repo.get_latest_for_patient(patient.patient_id)
            if not latest_vitals:
                continue
            
            # Get latest risk to determine variation level
            latest_risk = risk_repo.get_latest_for_patient(patient.patient_id)
            risk_level = latest_risk.risk_category.value if latest_risk else 'MODERATE'
            
            # Generate new vitals with variation based on previous values
            base_vitals = {
                'heart_rate': latest_vitals.heart_rate,
                'systolic_bp': latest_vitals.systolic_bp,
                'diastolic_bp': latest_vitals.diastolic_bp,
                'respiratory_rate': latest_vitals.respiratory_rate,
                'oxygen_saturation': latest_vitals.oxygen_saturation,
                'temperature': latest_vitals.temperature,
            }
            
            new_vitals_data = generate_vitals_variation(base_vitals, risk_level)
            
            # Ensure diastolic < systolic
            if new_vitals_data['diastolic_bp'] >= new_vitals_data['systolic_bp']:
                new_vitals_data['diastolic_bp'] = new_vitals_data['systolic_bp'] - 15
            
            # Create new vital signs record with current simulated time
            new_vitals = VitalSigns(
                id=str(uuid4()),
                patient_id=patient.patient_id,
                heart_rate=round(new_vitals_data['heart_rate'], 1),
                systolic_bp=round(new_vitals_data['systolic_bp'], 1),
                diastolic_bp=round(new_vitals_data['diastolic_bp'], 1),
                respiratory_rate=round(new_vitals_data['respiratory_rate'], 1),
                oxygen_saturation=round(new_vitals_data['oxygen_saturation'], 1),
                temperature=round(new_vitals_data['temperature'], 1),
                timestamp=sim_time,
                created_at=datetime.utcnow(),
            )
            db.add(new_vitals)
            db.flush()
            
            # Calculate and store risk assessment
            is_ambulance = patient.arrival_mode == ArrivalModeEnum.AMBULANCE
            risk_score, risk_category = calculate_risk_from_vitals(
                new_vitals_data, patient.acuity_level, is_ambulance
            )
            
            risk_cat_enum = RiskCategoryEnum.HIGH if risk_category == 'HIGH' else \
                           RiskCategoryEnum.MODERATE if risk_category == 'MODERATE' else \
                           RiskCategoryEnum.LOW
            
            new_risk = RiskAssessment(
                id=str(uuid4()),
                patient_id=patient.patient_id,
                vital_signs_id=new_vitals.id,
                risk_score=risk_score,
                risk_category=risk_cat_enum,
                risk_flag=risk_score >= 65,
                assessment_time=sim_time,
                model_version="v1.0.0-sim",
                processing_time_ms=random.randint(10, 30),
            )
            db.add(new_risk)
            
            # Update patient last_updated
            patient.last_updated = sim_time
            
            updated_count += 1
        
        # Commit all changes to database (data persists)
        db.commit()
        simulation_state.last_vitals_update = datetime.utcnow()
        
        logger.info(f"Simulation tick: updated {updated_count} patients at sim time {sim_time}")
        
        return {
            "success": True,
            "message": f"Updated {updated_count} patients",
            "updated": updated_count,
            "simulated_time": sim_time.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Simulation tick failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_simulation_status(db: Session = Depends(get_db)):
    """Get full simulation status including patient counts."""
    global simulation_state
    
    sim_time = simulation_state.get_simulated_time()
    
    patient_repo = PatientRepository(db)
    patients = patient_repo.get_all()
    
    # Get latest timestamp from DB
    latest_vital = db.query(func.max(VitalSigns.timestamp)).scalar()
    
    return {
        "is_running": simulation_state.is_running,
        "simulated_time": sim_time.isoformat(),
        "real_time": datetime.utcnow().isoformat(),
        "time_scale": simulation_state.time_scale,
        "total_patients": len(patients),
        "start_sim_time": simulation_state.start_sim_time.isoformat() if simulation_state.start_sim_time else None,
        "latest_db_timestamp": latest_vital.isoformat() if latest_vital else None
    }
