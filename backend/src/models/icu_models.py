"""
SQLAlchemy database models for ICU management.
Tracks ICU admissions and occupancy for load prediction.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db_models import Base


class ICUAdmissionStatus(str, Enum):
    """ICU admission status enumeration."""
    ADMITTED = "ADMITTED"
    DISCHARGED = "DISCHARGED"
    TRANSFERRED = "TRANSFERRED"


class ICUAdmission(Base):
    """
    ICU Admission entity for tracking patients admitted to ICU.
    Patients with HIGH risk classification are automatically admitted.
    """
    __tablename__ = "icu_admissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()),
        comment="Unique identifier for this ICU admission"
    )
    patient_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("patients.patient_id"), nullable=False, index=True,
        comment="Reference to the patient"
    )
    
    # Admission details
    admission_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True,
        comment="When the patient was admitted to ICU"
    )
    discharge_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="When the patient was discharged from ICU"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ICUAdmissionStatus.ADMITTED.value,
        comment="Current admission status"
    )
    
    # Risk information at admission
    risk_score_at_admission: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Risk score when admitted to ICU"
    )
    risk_category_at_admission: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Risk category when admitted (should be HIGH)"
    )
    
    # Bed assignment
    bed_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="Assigned ICU bed number"
    )
    
    # Notes
    admission_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Reason for ICU admission"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<ICUAdmission(id='{self.id}', patient_id='{self.patient_id}', status='{self.status}')>"


class ICUOccupancyLog(Base):
    """
    Hourly ICU occupancy log for load prediction model.
    Records the number of patients in ICU at each hour.
    """
    __tablename__ = "icu_occupancy_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True,
        comment="Hour timestamp for this occupancy record"
    )
    patient_count: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Number of patients in ICU at this hour"
    )
    beds_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60,
        comment="Total ICU beds available"
    )
    beds_occupied: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Number of beds occupied"
    )
    
    # Additional metrics
    high_risk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of high-risk patients"
    )
    new_admissions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="New admissions in this hour"
    )
    discharges: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Discharges in this hour"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<ICUOccupancyLog(timestamp='{self.timestamp}', count={self.patient_count})>"
