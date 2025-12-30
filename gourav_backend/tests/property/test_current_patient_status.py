"""
Property-based tests for current patient status retrieval.
Tests that retrieving patient status returns the most recent vital signs and risk assessment.

Property 10: Current Patient Status Retrieval
Validates: Requirements 4.1
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.db_models import ArrivalModeEnum
from src.repositories.patient_repository import PatientRepository
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.services.patient_service import PatientService
from src.utils.database import create_test_database, get_test_db


def generate_unique_patient_id() -> str:
    """Generate a unique patient ID to avoid collisions."""
    return f"P_{uuid4().hex[:12]}"


class TestCurrentPatientStatusRetrieval:
    """Property 10: Current Patient Status Retrieval - Validates Requirements 4.1"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        create_test_database()

    @given(
        arrival_mode=st.sampled_from(ArrivalModeEnum),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=30, max_value=200),
        systolic_bp=st.floats(min_value=50, max_value=300),
        diastolic_bp=st.floats(min_value=20, max_value=200),
        respiratory_rate=st.floats(min_value=5, max_value=60),
        oxygen_saturation=st.floats(min_value=50, max_value=100),
        temperature=st.floats(min_value=30, max_value=45),
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property_tests
    def test_current_status_returns_latest_vitals_and_risk(
        self,
        arrival_mode,
        acuity_level,
        heart_rate,
        systolic_bp,
        diastolic_bp,
        respiratory_rate,
        oxygen_saturation,
        temperature,
    ):
        """
        Property 10: Current Patient Status Retrieval
        Validates: Requirements 4.1

        For any patient with stored data, retrieving current status should return
        the most recent vital signs and risk assessment.
        """
        # Ensure diastolic BP is less than systolic BP (medical constraint)
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0

        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            patient_service = PatientService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=arrival_mode,
                acuity_level=acuity_level
            )

            # Create initial vital signs
            initial_timestamp = datetime.utcnow() - timedelta(hours=2)
            initial_vitals = vitals_repo.create(
                patient_id=patient.patient_id,
                heart_rate=heart_rate,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                respiratory_rate=respiratory_rate,
                oxygen_saturation=oxygen_saturation,
                temperature=temperature,
                timestamp=initial_timestamp,
                recorded_by="test_system"
            )

            # Create initial risk assessment
            initial_risk = risk_repo.create(
                patient_id=patient.patient_id,
                vital_signs_id=initial_vitals.id,
                risk_score=0.3,
                risk_flag=False,
                assessment_time=initial_timestamp + timedelta(seconds=5),
                model_version="test_v1"
            )

            # Get patient status - should return initial data
            status = patient_service.get_patient_status(patient.patient_id)

            # Verify status contains the initial vital signs (using attribute access)
            assert status.current_vitals.heart_rate == heart_rate
            assert status.current_vitals.systolic_bp == systolic_bp
            assert status.current_vitals.diastolic_bp == diastolic_bp
            assert status.current_vitals.respiratory_rate == respiratory_rate
            assert status.current_vitals.oxygen_saturation == oxygen_saturation
            assert status.current_vitals.temperature == temperature

            # Verify status contains the initial risk assessment
            assert status.current_risk.risk_score == 0.3
            assert status.current_risk.risk_flag is False

        finally:
            db_session.close()

    @given(
        num_updates=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.property_tests
    def test_status_returns_most_recent_after_multiple_updates(
        self,
        num_updates,
    ):
        """
        Property 10: Current Patient Status Retrieval
        Validates: Requirements 4.1

        For any patient with multiple vital signs updates, retrieving current status
        should return the most recent vital signs and risk assessment.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            patient_service = PatientService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=ArrivalModeEnum.AMBULANCE,
                acuity_level=3
            )

            base_time = datetime.utcnow() - timedelta(hours=num_updates)
            latest_vitals = None
            latest_risk = None

            # Create multiple vital signs and risk assessments
            for i in range(num_updates):
                timestamp = base_time + timedelta(hours=i)
                
                # Create vital signs with varying values
                vitals = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=70.0 + i * 5,
                    systolic_bp=120.0 + i * 2,
                    diastolic_bp=80.0 + i,
                    respiratory_rate=16.0 + i,
                    oxygen_saturation=98.0 - i * 0.5,
                    temperature=36.5 + i * 0.1,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )

                # Create corresponding risk assessment
                risk_score = 0.2 + i * 0.1
                risk = risk_repo.create(
                    patient_id=patient.patient_id,
                    vital_signs_id=vitals.id,
                    risk_score=min(risk_score, 1.0),
                    risk_flag=risk_score >= 0.5,
                    assessment_time=timestamp + timedelta(seconds=5),
                    model_version="test_v1"
                )

                # Track the latest values
                latest_vitals = vitals
                latest_risk = risk

            # Get patient status
            status = patient_service.get_patient_status(patient.patient_id)

            # Verify status contains the MOST RECENT vital signs (using attribute access)
            assert status.current_vitals.heart_rate == latest_vitals.heart_rate
            assert status.current_vitals.systolic_bp == latest_vitals.systolic_bp
            assert status.current_vitals.diastolic_bp == latest_vitals.diastolic_bp
            assert status.current_vitals.respiratory_rate == latest_vitals.respiratory_rate
            assert status.current_vitals.oxygen_saturation == latest_vitals.oxygen_saturation
            assert status.current_vitals.temperature == latest_vitals.temperature

            # Verify status contains the MOST RECENT risk assessment
            assert status.current_risk.risk_score == latest_risk.risk_score
            assert status.current_risk.risk_flag == latest_risk.risk_flag

        finally:
            db_session.close()

    @given(
        arrival_mode=st.sampled_from(ArrivalModeEnum),
        acuity_level=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.property_tests
    def test_status_contains_all_required_fields(
        self,
        arrival_mode,
        acuity_level,
    ):
        """
        Property 10: Current Patient Status Retrieval
        Validates: Requirements 4.1

        For any patient, the status response should contain all required fields:
        patient_id, arrival_mode, acuity_level, current_vitals, current_risk,
        registration_time, and last_updated.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            patient_service = PatientService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=arrival_mode,
                acuity_level=acuity_level
            )

            # Create vital signs
            timestamp = datetime.utcnow()
            vitals = vitals_repo.create(
                patient_id=patient.patient_id,
                heart_rate=75.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
                timestamp=timestamp,
                recorded_by="test_system"
            )

            # Create risk assessment
            risk = risk_repo.create(
                patient_id=patient.patient_id,
                vital_signs_id=vitals.id,
                risk_score=0.25,
                risk_flag=False,
                assessment_time=timestamp + timedelta(seconds=5),
                model_version="test_v1"
            )

            # Get patient status
            status = patient_service.get_patient_status(patient.patient_id)

            # Verify all required fields are present
            assert status.patient_id == patient_id
            assert status.acuity_level == acuity_level
            assert status.registration_time is not None
            assert status.last_updated is not None

            # Verify current_vitals contains all required vital sign fields (using hasattr)
            assert hasattr(status.current_vitals, 'heart_rate')
            assert hasattr(status.current_vitals, 'systolic_bp')
            assert hasattr(status.current_vitals, 'diastolic_bp')
            assert hasattr(status.current_vitals, 'respiratory_rate')
            assert hasattr(status.current_vitals, 'oxygen_saturation')
            assert hasattr(status.current_vitals, 'temperature')
            assert hasattr(status.current_vitals, 'timestamp')

            # Verify current_risk contains all required risk fields
            assert hasattr(status.current_risk, 'risk_score')
            assert hasattr(status.current_risk, 'risk_flag')
            assert hasattr(status.current_risk, 'assessment_time')
            assert hasattr(status.current_risk, 'model_version')

            # Verify the values are not None
            assert status.current_vitals.heart_rate is not None
            assert status.current_vitals.systolic_bp is not None
            assert status.current_vitals.diastolic_bp is not None
            assert status.current_vitals.respiratory_rate is not None
            assert status.current_vitals.oxygen_saturation is not None
            assert status.current_vitals.temperature is not None
            assert status.current_vitals.timestamp is not None

            assert status.current_risk.risk_score is not None
            assert status.current_risk.risk_flag is not None
            assert status.current_risk.assessment_time is not None

        finally:
            db_session.close()
