#!/usr/bin/env python3
"""
Direct Database Population Script - bypasses API to avoid rate limiting.
Populates the database with 20 patients, each with 7 hours of vitals data (every 5 minutes).
This provides enough historical data for the risk_classifier and ICU prediction ML models.
"""

import sys
import os
import random
from datetime import datetime, timedelta
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import Base, Patient, VitalSigns, RiskAssessment, ArrivalModeEnum, RiskCategoryEnum
from models.icu_models import ICUAdmission, ICUOccupancyLog, ICUAdmissionStatus

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'patient_risk_dev.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Patient profiles - 20 patients with varied risk levels
PATIENT_PROFILES = [
    # HIGH risk patients (7)
    {"id": "P001", "arrival_mode": "Ambulance", "acuity": 5, "risk": "HIGH",
     "vitals": {"hr": (95, 120), "sbp": (150, 180), "dbp": (95, 110), "rr": (22, 28), "o2": (88, 94), "temp": (37.8, 39.0)}},
    {"id": "P002", "arrival_mode": "Ambulance", "acuity": 5, "risk": "HIGH",
     "vitals": {"hr": (100, 130), "sbp": (130, 150), "dbp": (85, 100), "rr": (28, 38), "o2": (85, 92), "temp": (38.0, 39.5)}},
    {"id": "P003", "arrival_mode": "Ambulance", "acuity": 5, "risk": "HIGH",
     "vitals": {"hr": (85, 110), "sbp": (170, 200), "dbp": (100, 120), "rr": (18, 24), "o2": (92, 96), "temp": (37.0, 37.8)}},
    {"id": "P006", "arrival_mode": "Ambulance", "acuity": 4, "risk": "HIGH",
     "vitals": {"hr": (90, 110), "sbp": (100, 120), "dbp": (60, 75), "rr": (18, 24), "o2": (95, 98), "temp": (36.5, 37.5)}},
    {"id": "P010", "arrival_mode": "Ambulance", "acuity": 5, "risk": "HIGH",
     "vitals": {"hr": (110, 140), "sbp": (85, 100), "dbp": (50, 65), "rr": (24, 32), "o2": (88, 94), "temp": (37.5, 38.5)}},
    {"id": "P011", "arrival_mode": "Ambulance", "acuity": 5, "risk": "HIGH",
     "vitals": {"hr": (105, 125), "sbp": (160, 190), "dbp": (95, 115), "rr": (20, 26), "o2": (89, 93), "temp": (38.2, 39.2)}},
    {"id": "P012", "arrival_mode": "Ambulance", "acuity": 4, "risk": "HIGH",
     "vitals": {"hr": (95, 115), "sbp": (145, 175), "dbp": (90, 105), "rr": (22, 30), "o2": (90, 95), "temp": (37.5, 38.8)}},
    
    # MODERATE risk patients (7)
    {"id": "P004", "arrival_mode": "Walk-in", "acuity": 3, "risk": "MODERATE",
     "vitals": {"hr": (85, 100), "sbp": (120, 140), "dbp": (75, 90), "rr": (18, 22), "o2": (94, 97), "temp": (38.5, 39.5)}},
    {"id": "P005", "arrival_mode": "Walk-in", "acuity": 3, "risk": "MODERATE",
     "vitals": {"hr": (80, 95), "sbp": (115, 135), "dbp": (70, 85), "rr": (16, 20), "o2": (96, 99), "temp": (37.2, 38.2)}},
    {"id": "P009", "arrival_mode": "Walk-in", "acuity": 2, "risk": "MODERATE",
     "vitals": {"hr": (70, 85), "sbp": (120, 135), "dbp": (75, 85), "rr": (14, 18), "o2": (97, 99), "temp": (36.5, 37.2)}},
    {"id": "P013", "arrival_mode": "Walk-in", "acuity": 3, "risk": "MODERATE",
     "vitals": {"hr": (82, 98), "sbp": (125, 145), "dbp": (78, 92), "rr": (17, 21), "o2": (95, 98), "temp": (37.8, 38.8)}},
    {"id": "P014", "arrival_mode": "Ambulance", "acuity": 3, "risk": "MODERATE",
     "vitals": {"hr": (88, 102), "sbp": (130, 150), "dbp": (80, 95), "rr": (18, 23), "o2": (94, 97), "temp": (37.5, 38.5)}},
    {"id": "P015", "arrival_mode": "Walk-in", "acuity": 3, "risk": "MODERATE",
     "vitals": {"hr": (78, 92), "sbp": (118, 138), "dbp": (72, 88), "rr": (16, 20), "o2": (95, 98), "temp": (37.0, 38.0)}},
    {"id": "P016", "arrival_mode": "Walk-in", "acuity": 2, "risk": "MODERATE",
     "vitals": {"hr": (75, 90), "sbp": (122, 140), "dbp": (74, 88), "rr": (15, 19), "o2": (96, 99), "temp": (36.8, 37.8)}},
    
    # LOW risk patients (6)
    {"id": "P007", "arrival_mode": "Walk-in", "acuity": 2, "risk": "LOW",
     "vitals": {"hr": (65, 80), "sbp": (110, 125), "dbp": (70, 80), "rr": (14, 18), "o2": (97, 100), "temp": (36.5, 37.2)}},
    {"id": "P008", "arrival_mode": "Walk-in", "acuity": 1, "risk": "LOW",
     "vitals": {"hr": (60, 75), "sbp": (115, 125), "dbp": (70, 80), "rr": (12, 16), "o2": (98, 100), "temp": (36.4, 37.0)}},
    {"id": "P017", "arrival_mode": "Walk-in", "acuity": 1, "risk": "LOW",
     "vitals": {"hr": (62, 78), "sbp": (112, 128), "dbp": (68, 78), "rr": (13, 17), "o2": (98, 100), "temp": (36.3, 37.1)}},
    {"id": "P018", "arrival_mode": "Walk-in", "acuity": 2, "risk": "LOW",
     "vitals": {"hr": (68, 82), "sbp": (108, 122), "dbp": (65, 78), "rr": (14, 18), "o2": (97, 100), "temp": (36.5, 37.2)}},
    {"id": "P019", "arrival_mode": "Walk-in", "acuity": 1, "risk": "LOW",
     "vitals": {"hr": (58, 72), "sbp": (110, 120), "dbp": (68, 76), "rr": (12, 16), "o2": (98, 100), "temp": (36.4, 36.9)}},
    {"id": "P020", "arrival_mode": "Walk-in", "acuity": 2, "risk": "LOW",
     "vitals": {"hr": (64, 78), "sbp": (115, 128), "dbp": (70, 82), "rr": (13, 17), "o2": (97, 100), "temp": (36.5, 37.3)}},
]

def generate_vitals(profile):
    """Generate random vitals within profile ranges."""
    v = profile["vitals"]
    return {
        "heart_rate": round(random.uniform(*v["hr"]), 1),
        "systolic_bp": round(random.uniform(*v["sbp"]), 1),
        "diastolic_bp": round(random.uniform(*v["dbp"]), 1),
        "respiratory_rate": round(random.uniform(*v["rr"]), 1),
        "oxygen_saturation": min(100, round(random.uniform(*v["o2"]), 1)),
        "temperature": round(random.uniform(*v["temp"]), 1),
    }

def calculate_risk_score(vitals, acuity, arrival_mode):
    """Simple risk score calculation."""
    score = 0
    if vitals["oxygen_saturation"] < 92: score += 25
    elif vitals["oxygen_saturation"] < 95: score += 10
    if vitals["systolic_bp"] < 90 or vitals["systolic_bp"] > 160: score += 15
    if vitals["heart_rate"] > 120 or vitals["heart_rate"] < 50: score += 10
    if vitals["respiratory_rate"] > 24: score += 10
    if acuity >= 4: score += 20
    elif acuity >= 3: score += 10
    if arrival_mode == "Ambulance": score += 5
    return min(100, score + random.randint(10, 30))

def main():
    print("=" * 60)
    print("DIRECT DATABASE POPULATION")
    print("=" * 60)
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    
    # Import all models to register them with Base
    from models.db_models import Base
    from models.icu_models import ICUAdmission, ICUOccupancyLog, ICUAdmissionStatus
    
    # Create all tables including ICU tables
    Base.metadata.create_all(engine)
    
    # Also explicitly create ICU tables
    ICUAdmission.__table__.create(engine, checkfirst=True)
    ICUOccupancyLog.__table__.create(engine, checkfirst=True)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Clear existing data
    print("\n1. Clearing existing data...")
    session.query(RiskAssessment).delete()
    session.query(VitalSigns).delete()
    session.query(Patient).delete()
    session.commit()
    print("   ✅ Cleared all tables")
    
    # Time settings - 7 hours of history for ML models
    now = datetime.utcnow()
    history_hours = 7
    history_minutes = history_hours * 60  # 420 minutes
    interval_minutes = 5
    num_readings = history_minutes // interval_minutes  # 84 readings per patient
    
    print(f"\n2. Creating {len(PATIENT_PROFILES)} patients with {num_readings} readings each...")
    print(f"   History: {history_hours} hours, Interval: {interval_minutes} minutes")
    
    total_vitals = 0
    total_assessments = 0
    
    for profile in PATIENT_PROFILES:
        # Create patient
        arrival_mode = ArrivalModeEnum.AMBULANCE if profile["arrival_mode"] == "Ambulance" else ArrivalModeEnum.WALK_IN
        patient = Patient(
            patient_id=profile["id"],
            arrival_mode=arrival_mode,
            acuity_level=profile["acuity"],
            registration_time=now - timedelta(minutes=history_minutes),
        )
        session.add(patient)
        
        # Create vitals every 5 minutes
        for i in range(num_readings + 1):
            timestamp = now - timedelta(minutes=history_minutes - (i * interval_minutes))
            vitals_data = generate_vitals(profile)
            
            vital_signs = VitalSigns(
                id=str(uuid4()),
                patient_id=profile["id"],
                heart_rate=vitals_data["heart_rate"],
                systolic_bp=vitals_data["systolic_bp"],
                diastolic_bp=vitals_data["diastolic_bp"],
                respiratory_rate=vitals_data["respiratory_rate"],
                oxygen_saturation=vitals_data["oxygen_saturation"],
                temperature=vitals_data["temperature"],
                timestamp=timestamp,
                created_at=timestamp,
            )
            session.add(vital_signs)
            total_vitals += 1
            
            # Create risk assessment
            risk_score = calculate_risk_score(vitals_data, profile["acuity"], profile["arrival_mode"])
            risk_cat = RiskCategoryEnum.HIGH if risk_score >= 60 else RiskCategoryEnum.MODERATE if risk_score >= 40 else RiskCategoryEnum.LOW
            
            assessment = RiskAssessment(
                id=str(uuid4()),
                patient_id=profile["id"],
                vital_signs_id=vital_signs.id,
                risk_score=risk_score,
                risk_category=risk_cat,
                risk_flag=risk_score >= 60,
                assessment_time=timestamp,
                model_version="v1.0.0",
                processing_time_ms=random.randint(10, 50),
            )
            session.add(assessment)
            total_assessments += 1
        
        risk_emoji = "🚨" if profile["risk"] == "HIGH" else "⚠️" if profile["risk"] == "MODERATE" else "✅"
        print(f"   {risk_emoji} {profile['id']}: {num_readings + 1} readings ({profile['risk']} risk)")
    
    session.commit()
    
    print(f"\n3. Summary:")
    print(f"   Patients: {len(PATIENT_PROFILES)}")
    print(f"   Vital signs records: {total_vitals}")
    print(f"   Risk assessments: {total_assessments}")
    
    # Create ICU admissions for HIGH risk patients
    print(f"\n4. Creating ICU admissions for HIGH risk patients...")
    session.query(ICUAdmission).delete()
    session.query(ICUOccupancyLog).delete()
    session.commit()
    
    icu_admissions = 0
    bed_number = 1
    for profile in PATIENT_PROFILES:
        if profile["risk"] == "HIGH":
            admission = ICUAdmission(
                id=str(uuid4()),
                patient_id=profile["id"],
                admission_time=now - timedelta(minutes=random.randint(30, 60)),
                status=ICUAdmissionStatus.ADMITTED.value,
                risk_score_at_admission=random.uniform(60, 85),
                risk_category_at_admission="HIGH",
                bed_number=f"ICU-{bed_number:02d}",
                admission_reason=f"Automatic admission due to HIGH risk classification"
            )
            session.add(admission)
            icu_admissions += 1
            bed_number += 1
            print(f"   🏥 {profile['id']} admitted to ICU bed ICU-{bed_number-1:02d}")
    
    # Create hourly occupancy logs for the past 7 hours
    print(f"\n5. Creating ICU occupancy history (7 hours)...")
    for i in range(7, 0, -1):
        hour_time = now - timedelta(hours=i)
        hour_time = hour_time.replace(minute=0, second=0, microsecond=0)
        
        # Simulate varying occupancy
        base_count = icu_admissions + random.randint(-2, 3)
        patient_count = max(0, min(60, base_count))
        
        log = ICUOccupancyLog(
            id=str(uuid4()),
            timestamp=hour_time,
            patient_count=patient_count,
            beds_total=15,
            beds_occupied=patient_count,
            high_risk_count=min(patient_count, icu_admissions),
            new_admissions=random.randint(0, 2),
            discharges=random.randint(0, 1)
        )
        session.add(log)
        print(f"   📊 {hour_time.strftime('%H:%M')}: {patient_count} patients")
    
    session.commit()
    
    # Verify
    print(f"\n6. Verification:")
    p_count = session.query(Patient).count()
    v_count = session.query(VitalSigns).count()
    r_count = session.query(RiskAssessment).count()
    i_count = session.query(ICUAdmission).count()
    o_count = session.query(ICUOccupancyLog).count()
    print(f"   Patients in DB: {p_count}")
    print(f"   Vital signs in DB: {v_count}")
    print(f"   Risk assessments in DB: {r_count}")
    print(f"   ICU admissions: {i_count}")
    print(f"   ICU occupancy logs: {o_count}")
    
    session.close()
    
    print("\n" + "=" * 60)
    print("✅ DATABASE POPULATED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
