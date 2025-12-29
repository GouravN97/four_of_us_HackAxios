"""
Property-based tests for patient registration functionality.
Tests that patient registration and retrieval maintains data integrity.
"""

from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.models.api_models import (
    ArrivalMode,
    PatientRegistration,
    VitalSignsWithTimestamp,
)


class TestPatientRegistrationRoundTrip:
    """Property 1: Patient Registration Round Trip - Validates Requirements 1.1, 1.2"""

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
            max_value=datetime(2030, 12, 31),
            timezones=st.just(timezone.utc),
        ),
    )
    @pytest.mark.property_tests
    def test_patient_registration_round_trip(
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
        Property 1: Patient Registration Round Trip
        Validates: Requirements 1.1, 1.2

        For any valid patient registration data (patient ID, arrival mode,
        acuity level, and initial vital signs), registering the patient
        and then retrieving it should return exactly the same data.
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
        original_registration = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals,
        )

        # Test round trip: serialize to dict and back
        registration_dict = original_registration.model_dump()
        reconstructed_registration = PatientRegistration.model_validate(
            registration_dict
        )

        # Verify all fields match exactly
        assert (
            reconstructed_registration.patient_id
            == original_registration.patient_id
        )
        assert (
            reconstructed_registration.arrival_mode
            == original_registration.arrival_mode
        )
        assert (
            reconstructed_registration.acuity_level
            == original_registration.acuity_level
        )

        # Verify vital signs match exactly
        original_vitals = original_registration.initial_vitals
        reconstructed_vitals = reconstructed_registration.initial_vitals

        assert reconstructed_vitals.heart_rate == original_vitals.heart_rate
        assert reconstructed_vitals.systolic_bp == original_vitals.systolic_bp
        assert (
            reconstructed_vitals.diastolic_bp == original_vitals.diastolic_bp
        )
        assert (
            reconstructed_vitals.respiratory_rate
            == original_vitals.respiratory_rate
        )
        assert (
            reconstructed_vitals.oxygen_saturation
            == original_vitals.oxygen_saturation
        )
        assert reconstructed_vitals.temperature == original_vitals.temperature
        assert reconstructed_vitals.timestamp == original_vitals.timestamp

        # Verify complete object equality
        assert reconstructed_registration == original_registration

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
            max_value=datetime(2030, 12, 31),
            timezones=st.just(timezone.utc),
        ),
    )
    @pytest.mark.property_tests
    def test_patient_registration_json_round_trip(
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
        Property 1: Patient Registration Round Trip
        Validates: Requirements 1.1, 1.2

        For any valid patient registration data, serializing to JSON and
        deserializing should preserve all data exactly.
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
        original_registration = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals,
        )

        # Test JSON round trip
        json_str = original_registration.model_dump_json()
        reconstructed_registration = PatientRegistration.model_validate_json(
            json_str
        )

        # Verify complete object equality after JSON round trip
        assert reconstructed_registration == original_registration

        # Verify specific fields to ensure no data loss
        assert (
            reconstructed_registration.patient_id
            == original_registration.patient_id
        )
        assert (
            reconstructed_registration.arrival_mode
            == original_registration.arrival_mode
        )
        assert (
            reconstructed_registration.acuity_level
            == original_registration.acuity_level
        )

        # Verify vital signs are preserved exactly
        original_vitals = original_registration.initial_vitals
        reconstructed_vitals = reconstructed_registration.initial_vitals

        assert reconstructed_vitals.heart_rate == original_vitals.heart_rate
        assert reconstructed_vitals.systolic_bp == original_vitals.systolic_bp
        assert (
            reconstructed_vitals.diastolic_bp == original_vitals.diastolic_bp
        )
        assert (
            reconstructed_vitals.respiratory_rate
            == original_vitals.respiratory_rate
        )
        assert (
            reconstructed_vitals.oxygen_saturation
            == original_vitals.oxygen_saturation
        )
        assert reconstructed_vitals.temperature == original_vitals.temperature
        assert reconstructed_vitals.timestamp == original_vitals.timestamp