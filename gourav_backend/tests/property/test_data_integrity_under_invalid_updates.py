"""
Property-based tests for data integrity under invalid updates.
Tests that invalid vital signs updates preserve previous valid measurements.
"""

from datetime import datetime
import uuid

import pytest
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


class TestDataIntegrityUnderInvalidUpdates:
    """Property 7: Data Integrity Under Invalid Updates - Validates Requirements 2.5"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        create_test_database()
        # Clear any existing data
        db_session = next(get_test_db())
        try:
            # Clear all tables
            from src.models.db_models import Patient, VitalSigns, RiskAssessment
            db_session.query(RiskAssessment).delete()
            db_session.query(VitalSigns).delete()
            db_session.query(Patient).delete()
            db_session.commit()
        finally:
            db_session.close()

    @given(
        arrival_mode=st.sampled_from(ArrivalMode),
        acuity_level=st.integers(min_value=1, max_value=5),
        # Valid initial vital signs
        initial_heart_rate=st.floats(min_value=30, max_value=200),
        initial_systolic_bp=st.floats(min_value=50, max_value=300),
        initial_diastolic_bp=st.floats(min_value=20, max_value=200),
        initial_respiratory_rate=st.floats(min_value=5, max_value=60),
        initial_oxygen_saturation=st.floats(min_value=50, max_value=100),
        initial_temperature=st.floats(min_value=30, max_value=45),
        # Invalid update vital signs (out of range)
        invalid_heart_rate=st.one_of(
            st.floats(min_value=-100, max_value=29.9),
            st.floats(min_value=200.1, max_value=500)
        ),
        timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime.utcnow(),
            timezones=st.none(),
        ),
    )
    @settings(max_examples=20)
    @pytest.mark.property_tests
    def test_invalid_vital_signs_preserve_previous_data(
        self,
        arrival_mode,
        acuity_level,
        initial_heart_rate,
        initial_systolic_bp,
        initial_diastolic_bp,
        initial_respiratory_rate,
        initial_oxygen_saturation,
        initial_temperature,
        invalid_heart_rate,
        timestamp,
    ):
        """
        Property 7: Data Integrity Under Invalid Updates
        Validates: Requirements 2.5

        For any invalid vital signs update attempt, the system should
        preserve all previous valid measurements unchanged.
        """
        # Generate unique patient ID for each test
        patient_id = f"TEST_PATIENT_{uuid.uuid4().hex[:8]}"
        
        # Ensure diastolic BP is less than systolic BP for initial valid data
        if initial_diastolic_bp >= initial_systolic_bp:
            initial_diastolic_bp = initial_systolic_bp - 1.0
            # Ensure diastolic is still within valid range
            if initial_diastolic_bp < 20:
                initial_systolic_bp = 21.0
                initial_diastolic_bp = 20.0

        # Create initial valid vital signs
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=initial_heart_rate,
            systolic_bp=initial_systolic_bp,
            diastolic_bp=initial_diastolic_bp,
            respiratory_rate=initial_respiratory_rate,
            oxygen_saturation=initial_oxygen_saturation,
            temperature=initial_temperature,
            timestamp=timestamp,
        )

        # Create patient registration with valid initial data
        registration_data = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals,
        )

        # Use test database session
        db_session = next(get_test_db())
        try:
            # Initialize services
            patient_service = PatientService(db_session)
            vital_signs_service = VitalSignsService(db_session)
            vital_signs_repo = VitalSignsRepository(db_session)
            
            # Register the patient with valid initial data
            registered_patient = patient_service.register_patient(registration_data)
            
            # Verify patient was created with initial vital signs
            assert registered_patient is not None
            initial_vital_signs = vital_signs_repo.get_latest_for_patient(patient_id)
            assert initial_vital_signs is not None
            
            # Store the initial state for comparison
            initial_count = vital_signs_repo.get_count_for_patient(patient_id)
            initial_values = {
                'heart_rate': initial_vital_signs.heart_rate,
                'systolic_bp': initial_vital_signs.systolic_bp,
                'diastolic_bp': initial_vital_signs.diastolic_bp,
                'respiratory_rate': initial_vital_signs.respiratory_rate,
                'oxygen_saturation': initial_vital_signs.oxygen_saturation,
                'temperature': initial_vital_signs.temperature,
            }
            
            # Create invalid vital signs update (invalid heart rate)
            try:
                invalid_update = VitalSignsUpdate(
                    heart_rate=invalid_heart_rate,
                    systolic_bp=initial_systolic_bp,
                    diastolic_bp=initial_diastolic_bp,
                    respiratory_rate=initial_respiratory_rate,
                    oxygen_saturation=initial_oxygen_saturation,
                    temperature=initial_temperature,
                )
                
                # This should fail due to Pydantic validation
                vital_signs_service.update_vital_signs(patient_id, invalid_update)
                
                # If we reach here, the validation didn't work as expected
                # This should not happen, but let's check data integrity anyway
                
            except (ValidationError, ValueError, VitalSignsServiceError):
                # Expected - invalid data should be rejected
                pass
            
            # Verify data integrity: previous valid measurements should be unchanged
            after_invalid_count = vital_signs_repo.get_count_for_patient(patient_id)
            after_invalid_vitals = vital_signs_repo.get_latest_for_patient(patient_id)
            
            # Count should not increase (no new record should be created)
            assert after_invalid_count == initial_count, \
                f"Expected count {initial_count}, got {after_invalid_count}"
            
            # Latest vital signs should still be the initial ones (unchanged)
            assert after_invalid_vitals.heart_rate == initial_values['heart_rate']
            assert after_invalid_vitals.systolic_bp == initial_values['systolic_bp']
            assert after_invalid_vitals.diastolic_bp == initial_values['diastolic_bp']
            assert after_invalid_vitals.respiratory_rate == initial_values['respiratory_rate']
            assert after_invalid_vitals.oxygen_saturation == initial_values['oxygen_saturation']
            assert after_invalid_vitals.temperature == initial_values['temperature']
            
        finally:
            db_session.close()

    @given(
        arrival_mode=st.sampled_from(ArrivalMode),
        acuity_level=st.integers(min_value=1, max_value=5),
        # Valid vital signs
        heart_rate=st.floats(min_value=30, max_value=200),
        systolic_bp=st.floats(min_value=50, max_value=300),
        diastolic_bp=st.floats(min_value=20, max_value=200),
        respiratory_rate=st.floats(min_value=5, max_value=60),
        oxygen_saturation=st.floats(min_value=50, max_value=100),
        temperature=st.floats(min_value=30, max_value=45),
        timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime.utcnow(),
            timezones=st.none(),
        ),
    )
    @settings(max_examples=20)
    @pytest.mark.property_tests
    def test_invalid_blood_pressure_relationship_preserves_data(
        self,
        arrival_mode,
        acuity_level,
        heart_rate,
        systolic_bp,
        diastolic_bp,
        respiratory_rate,
        oxygen_saturation,
        temperature,
        timestamp,
    ):
        """
        Property 7: Data Integrity Under Invalid Updates (Blood Pressure Relationship)
        Validates: Requirements 2.5

        For any vital signs update where diastolic BP >= systolic BP,
        the system should preserve all previous valid measurements unchanged.
        """
        # Generate unique patient ID for each test
        patient_id = f"TEST_PATIENT_{uuid.uuid4().hex[:8]}"
        
        # Ensure initial data has valid BP relationship
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0

        # Create initial valid vital signs
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=heart_rate,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=oxygen_saturation,
            temperature=temperature,
            timestamp=timestamp,
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
            # Initialize services
            patient_service = PatientService(db_session)
            vital_signs_service = VitalSignsService(db_session)
            vital_signs_repo = VitalSignsRepository(db_session)
            
            # Register the patient
            registered_patient = patient_service.register_patient(registration_data)
            assert registered_patient is not None
            
            # Get initial state
            initial_count = vital_signs_repo.get_count_for_patient(patient_id)
            initial_vital_signs = vital_signs_repo.get_latest_for_patient(patient_id)
            assert initial_vital_signs is not None
            
            # Create invalid update with diastolic >= systolic
            invalid_diastolic = systolic_bp + 10.0  # Make diastolic higher than systolic
            if invalid_diastolic > 200:  # Keep within overall range
                invalid_diastolic = 200.0
                invalid_systolic = 190.0
            else:
                invalid_systolic = systolic_bp
            
            try:
                invalid_update = VitalSignsUpdate(
                    heart_rate=heart_rate,
                    systolic_bp=invalid_systolic,
                    diastolic_bp=invalid_diastolic,  # This violates BP relationship
                    respiratory_rate=respiratory_rate,
                    oxygen_saturation=oxygen_saturation,
                    temperature=temperature,
                )
                
                # This should fail due to validation
                vital_signs_service.update_vital_signs(patient_id, invalid_update)
                
            except (ValidationError, ValueError, VitalSignsServiceError):
                # Expected - invalid BP relationship should be rejected
                pass
            
            # Verify data integrity: no new records, original data unchanged
            final_count = vital_signs_repo.get_count_for_patient(patient_id)
            final_vitals = vital_signs_repo.get_latest_for_patient(patient_id)
            
            assert final_count == initial_count, \
                f"Expected count {initial_count}, got {final_count}"
            
            # All values should remain exactly the same
            assert final_vitals.heart_rate == initial_vital_signs.heart_rate
            assert final_vitals.systolic_bp == initial_vital_signs.systolic_bp
            assert final_vitals.diastolic_bp == initial_vital_signs.diastolic_bp
            assert final_vitals.respiratory_rate == initial_vital_signs.respiratory_rate
            assert final_vitals.oxygen_saturation == initial_vital_signs.oxygen_saturation
            assert final_vitals.temperature == initial_vital_signs.temperature
            assert final_vitals.timestamp == initial_vital_signs.timestamp
            
        finally:
            db_session.close()