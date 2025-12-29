"""
Unit tests for SQLAlchemy database models.
Tests model instantiation, relationships, and constraints.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.models.db_models import (
    ArrivalModeEnum,
    Base,
    Patient,
    RiskAssessment,
    VitalSigns,
)


class TestPatientModel:
    """Test Patient database model."""

    def test_patient_creation(self):
        """Test creating a valid Patient instance."""
        patient = Patient(
            patient_id="P12345", arrival_mode=ArrivalModeEnum.AMBULANCE, acuity_level=3
        )

        assert patient.patient_id == "P12345"
        assert patient.arrival_mode == ArrivalModeEnum.AMBULANCE
        assert patient.acuity_level == 3
        assert patient.vital_signs == []
        assert patient.risk_assessments == []

    def test_patient_repr(self):
        """Test Patient string representation."""
        patient = Patient(
            patient_id="P12345", arrival_mode=ArrivalModeEnum.WALK_IN, acuity_level=2
        )

        expected = (
            "<Patient(patient_id='P12345', arrival_mode='Walk-in', acuity_level=2)>"
        )
        assert repr(patient) == expected


class TestVitalSignsModel:
    """Test VitalSigns database model."""

    def test_vital_signs_creation(self):
        """Test creating a valid VitalSigns instance."""
        timestamp = datetime.now(timezone.utc)
        vital_signs = VitalSigns(
            patient_id="P12345",
            heart_rate=72.0,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            oxygen_saturation=98.0,
            temperature=36.5,
            timestamp=timestamp,
            recorded_by="Nurse Smith",
        )

        assert vital_signs.patient_id == "P12345"
        assert vital_signs.heart_rate == 72.0
        assert vital_signs.systolic_bp == 120.0
        assert vital_signs.diastolic_bp == 80.0
        assert vital_signs.respiratory_rate == 16.0
        assert vital_signs.oxygen_saturation == 98.0
        assert vital_signs.temperature == 36.5
        assert vital_signs.timestamp == timestamp
        assert vital_signs.recorded_by == "Nurse Smith"

    def test_vital_signs_repr(self):
        """Test VitalSigns string representation."""
        vital_signs_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        vital_signs = VitalSigns(
            id=vital_signs_id,
            patient_id="P12345",
            heart_rate=72.0,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            oxygen_saturation=98.0,
            temperature=36.5,
            timestamp=timestamp,
        )

        expected = f"<VitalSigns(id='{vital_signs_id}', patient_id='P12345', timestamp='{timestamp}')>"
        assert repr(vital_signs) == expected


class TestRiskAssessmentModel:
    """Test RiskAssessment database model."""

    def test_risk_assessment_creation(self):
        """Test creating a valid RiskAssessment instance."""
        assessment_time = datetime.now(timezone.utc)
        vital_signs_id = uuid4()

        risk_assessment = RiskAssessment(
            patient_id="P12345",
            vital_signs_id=vital_signs_id,
            risk_score=0.25,
            risk_flag=False,
            assessment_time=assessment_time,
            model_version="v1.2.3",
        )

        assert risk_assessment.patient_id == "P12345"
        assert risk_assessment.vital_signs_id == vital_signs_id
        assert risk_assessment.risk_score == 0.25
        assert risk_assessment.risk_flag is False
        assert risk_assessment.assessment_time == assessment_time
        assert risk_assessment.model_version == "v1.2.3"

    def test_risk_assessment_repr(self):
        """Test RiskAssessment string representation."""
        assessment_id = uuid4()
        vital_signs_id = uuid4()
        assessment_time = datetime.now(timezone.utc)

        risk_assessment = RiskAssessment(
            id=assessment_id,
            patient_id="P12345",
            vital_signs_id=vital_signs_id,
            risk_score=0.75,
            risk_flag=True,
            assessment_time=assessment_time,
        )

        expected = f"<RiskAssessment(id='{assessment_id}', patient_id='P12345', risk_score=0.75, risk_flag=True)>"
        assert repr(risk_assessment) == expected


class TestModelRelationships:
    """Test relationships between models."""

    def test_patient_vital_signs_relationship(self):
        """Test Patient to VitalSigns relationship setup."""
        patient = Patient(
            patient_id="P12345", arrival_mode=ArrivalModeEnum.AMBULANCE, acuity_level=3
        )

        vital_signs = VitalSigns(
            patient_id="P12345",
            heart_rate=72.0,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            oxygen_saturation=98.0,
            temperature=36.5,
            timestamp=datetime.now(timezone.utc),
        )

        # Test that relationships are properly configured
        assert hasattr(patient, "vital_signs")
        assert hasattr(vital_signs, "patient")
        assert hasattr(patient, "risk_assessments")

    def test_vital_signs_risk_assessment_relationship(self):
        """Test VitalSigns to RiskAssessment relationship setup."""
        vital_signs_id = uuid4()

        vital_signs = VitalSigns(
            id=vital_signs_id,
            patient_id="P12345",
            heart_rate=72.0,
            systolic_bp=120.0,
            diastolic_bp=80.0,
            respiratory_rate=16.0,
            oxygen_saturation=98.0,
            temperature=36.5,
            timestamp=datetime.now(timezone.utc),
        )

        risk_assessment = RiskAssessment(
            patient_id="P12345",
            vital_signs_id=vital_signs_id,
            risk_score=0.25,
            risk_flag=False,
            assessment_time=datetime.now(timezone.utc),
        )

        # Test that relationships are properly configured
        assert hasattr(vital_signs, "risk_assessments")
        assert hasattr(risk_assessment, "vital_signs")
        assert hasattr(risk_assessment, "patient")


class TestEnumValues:
    """Test enumeration values."""

    def test_arrival_mode_enum_values(self):
        """Test ArrivalModeEnum values."""
        assert ArrivalModeEnum.AMBULANCE.value == "Ambulance"
        assert ArrivalModeEnum.WALK_IN.value == "Walk-in"

        # Test that we can create patients with both enum values
        patient1 = Patient(
            patient_id="P1", arrival_mode=ArrivalModeEnum.AMBULANCE, acuity_level=1
        )

        patient2 = Patient(
            patient_id="P2", arrival_mode=ArrivalModeEnum.WALK_IN, acuity_level=2
        )

        assert patient1.arrival_mode == ArrivalModeEnum.AMBULANCE
        assert patient2.arrival_mode == ArrivalModeEnum.WALK_IN
