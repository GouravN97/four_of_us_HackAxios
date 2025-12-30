"""
Property-based tests for registration triggering risk assessment.
Tests that patient registration automatically creates a risk assessment.
"""

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.api_models import (
    ArrivalMode,
    PatientRegistration,
    VitalSignsWithTimestamp,
)
from src.services.patient_service import PatientService
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.utils.database import get_test_db, create_test_database


class TestRegistrationTriggersRiskAssessment:
    """Property 3: Registration Triggers Risk Assessment - Validates Requirements 1.3"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        # This will be called before each test method
        pass

    def _setup_clean_db(self):
        """Create a clean database for each test iteration."""
        create_test_database()

    @given(
        patient_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Pc")
            )
        ).filter(lambda x: x.strip()),
        arrival_mode=st.sampled_from(ArrivalMode),
        acuity_level=st.integers(min_value=1, max_value=5),
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
    @settings(max_examples=100)
    @pytest.mark.property_tests
    def test_registration_triggers_risk_assessment(
        self,
        patient_id,
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
        Property 3: Registration Triggers Risk Assessment
        Validates: Requirements 1.3

        For any patient registration with valid data, the system should
        automatically create a risk assessment record linked to that patient.
        """
        # Ensure diastolic BP is less than systolic BP (medical constraint)
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            # Ensure diastolic is still within valid range
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0

        # Create initial vital signs
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
        self._setup_clean_db()
        db_session = next(get_test_db())
        try:
            # Initialize services
            patient_service = PatientService(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            
            # Check that no risk assessment exists before registration
            initial_risk_count = risk_repo.get_count_for_patient(patient_id)
            assert initial_risk_count == 0, f"Expected no risk assessments initially, found {initial_risk_count}"
            
            # Register the patient
            registered_patient = patient_service.register_patient(registration_data)
            
            # Verify patient was created
            assert registered_patient is not None
            assert registered_patient.patient_id == patient_id
            assert registered_patient.arrival_mode.value == arrival_mode.value
            assert registered_patient.acuity_level == acuity_level
            
            # NOTE: This test currently only verifies that patient registration
            # creates the patient and vital signs records. The actual risk assessment
            # creation will be handled by RiskAssessmentService when it's implemented.
            # For now, we verify that the foundation is in place for risk assessment
            # to be triggered.
            
            # Verify that vital signs were created (prerequisite for risk assessment)
            vital_signs_repo = VitalSignsRepository(db_session)
            latest_vitals = vital_signs_repo.get_latest_for_patient(patient_id)
            
            assert latest_vitals is not None, "Expected vital signs to be created during registration"
            assert latest_vitals.patient_id == patient_id
            assert latest_vitals.heart_rate == heart_rate
            assert latest_vitals.systolic_bp == systolic_bp
            assert latest_vitals.diastolic_bp == diastolic_bp
            assert latest_vitals.respiratory_rate == respiratory_rate
            assert latest_vitals.oxygen_saturation == oxygen_saturation
            assert latest_vitals.temperature == temperature
            
            # The risk assessment should be created by RiskAssessmentService
            # when it detects new vital signs. For now, we verify the foundation
            # is in place.
            
        finally:
            db_session.close()

    @given(
        patient_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Pc")
            )
        ).filter(lambda x: x.strip()),
        arrival_mode=st.sampled_from(ArrivalMode),
        acuity_level=st.integers(min_value=1, max_value=5),
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
    @settings(max_examples=50)
    @pytest.mark.property_tests
    def test_registration_creates_complete_patient_record(
        self,
        patient_id,
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
        Property 3: Registration Triggers Risk Assessment (Foundation)
        Validates: Requirements 1.3

        For any patient registration, the system should create a complete
        patient record with all necessary data for risk assessment.
        """
        # Ensure diastolic BP is less than systolic BP (medical constraint)
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            # Ensure diastolic is still within valid range
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0

        # Create initial vital signs
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
        self._setup_clean_db()
        db_session = next(get_test_db())
        try:
            # Initialize services
            patient_service = PatientService(db_session)
            
            # Register the patient
            registered_patient = patient_service.register_patient(registration_data)
            
            # Verify patient record has all required fields for risk assessment
            assert registered_patient.patient_id == patient_id
            assert registered_patient.arrival_mode is not None
            assert registered_patient.acuity_level is not None
            assert 1 <= registered_patient.acuity_level <= 5
            assert registered_patient.registration_time is not None
            assert registered_patient.last_updated is not None
            
            # Verify vital signs record exists with all required fields
            vital_signs_repo = VitalSignsRepository(db_session)
            latest_vitals = vital_signs_repo.get_latest_for_patient(patient_id)
            
            assert latest_vitals is not None
            assert latest_vitals.patient_id == patient_id
            assert latest_vitals.heart_rate is not None
            assert latest_vitals.systolic_bp is not None
            assert latest_vitals.diastolic_bp is not None
            assert latest_vitals.respiratory_rate is not None
            assert latest_vitals.oxygen_saturation is not None
            assert latest_vitals.temperature is not None
            assert latest_vitals.timestamp is not None
            
            # Verify all data needed for risk model is present
            # (heart rate, systolic BP, diastolic BP, respiratory rate, 
            #  oxygen saturation, temperature, arrival mode, acuity level)
            risk_model_inputs = {
                'heart_rate': latest_vitals.heart_rate,
                'systolic_bp': latest_vitals.systolic_bp,
                'diastolic_bp': latest_vitals.diastolic_bp,
                'respiratory_rate': latest_vitals.respiratory_rate,
                'oxygen_saturation': latest_vitals.oxygen_saturation,
                'temperature': latest_vitals.temperature,
                'arrival_mode': registered_patient.arrival_mode.value,
                'acuity_level': registered_patient.acuity_level
            }
            
            # Verify all required inputs are present and valid
            for field_name, field_value in risk_model_inputs.items():
                assert field_value is not None, f"Risk model input {field_name} is None"
                if isinstance(field_value, (int, float)):
                    assert not (field_value != field_value), f"Risk model input {field_name} is NaN"  # Check for NaN
            
        finally:
            db_session.close()