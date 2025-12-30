#!/usr/bin/env python3
"""
Simple test to verify the timezone fix works.
"""

from datetime import datetime, timezone
from src.models.api_models import PatientRegistration, VitalSignsWithTimestamp, ArrivalMode
from src.services.patient_service import PatientService, ValidationError

def test_timezone_fix():
    """Test that the timezone fix works for both naive and aware timestamps."""
    
    # Test with timezone-naive timestamp (should work)
    naive_timestamp = datetime(2020, 1, 1)
    print(f"Testing naive timestamp: {naive_timestamp}, tzinfo: {naive_timestamp.tzinfo}")
    
    initial_vitals_naive = VitalSignsWithTimestamp(
        heart_rate=80.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        respiratory_rate=16.0,
        oxygen_saturation=98.0,
        temperature=37.0,
        timestamp=naive_timestamp,
    )
    
    registration_naive = PatientRegistration(
        patient_id="test_patient_naive",
        arrival_mode=ArrivalMode.AMBULANCE,
        acuity_level=3,
        initial_vitals=initial_vitals_naive,
    )
    
    # Test with timezone-aware timestamp (should work after fix)
    aware_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    print(f"Testing aware timestamp: {aware_timestamp}, tzinfo: {aware_timestamp.tzinfo}")
    
    initial_vitals_aware = VitalSignsWithTimestamp(
        heart_rate=80.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        respiratory_rate=16.0,
        oxygen_saturation=98.0,
        temperature=37.0,
        timestamp=aware_timestamp,
    )
    
    registration_aware = PatientRegistration(
        patient_id="test_patient_aware",
        arrival_mode=ArrivalMode.AMBULANCE,
        acuity_level=3,
        initial_vitals=initial_vitals_aware,
    )
    
    # Create a mock patient service to test validation
    class MockPatientService(PatientService):
        def __init__(self):
            # Don't call super().__init__ to avoid database dependency
            pass
    
    service = MockPatientService()
    
    try:
        print("Testing naive timestamp validation...")
        service._validate_registration_data(registration_naive)
        print("✓ Naive timestamp validation passed")
    except Exception as e:
        print(f"✗ Naive timestamp validation failed: {e}")
    
    try:
        print("Testing aware timestamp validation...")
        service._validate_registration_data(registration_aware)
        print("✓ Aware timestamp validation passed")
    except Exception as e:
        print(f"✗ Aware timestamp validation failed: {e}")
    
    # Test future timestamp (should fail)
    future_timestamp = datetime(2030, 1, 1)
    print(f"Testing future timestamp: {future_timestamp}, tzinfo: {future_timestamp.tzinfo}")
    
    initial_vitals_future = VitalSignsWithTimestamp(
        heart_rate=80.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        respiratory_rate=16.0,
        oxygen_saturation=98.0,
        temperature=37.0,
        timestamp=future_timestamp,
    )
    
    registration_future = PatientRegistration(
        patient_id="test_patient_future",
        arrival_mode=ArrivalMode.AMBULANCE,
        acuity_level=3,
        initial_vitals=initial_vitals_future,
    )
    
    try:
        print("Testing future timestamp validation (should fail)...")
        service._validate_registration_data(registration_future)
        print("✗ Future timestamp validation should have failed but didn't")
    except ValidationError as e:
        print(f"✓ Future timestamp validation correctly failed: {e}")
    except Exception as e:
        print(f"✗ Future timestamp validation failed with unexpected error: {e}")

if __name__ == "__main__":
    test_timezone_fix()