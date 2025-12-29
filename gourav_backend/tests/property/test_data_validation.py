"""
Property-based tests for data validation.
Tests that invalid data outside medical ranges is rejected with descriptive error messages.
"""

from datetime import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from src.models.api_models import (
    ArrivalMode,
    PatientRegistration,
    VitalSignsUpdate,
    VitalSignsWithTimestamp,
)


class TestInvalidDataRejection:
    """Property 4: Invalid Data Rejection - Validates Requirements 1.5, 2.1, 6.1"""

    @given(
        heart_rate=st.one_of(
            st.floats(min_value=-1000, max_value=29.9),  # Below valid range
            st.floats(min_value=200.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_heart_rate_rejection(self, heart_rate):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any heart rate outside the valid medical range (30-200 bpm),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=heart_rate,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "heart_rate" in error_str.lower()

    @given(
        systolic_bp=st.one_of(
            st.floats(min_value=-1000, max_value=49.9),  # Below valid range
            st.floats(min_value=300.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_systolic_bp_rejection(self, systolic_bp):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any systolic blood pressure outside the valid medical range (50-300 mmHg),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=systolic_bp,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "systolic_bp" in error_str.lower()

    @given(
        diastolic_bp=st.one_of(
            st.floats(min_value=-1000, max_value=19.9),  # Below valid range
            st.floats(min_value=200.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_diastolic_bp_rejection(self, diastolic_bp):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any diastolic blood pressure outside the valid medical range (20-200 mmHg),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=diastolic_bp,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "diastolic_bp" in error_str.lower()

    @given(
        respiratory_rate=st.one_of(
            st.floats(min_value=-1000, max_value=4.9),  # Below valid range
            st.floats(min_value=60.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_respiratory_rate_rejection(self, respiratory_rate):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any respiratory rate outside the valid medical range (5-60 breaths/min),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=respiratory_rate,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "respiratory_rate" in error_str.lower()

    @given(
        oxygen_saturation=st.one_of(
            st.floats(min_value=-1000, max_value=49.9),  # Below valid range
            st.floats(min_value=100.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_oxygen_saturation_rejection(self, oxygen_saturation):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any oxygen saturation outside the valid medical range (50-100%),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=oxygen_saturation,
                temperature=36.5,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "oxygen_saturation" in error_str.lower()

    @given(
        temperature=st.one_of(
            st.floats(min_value=-1000, max_value=29.9),  # Below valid range
            st.floats(min_value=45.1, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_temperature_rejection(self, temperature):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any temperature outside the valid medical range (30-45°C),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=temperature,
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "temperature" in error_str.lower()

    @given(
        acuity_level=st.one_of(
            st.integers(min_value=-1000, max_value=0),  # Below valid range
            st.integers(min_value=6, max_value=1000),  # Above valid range
        )
    )
    @pytest.mark.property_tests
    def test_invalid_acuity_level_rejection(self, acuity_level):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any acuity level outside the valid range (1-5),
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            PatientRegistration(
                patient_id="P12345",
                arrival_mode=ArrivalMode.AMBULANCE,
                acuity_level=acuity_level,
                initial_vitals=VitalSignsWithTimestamp(
                    heart_rate=85.0,
                    systolic_bp=140.0,
                    diastolic_bp=90.0,
                    respiratory_rate=18.0,
                    oxygen_saturation=96.0,
                    temperature=37.2,
                    timestamp=datetime.now(),
                ),
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "acuity_level" in error_str.lower()

    @given(
        # Generate systolic BP in valid range, then make diastolic >= systolic but within range
        systolic_bp=st.floats(min_value=50, max_value=150),  # Leave room for diastolic
        diastolic_offset=st.floats(
            min_value=0, max_value=50
        ),  # Smaller offset to stay in range
    )
    @pytest.mark.property_tests
    def test_blood_pressure_relationship_rejection(self, systolic_bp, diastolic_offset):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any case where diastolic blood pressure is greater than or equal to systolic,
        the system should reject the data with a descriptive error message.
        """
        diastolic_bp = systolic_bp + diastolic_offset  # Ensure diastolic >= systolic

        # Skip if diastolic would exceed maximum allowed value
        if diastolic_bp > 200:
            return

        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Verify error message mentions blood pressure relationship
        error_str = str(exc_info.value)
        assert "diastolic" in error_str.lower() and "systolic" in error_str.lower()

    @given(patient_id=st.text(min_size=0, max_size=0))  # Empty string
    @pytest.mark.property_tests
    def test_empty_patient_id_rejection(self, patient_id):
        """
        **Feature: patient-risk-classifier, Property 4: Invalid Data Rejection**
        **Validates: Requirements 1.5, 2.1, 6.1**

        For any empty patient ID,
        the system should reject the data with a descriptive error message.
        """
        with pytest.raises(ValidationError) as exc_info:
            PatientRegistration(
                patient_id=patient_id,
                arrival_mode=ArrivalMode.AMBULANCE,
                acuity_level=3,
                initial_vitals=VitalSignsWithTimestamp(
                    heart_rate=85.0,
                    systolic_bp=140.0,
                    diastolic_bp=90.0,
                    respiratory_rate=18.0,
                    oxygen_saturation=96.0,
                    temperature=37.2,
                    timestamp=datetime.now(),
                ),
            )

        # Verify error message contains field name
        error_str = str(exc_info.value)
        assert "patient_id" in error_str.lower()