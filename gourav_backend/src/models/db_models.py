"""
SQLAlchemy database models for the Patient Risk Classifier system.
Defines Patient, VitalSigns, and RiskAssessment entities with proper relationships.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class ArrivalModeEnum(str, Enum):
    """Patient arrival mode enumeration for database storage."""
    AMBULANCE = "Ambulance"
    WALK_IN = "Walk-in"


class Patient(Base):
    """
    Patient entity representing registered patients in the system.
    
    Stores basic patient information including arrival mode and acuity level.
    Related to VitalSigns and RiskAssessment records.
    """
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, index=True,
        comment="Unique patient identifier"
    )
    arrival_mode: Mapped[ArrivalModeEnum] = mapped_column(
        SQLEnum(ArrivalModeEnum), nullable=False,
        comment="How the patient arrived at the hospital"
    )
    acuity_level: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Clinical severity rating from 1 (least severe) to 5 (most severe)"
    )
    registration_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
        comment="When the patient was registered in the system"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
        comment="When the patient record was last updated"
    )

    # Relationships
    vital_signs: Mapped[List["VitalSigns"]] = relationship(
        "VitalSigns", back_populates="patient", cascade="all, delete-orphan",
        order_by="VitalSigns.timestamp.desc()"
    )
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment", back_populates="patient", cascade="all, delete-orphan",
        order_by="RiskAssessment.assessment_time.desc()"
    )

    def __repr__(self) -> str:
        return (
            f"<Patient(patient_id='{self.patient_id}', "
            f"arrival_mode='{self.arrival_mode}', "
            f"acuity_level={self.acuity_level})>"
        )


class VitalSigns(Base):
    """
    VitalSigns entity for time-series storage of patient vital signs.
    
    Stores all vital signs measurements with timestamps for historical tracking.
    Each record is linked to a specific patient.
    """
    __tablename__ = "vital_signs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()),
        comment="Unique identifier for this vital signs record"
    )
    patient_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("patients.patient_id"), nullable=False, index=True,
        comment="Reference to the patient these vital signs belong to"
    )
    
    # Vital signs measurements with medical range constraints
    heart_rate: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Heart rate in beats per minute (30-200 bpm)"
    )
    systolic_bp: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Systolic blood pressure in mmHg (50-300 mmHg)"
    )
    diastolic_bp: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Diastolic blood pressure in mmHg (20-200 mmHg)"
    )
    respiratory_rate: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Respiratory rate in breaths per minute (5-60 breaths/min)"
    )
    oxygen_saturation: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Oxygen saturation percentage (50-100%)"
    )
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Body temperature in Celsius (30-45°C)"
    )
    
    # Metadata
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True,
        comment="When these vital signs were recorded"
    )
    recorded_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Who recorded these vital signs (optional)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
        comment="When this record was created in the system"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="vital_signs")
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment", back_populates="vital_signs", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<VitalSigns(id='{self.id}', patient_id='{self.patient_id}', "
            f"timestamp='{self.timestamp}')>"
        )


class RiskAssessment(Base):
    """
    RiskAssessment entity for storing ML model risk predictions.
    
    Stores both numerical risk scores and boolean risk flags from the ML model.
    Each assessment is linked to specific patient and vital signs records.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()),
        comment="Unique identifier for this risk assessment"
    )
    patient_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("patients.patient_id"), nullable=False, index=True,
        comment="Reference to the patient this assessment belongs to"
    )
    vital_signs_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vital_signs.id"), nullable=False, index=True,
        comment="Reference to the vital signs used for this assessment"
    )
    
    # Risk assessment results
    risk_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Numerical risk score between 0.0 and 1.0"
    )
    risk_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False,
        comment="Boolean indicator of high deterioration risk"
    )
    
    # Assessment metadata
    assessment_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True,
        comment="When the risk assessment was performed"
    )
    model_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Version of the ML model used for this assessment"
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Time taken to process this assessment in milliseconds"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Error message if assessment failed (for debugging)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
        comment="When this record was created in the system"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="risk_assessments")
    vital_signs: Mapped["VitalSigns"] = relationship("VitalSigns", back_populates="risk_assessments")

    def __repr__(self) -> str:
        return (
            f"<RiskAssessment(id='{self.id}', patient_id='{self.patient_id}', "
            f"risk_score={self.risk_score}, risk_flag={self.risk_flag})>"
        )

    @property
    def is_high_risk(self) -> bool:
        """Convenience property to check if this assessment indicates high risk."""
        return self.risk_flag

    @property
    def risk_level(self) -> str:
        """Convenience property to get human-readable risk level."""
        if self.risk_flag:
            return "HIGH"
        elif self.risk_score >= 0.5:
            return "MEDIUM"
        elif self.risk_score >= 0.25:
            return "LOW"
        else:
            return "MINIMAL"