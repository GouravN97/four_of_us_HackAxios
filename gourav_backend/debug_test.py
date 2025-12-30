#!/usr/bin/env python3
"""
Debug script to test the data integrity property test.
"""

import sys
import os
sys.path.append('.')

from datetime import datetime
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.api_models import (
    ArrivalMode,
    PatientRegistration,
    VitalSignsUpdate,
    VitalSignsWithTimestamp,
)
from src.services.patient_service import PatientService
from src.services.vital_signs_service import (
    VitalSignsService,
    ValidationError,
    VitalSignsServiceError,
)
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.utils.database import get_test_db, create_test_database

def test_simple_case():
    """Test a simple case manually."""
    print("Creating test database...")
    create_test_database()
    
    print("Setting up test data...")
    patient_id = "TEST_PATIENT_001"
    arrival_mode = ArrivalMode.AMBULANCE
    acuity_level = 3
    
    # Valid initial vital signs
    initial_vitals = VitalSignsWithTimestamp(
        heart_rate=80.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        respiratory_rate=16.0,
        oxygen_saturation=98.0,
        temperature=37.0,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )
    
    # Create patient registration
    registration_data = PatientRegistration(
        patient_id=patient_id,
        arrival_mode=arrival_mode,
        acuity_level=acuity_level,
        initial_vitals=initial_vitals,
    )
    
    # Use test database session
    db_session = next(get_test_db())
    try:
        print("Initializing services...")
        patient_service = PatientService(db_session)
        vital_signs_service = VitalSignsService(db_session)
        vital_signs_repo = VitalSignsRepository(db_session)
        
        print("Registering patient...")
        registered_patient = patient_service.register_patient(registration_data)
        print(f"Patient registered: {registered_patient.patient_id}")
        
        # Get initial state
        initial_count = vital_signs_repo.get_count_for_patient(patient_id)
        initial_vital_signs = vital_signs_repo.get_latest_for_patient(patient_id)
        print(f"Initial vital signs count: {initial_count}")
        print(f"Initial heart rate: {initial_vital_signs.heart_rate}")
        
        # Try invalid update (heart rate out of range)
        print("Attempting invalid vital signs update...")
        try:
            invalid_update = VitalSignsUpdate(
                heart_rate=500.0,  # Invalid - too high
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=37.0,
            )
            
            vital_signs_service.update_vital_signs(patient_id, invalid_update)
            print("ERROR: Invalid update was accepted!")
            
        except (ValidationError, ValueError, VitalSignsServiceError) as e:
            print(f"Good: Invalid update was rejected: {e}")
        
        # Verify data integrity
        final_count = vital_signs_repo.get_count_for_patient(patient_id)
        final_vitals = vital_signs_repo.get_latest_for_patient(patient_id)
        
        print(f"Final vital signs count: {final_count}")
        print(f"Final heart rate: {final_vitals.heart_rate}")
        
        if final_count == initial_count and final_vitals.heart_rate == initial_vital_signs.heart_rate:
            print("SUCCESS: Data integrity preserved!")
            return True
        else:
            print("FAILURE: Data integrity compromised!")
            return False
            
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_simple_case()
    if success:
        print("\nTest passed! The property test logic should work.")
    else:
        print("\nTest failed! There's an issue with the implementation.")