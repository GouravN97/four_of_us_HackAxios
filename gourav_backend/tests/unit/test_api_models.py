"""
Unit tests for API models and validation.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.api_models import (
    ArrivalMode,
    PatientRegistration,
    VitalSignsUpdate,
    VitalSignsWithTimestamp,
)


class TestVitalSignsValidation:
    """Test vital signs validation ranges."""

    def test_valid_vital_signs(self):
        """Test that valid vital signs are accepted."""
        valid_vitals = VitalSignsUpdate(
            heart_rate=72.0,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            oxygen_saturation=98.0,
            temperature=36.5,
        )

        assert valid_vitals.heart_rate == 72.0
        assert valid_vitals.systolic_bp == 120.0
        assert valid_vitals.diastolic_bp == 80.0
        assert valid_vitals.respiratory_rate == 16.0
        assert valid_vitals.oxygen_saturation == 98.0
        assert valid_vitals.temperature == 36.5

    def test_heart_rate_validation(self):
        """Test heart rate range validation."""
        # Test below minimum
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=25.0,  # Below 30
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )
        assert "heart_rate" in str(exc_info.value)

        # Test above maximum
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=205.0,  # Above 200
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )
        assert "heart_rate" in str(exc_info.value)

    def test_blood_pressure_validation(self):
        """Test blood pressure range and relationship validation."""
        # Test systolic BP below minimum
        with pytest.raises(ValidationError):
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=45.0,  # Below 50
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )

        # Test diastolic BP above systolic BP
        with pytest.raises(ValidationError) as exc_info:
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=125.0,  # Above systolic
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=36.5,
            )
        assert "Diastolic blood pressure must be less than systolic" in str(
            exc_info.value
        )

    def test_temperature_validation(self):
        """Test temperature range validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=25.0,  # Below 30
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=98.0,
                temperature=50.0,  # Above 45
            )

    def test_oxygen_saturation_validation(self):
        """Test oxygen saturation range validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=45.0,  # Below 50
                temperature=36.5,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            VitalSignsUpdate(
                heart_rate=72.0,
                systolic_bp=120.0,
                diastolic_bp=80.0,
                respiratory_rate=16.0,
                oxygen_saturation=105.0,  # Above 100
                temperature=36.5,
            )


class TestPatientRegistration:
    """Test patient registration model validation."""

    def test_valid_patient_registration(self):
        """Test that valid patient registration is accepted."""
        registration = PatientRegistration(
            patient_id="P12345",
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

        assert registration.patient_id == "P12345"
        assert registration.arrival_mode == ArrivalMode.AMBULANCE
        assert registration.acuity_level == 3
        assert registration.initial_vitals.heart_rate == 85.0

    def test_acuity_level_validation(self):
        """Test acuity level range validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            PatientRegistration(
                patient_id="P12345",
                arrival_mode=ArrivalMode.AMBULANCE,
                acuity_level=0,  # Below 1
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

        # Test above maximum
        with pytest.raises(ValidationError):
            PatientRegistration(
                patient_id="P12345",
                arrival_mode=ArrivalMode.AMBULANCE,
                acuity_level=6,  # Above 5
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

    def test_patient_id_validation(self):
        """Test patient ID validation."""
        # Test empty patient ID
        with pytest.raises(ValidationError):
            PatientRegistration(
                patient_id="",  # Empty string
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

    def test_arrival_mode_validation(self):
        """Test arrival mode enum validation."""
        # Test invalid arrival mode
        with pytest.raises(ValidationError):
            PatientRegistration(
                patient_id="P12345",
                arrival_mode="Invalid",  # Not in enum
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


class TestEdgeCases:
    """Test edge cases and boundary values."""

    def test_boundary_values(self):
        """Test boundary values for all vital signs."""
        # Test minimum valid values
        min_vitals = VitalSignsUpdate(
            heart_rate=30.0,
            systolic_bp=50.0,
            diastolic_bp=20.0,
            respiratory_rate=5.0,
            oxygen_saturation=50.0,
            temperature=30.0,
        )
        assert min_vitals.heart_rate == 30.0

        # Test maximum valid values
        max_vitals = VitalSignsUpdate(
            heart_rate=200.0,
            systolic_bp=300.0,
            diastolic_bp=200.0,
            respiratory_rate=60.0,
            oxygen_saturation=100.0,
            temperature=45.0,
        )
        assert max_vitals.heart_rate == 200.0
