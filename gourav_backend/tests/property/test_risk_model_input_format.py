"""
Property-based tests for risk model input format compliance.
Tests that the system calls the risk model with the correct input format.

**Feature: patient-risk-classifier, Property 8: Risk Model Input Format Compliance**
**Validates: Requirements 5.1, 5.4**
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.models.api_models import ArrivalMode
from src.models.db_models import Patient, VitalSigns, ArrivalModeEnum
from src.services.risk_assessment_service import RiskAssessmentService
from src.utils.database import get_test_db, create_test_database
from src.utils.ml_client import RiskModelClient


class TestRiskModelInputFormatCompliance:
    """
    Property 8: Risk Model Input Format Compliance
    Validates: Requirements 5.1, 5.4
    
    For any risk assessment request, the system should call the risk model with
    exactly the specified input format: heart rate, systolic BP, diastolic BP,
    respiratory rate, oxygen saturation, temperature, arrival mode, and acuity level.
    """

    # Expected input fields for the risk model (Requirement 5.1)
    EXPECTED_INPUT_FIELDS = {
        "heart_rate",
        "systolic_bp", 
        "diastolic_bp",
        "respiratory_rate",
        "oxygen_saturation",
        "temperature",
        "arrival_mode",
        "acuity_level"
    }

    def _setup_clean_db(self):
        """Create a clean database for each test iteration."""
        create_test_database()

    @given(
        patient_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))
        ).filter(lambda x: x.strip()),
        arrival_mode=st.sampled_from([ArrivalModeEnum.AMBULANCE, ArrivalModeEnum.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=30, max_value=200, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=50, max_value=300, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=20, max_value=200, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=5, max_value=60, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=50, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=30, max_value=45, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    @pytest.mark.property_tests
    def test_risk_model_receives_correct_input_format(
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
    ):
        """
        Property 8: Risk Model Input Format Compliance
        Validates: Requirements 5.1, 5.4
        
        For any valid patient and vital signs data, the system should prepare
        model input with exactly the specified fields in the correct format.
        """
        # Ensure diastolic BP is less than systolic BP (medical constraint)
        assume(diastolic_bp < systolic_bp)

        self._setup_clean_db()
        db_session = next(get_test_db())
        
        try:
            # Create patient record
            patient = Patient(
                patient_id=patient_id,
                arrival_mode=arrival_mode,
                acuity_level=acuity_level,
                registration_time=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            db_session.add(patient)
            db_session.commit()
            
            # Create vital signs record
            vital_signs = VitalSigns(
                patient_id=patient_id,
                heart_rate=heart_rate,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                respiratory_rate=respiratory_rate,
                oxygen_saturation=oxygen_saturation,
                temperature=temperature,
                timestamp=datetime.utcnow()
            )
            db_session.add(vital_signs)
            db_session.commit()
            
            # Initialize service
            service = RiskAssessmentService(db_session)
            
            # Test prepare_model_input method
            model_input = service.prepare_model_input(patient, vital_signs)
            
            # Verify all expected fields are present (Requirement 5.1)
            assert set(model_input.keys()) == self.EXPECTED_INPUT_FIELDS, \
                f"Model input fields mismatch. Expected: {self.EXPECTED_INPUT_FIELDS}, Got: {set(model_input.keys())}"
            
            # Verify field values match the input data
            assert model_input["heart_rate"] == heart_rate
            assert model_input["systolic_bp"] == systolic_bp
            assert model_input["diastolic_bp"] == diastolic_bp
            assert model_input["respiratory_rate"] == respiratory_rate
            assert model_input["oxygen_saturation"] == oxygen_saturation
            assert model_input["temperature"] == temperature
            assert model_input["arrival_mode"] == arrival_mode.value
            assert model_input["acuity_level"] == acuity_level
            
            # Verify field types are correct
            assert isinstance(model_input["heart_rate"], float)
            assert isinstance(model_input["systolic_bp"], float)
            assert isinstance(model_input["diastolic_bp"], float)
            assert isinstance(model_input["respiratory_rate"], float)
            assert isinstance(model_input["oxygen_saturation"], float)
            assert isinstance(model_input["temperature"], float)
            assert isinstance(model_input["arrival_mode"], str)
            assert isinstance(model_input["acuity_level"], int)
            
        finally:
            db_session.close()

    @given(
        patient_id=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))
        ).filter(lambda x: x.strip()),
        arrival_mode=st.sampled_from([ArrivalModeEnum.AMBULANCE, ArrivalModeEnum.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=30, max_value=200, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=50, max_value=300, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=20, max_value=200, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=5, max_value=60, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=50, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=30, max_value=45, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    @pytest.mark.property_tests
    def test_input_validation_before_model_call(
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
    ):
        """
        Property 8: Risk Model Input Format Compliance (Validation)
        Validates: Requirements 5.4
        
        For any valid input data, the system should validate inputs are within
        expected ranges before processing.
        """
        # Ensure diastolic BP is less than systolic BP (medical constraint)
        assume(diastolic_bp < systolic_bp)

        self._setup_clean_db()
        db_session = next(get_test_db())
        
        try:
            # Initialize service
            service = RiskAssessmentService(db_session)
            
            # Test validate_model_inputs method (Requirement 5.4)
            validation_result = service.validate_model_inputs(
                heart_rate=heart_rate,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                respiratory_rate=respiratory_rate,
                oxygen_saturation=oxygen_saturation,
                temperature=temperature,
                arrival_mode=arrival_mode.value,
                acuity_level=acuity_level
            )
            
            # Valid inputs should pass validation
            assert validation_result["valid"] is True, \
                f"Valid inputs should pass validation. Errors: {validation_result['errors']}"
            assert len(validation_result["errors"]) == 0
            
            # Validation result should have expected structure
            assert "valid" in validation_result
            assert "errors" in validation_result
            assert "warnings" in validation_result
            
        finally:
            db_session.close()

    @given(
        # Generate out-of-range values for testing validation
        heart_rate=st.one_of(
            st.floats(min_value=0, max_value=29.9, allow_nan=False, allow_infinity=False),
            st.floats(min_value=200.1, max_value=500, allow_nan=False, allow_infinity=False)
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.property_tests
    def test_invalid_heart_rate_rejected(self, heart_rate):
        """
        Property 8: Risk Model Input Format Compliance (Invalid Heart Rate)
        Validates: Requirements 5.4
        
        For any heart rate outside valid range (30-200), validation should fail.
        """
        self._setup_clean_db()
        db_session = next(get_test_db())
        
        try:
            service = RiskAssessmentService(db_session)
            
            validation_result = service.validate_model_inputs(
                heart_rate=heart_rate,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
                arrival_mode="Walk-in",
                acuity_level=2
            )
            
            assert validation_result["valid"] is False, \
                f"Invalid heart rate {heart_rate} should fail validation"
            assert any("heart rate" in err.lower() for err in validation_result["errors"])
            
        finally:
            db_session.close()

    @given(
        acuity_level=st.one_of(
            st.integers(min_value=-100, max_value=0),
            st.integers(min_value=6, max_value=100)
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.property_tests
    def test_invalid_acuity_level_rejected(self, acuity_level):
        """
        Property 8: Risk Model Input Format Compliance (Invalid Acuity Level)
        Validates: Requirements 5.4
        
        For any acuity level outside valid range (1-5), validation should fail.
        """
        self._setup_clean_db()
        db_session = next(get_test_db())
        
        try:
            service = RiskAssessmentService(db_session)
            
            validation_result = service.validate_model_inputs(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
                arrival_mode="Walk-in",
                acuity_level=acuity_level
            )
            
            assert validation_result["valid"] is False, \
                f"Invalid acuity level {acuity_level} should fail validation"
            assert any("acuity" in err.lower() for err in validation_result["errors"])
            
        finally:
            db_session.close()

    @given(
        arrival_mode=st.text(min_size=1, max_size=20).filter(
            lambda x: x not in ["Ambulance", "Walk-in"]
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.property_tests
    def test_invalid_arrival_mode_rejected(self, arrival_mode):
        """
        Property 8: Risk Model Input Format Compliance (Invalid Arrival Mode)
        Validates: Requirements 5.4
        
        For any arrival mode not in ["Ambulance", "Walk-in"], validation should fail.
        """
        self._setup_clean_db()
        db_session = next(get_test_db())
        
        try:
            service = RiskAssessmentService(db_session)
            
            validation_result = service.validate_model_inputs(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
                arrival_mode=arrival_mode,
                acuity_level=2
            )
            
            assert validation_result["valid"] is False, \
                f"Invalid arrival mode '{arrival_mode}' should fail validation"
            assert any("arrival mode" in err.lower() for err in validation_result["errors"])
            
        finally:
            db_session.close()
