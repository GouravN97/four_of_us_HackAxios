"""
SQLAlchemy database models for the Patient Risk Classifier system.
Defines Patient, VitalSigns, and RiskAssessment entities with proper relationships and constraints.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class ArrivalModeEnum(PyEnum):
    """Enumeration for patient arrival modes."""
    AMBULANCE = "Ambulance"
    WALK_IN = "Walk-in"


class Patient(Base):
    """
    Patient entity representing registered patients in the system.
    
    Requirements covered:
    - 1.1: Store patient ID, arrival mode, and initial acuity level
    - 1.4: Assign unique identifier to each patient record
    """
    __tablename__ = "patients"

    # Primary key - using patient_id as provided by the system
    patient_id: Mapped[str] = mapped_column(
        String(50), 
        primary_key=True,
        comment="Unique patient identifier provided during registration"
    )
    
    # Patient attributes
    arrival_mode: Mapped[ArrivalModeEnum] = mapped_column(
        Enum(ArrivalModeEnum),
        nullable=False,
        comment="How the patient arrived at the hospital"
    )
    
    acuity_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Clinical severity rating from 1 (least severe) to 5 (most severe)"
    )
    
    # Timestamps
    registration_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the patient was registered in the system"
    )
    
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When the patient record was last updated"
    )

    # Relationships
    vital_signs: Mapped[List["VitalSigns"]] = relationship(
        "VitalSigns",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="VitalSigns.timestamp.desc()"
    )
    
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="RiskAssessment.assessment_time.desc()"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "acuity_level >= 1 AND acuity_level <= 5",
            name="check_acuity_level_range"
        ),
    )

    def __repr__(self) -> str:
        return f"<Patient(patient_id='{self.patient_id}', arrival_mode='{self.arrival_mode.value}', acuity_level={self.acuity_level})>"


class VitalSigns(Base):
    """
    VitalSigns entity for time-series storage of patient vital signs.
    
    Requirements covered:
    - 1.2: Store initial vital signs with validation
    - 2.2: Store vital signs with timestamps
    - 2.4: Maintain complete history of all vital sign measurements
    """
    __tablename__ = "vital_signs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for this vital signs record"
    )
    
    # Foreign key to patient
    patient_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the patient these vital signs belong to"
    )
    
    # Vital signs measurements with medical validation ranges
    heart_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Heart rate in beats per minute (30-200 bpm)"
    )
    
    systolic_bp: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Systolic blood pressure in mmHg (50-300 mmHg)"
    )
    
    diastolic_bp: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Diastolic blood pressure in mmHg (20-200 mmHg)"
    )
    
    respiratory_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Respiratory rate in breaths per minute (5-60 breaths/min)"
    )
    
    oxygen_saturation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Oxygen saturation percentage (50-100%)"
    )
    
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Body temperature in Celsius (30-45°C)"
    )
    
    # Timestamp and metadata
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When these vital signs were recorded"
    )
    
    recorded_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Who recorded these vital signs (optional)"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this record was created in the database"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="vital_signs"
    )
    
    risk_assessments: Mapped[List["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="vital_signs",
        cascade="all, delete-orphan"
    )

    # Constraints for medical validation ranges
    __table_args__ = (
        CheckConstraint(
            "heart_rate >= 30 AND heart_rate <= 200",
            name="check_heart_rate_range"
        ),
        CheckConstraint(
            "systolic_bp >= 50 AND systolic_bp <= 300",
            name="check_systolic_bp_range"
        ),
        CheckConstraint(
            "diastolic_bp >= 20 AND diastolic_bp <= 200",
            name="check_diastolic_bp_range"
        ),
        CheckConstraint(
            "diastolic_bp < systolic_bp",
            name="check_bp_relationship"
        ),
        CheckConstraint(
            "respiratory_rate >= 5 AND respiratory_rate <= 60",
            name="check_respiratory_rate_range"
        ),
        CheckConstraint(
            "oxygen_saturation >= 50 AND oxygen_saturation <= 100",
            name="check_oxygen_saturation_range"
        ),
        CheckConstraint(
            "temperature >= 30 AND temperature <= 45",
            name="check_temperature_range"
        ),
        # Index for efficient time-series queries
        {"comment": "Time-series storage optimized for vital signs history queries"}
    )

    def __repr__(self) -> str:
        return f"<VitalSigns(id='{self.id}', patient_id='{self.patient_id}', timestamp='{self.timestamp}')>"


class RiskAssessment(Base):
    """
    RiskAssessment entity for storing ML model risk predictions.
    
    Requirements covered:
    - 3.2: Store risk score and risk flag with timestamps
    - 3.3: Associate risk assessments with vital signs used for calculation
    """
    __tablename__ = "risk_assessments"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for this risk assessment"
    )
    
    # Foreign keys
    patient_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the patient this assessment belongs to"
    )
    
    vital_signs_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vital_signs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the vital signs used for this assessment"
    )
    
    # Risk assessment results
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Numerical risk score between 0 and 1"
    )
    
    risk_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Boolean indicator of high deterioration risk"
    )
    
    # Timestamps and metadata
    assessment_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the risk assessment was performed"
    )
    
    model_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Version of the ML model used for assessment"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this record was created in the database"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="risk_assessments"
    )
    
    vital_signs: Mapped["VitalSigns"] = relationship(
        "VitalSigns",
        back_populates="risk_assessments"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0.0 AND risk_score <= 1.0",
            name="check_risk_score_range"
        ),
        # Unique constraint to prevent duplicate assessments for same vital signs
        UniqueConstraint(
            "vital_signs_id",
            name="unique_assessment_per_vital_signs"
        ),
        # Index for efficient risk-based queries
        {"comment": "Risk assessment storage with proper linkage to vital signs"}
    )

    def __repr__(self) -> str:
        return f"<RiskAssessment(id='{self.id}', patient_id='{self.patient_id}', risk_score={self.risk_score}, risk_flag={self.risk_flag})>"