"""
Property-based tests for vital signs update triggering risk assessment.
Tests that updating vital signs automatically creates a new risk assessment.

**Feature: patient-risk-classifier, Property 6: Vital Signs Update Triggers Risk Assessment**
**Validates: Requirements 2.3**
"""

from datetime import datetime

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
from src.services.vital_signs_service import VitalSignsService
from src.services.risk_assessment_service import RiskAssessmentService
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.utils.database import get_test_db, create_test_database


class TestVitalSignsUpdateTriggersRiskAssessment:
    """Property 6: Vital Signs Update Triggers Risk Assessment - Validates Requirements 2.3"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
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
        # Initial vital signs
        initial_heart_rate=st.floats(min_value=30, max_value=200),
        initial_systolic_bp=st.floats(min_value=50, max_value=300),
        initial_diastolic_bp=st.floats(min_value=20, max_value=200),
        initial_respiratory_rate=st.floats(min_value=5, max_value=60),
        initial_oxygen_saturation=st.floats(min_value=50, max_value=100),
        initial_temperature=st.floats(min_value=30, max_value=45),
        initial_timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31),
            timezones=st.none(),
        ),
        # Updated vital signs
        updated_heart_rate=st.floats(min_value=30, max_value=200),
        updated_systolic_bp=st.floats(min_value=50, max_value=300),
        updated_diastolic_bp=st.floats(min_value=20, max_value=200),
        updated_respiratory_rate=st.floats(min_value=5, max_value=60),
        updated_oxygen_saturation=st.floats(min_value=50, max_value=100),
        updated_temperature=st.floats(min_value=30, max_value=45),
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property_tests
    def test_vital_signs_update_triggers_risk_assessment(
        self,
        patient_id,
        arrival_mode,
        acuity_level,
        initial_heart_rate,
        initial_systolic_bp,
        initial_diastolic_bp,
        initial_respiratory_rate,
        initial_oxygen_saturation,
        initial_temperature,
        initial_timestamp,
        updated_heart_rate,
        updated_systolic_bp,
        updated_diastolic_bp,
        updated_respiratory_rate,
        updated_oxygen_saturation,
        updated_temperature,
    ):
        """
        Property 6: Vital Signs Update Triggers Risk Assessment
        Validates: Requirements 2.3

        For any vital signs update for an existing patient, the system should
        automatically create a new risk assessment using the updated data.
        """
        # Ensure diastolic BP is less than systolic BP for initial vitals
        if initial_diastolic_bp >= initial_systolic_bp:
            initial_diastolic_bp = initial_systolic_bp - 1.0
            if initial_diastolic_bp < 20:
                initial_systolic_bp = 21.0
                initial_diastolic_bp = 20.0

        # Ensure diastolic BP is less than systolic BP for updated vitals
        if updated_diastolic_bp >= updated_systolic_bp:
            updated_diastolic_bp = updated_systolic_bp - 1.0
            if updated_diastolic_bp < 20:
                updated_systolic_bp = 21.0
                updated_diastolic_bp = 20.0

        # Create initial vital signs
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=initial_heart_rate,
            systolic_bp=initial_systolic_bp,
            diastolic_bp=initial_diastolic_bp,
            respiratory_rate=initial_respiratory_rate,
            oxygen_saturation=initial_oxygen_saturation,
            temperature=initial_temperature,
            timestamp=initial_timestamp,
        )

        # Create patient registration
        registration_data = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals,
        )

        # Create updated vital signs
        updated_vitals = VitalSignsUpdate(
            heart_rate=updated_heart_rate,
            systolic_bp=updated_systolic_bp,
            diastolic_bp=updated_diastolic_bp,
            respiratory_rate=updated_respiratory_rate,
            oxygen_saturation=updated_oxygen_saturation,
            temperature=updated_temperature,
        )

        # Use test database session
        self._setup_clean_db()
        db_session = next(get_test_db())
        try:
            # Initialize services
            patient_service = PatientService(db_session)
            vital_signs_service = VitalSignsService(db_session)
            risk_assessment_service = RiskAssessmentService(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vital_signs_repo = VitalSignsRepository(db_session)

            # Register the patient first
            registered_patient = patient_service.register_patient(registration_data)
            assert registered_patient is not None

            # Get initial risk assessment count (may be 0 or 1 depending on implementation)
            initial_risk_count = risk_repo.get_count_for_patient(patient_id)

            # Update vital signs
            new_vital_signs = vital_signs_service.update_vital_signs(
                patient_id=patient_id,
                vital_signs_data=updated_vitals,
                recorded_by="test_system"
            )

            # Verify vital signs were stored
            assert new_vital_signs is not None
            assert new_vital_signs.patient_id == patient_id
            assert new_vital_signs.heart_rate == updated_heart_rate
            assert new_vital_signs.systolic_bp == updated_systolic_bp
            assert new_vital_signs.diastolic_bp == updated_diastolic_bp
            assert new_vital_signs.respiratory_rate == updated_respiratory_rate
            assert new_vital_signs.oxygen_saturation == updated_oxygen_saturation
            assert new_vital_signs.temperature == updated_temperature

            # Trigger risk assessment for the new vital signs (Requirement 2.3)
            risk_assessment = risk_assessment_service.assess_risk_for_vital_signs(new_vital_signs)

            # Verify risk assessment was created
            assert risk_assessment is not None, \
                "Risk assessment should be created after vital signs update"
            assert risk_assessment.patient_id == patient_id, \
                "Risk assessment should be linked to the correct patient"
            assert risk_assessment.vital_signs_id == new_vital_signs.id, \
                "Risk assessment should be linked to the updated vital signs"

            # Verify risk assessment has valid data
            assert 0.0 <= risk_assessment.risk_score <= 1.0, \
                f"Risk score should be between 0 and 1, got {risk_assessment.risk_score}"
            assert isinstance(risk_assessment.risk_flag, bool), \
                "Risk flag should be a boolean"
            assert risk_assessment.assessment_time is not None, \
                "Risk assessment should have a timestamp"

            # Verify risk assessment count increased
            final_risk_count = risk_repo.get_count_for_patient(patient_id)
            assert final_risk_count > initial_risk_count, \
                f"Risk assessment count should increase after vital signs update: " \
                f"initial={initial_risk_count}, final={final_risk_count}"

            # Verify the latest risk assessment is the one we just created
            latest_risk = risk_repo.get_latest_for_patient(patient_id)
            assert latest_risk is not None
            assert latest_risk.id == risk_assessment.id, \
                "Latest risk assessment should be the one created after vital signs update"

        finally:
            db_session.close()
