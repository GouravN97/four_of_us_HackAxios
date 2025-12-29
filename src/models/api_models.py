"""
Pydantic models for API requests and responses.
Includes medical range validation for vital signs data.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ArrivalMode(str, Enum):
    """Patient arrival mode enumeration."""
    AMBULANCE = "Ambulance"
    WALK_IN = "Walk-in"


class VitalSignsBase(BaseModel):
    """Base model for vital signs with medical range validation."""
    
    heart_rate: float = Field(
        ..., 
        ge=30, 
        le=200, 
        description="Heart rate in beats per minute (30-200 bpm)"
    )
    systolic_bp: float = Field(
        ..., 
        ge=50, 
        le=300, 
        description="Systolic blood pressure in mmHg (50-300 mmHg)"
    )
    diastolic_bp: float = Field(
        ..., 
        ge=20, 
        le=200, 
        description="Diastolic blood pressure in mmHg (20-200 mmHg)"
    )
    respiratory_rate: float = Field(
        ..., 
        ge=5, 
        le=60, 
        description="Respiratory rate in breaths per minute (5-60 breaths/min)"
    )
    oxygen_saturation: float = Field(
        ..., 
        ge=50, 
        le=100, 
        description="Oxygen saturation percentage (50-100%)"
    )
    temperature: float = Field(
        ..., 
        ge=30, 
        le=45, 
        description="Body temperature in Celsius (30-45°C)"
    )

    @field_validator('diastolic_bp')
    @classmethod
    def validate_blood_pressure_relationship(cls, v, info):
        """Ensure diastolic BP is less than systolic BP."""
        if 'systolic_bp' in info.data and v >= info.data['systolic_bp']:
            raise ValueError('Diastolic blood pressure must be less than systolic blood pressure')
        return v

    model_config = ConfigDict()


class VitalSignsWithTimestamp(VitalSignsBase):
    """Vital signs model with timestamp for initial registration."""
    
    timestamp: datetime = Field(
        ...,
        description="Timestamp when vital signs were recorded"
    )


class VitalSignsUpdate(VitalSignsBase):
    """Model for vital signs update requests."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "heart_rate": 72.0,
                "systolic_bp": 120.0,
                "diastolic_bp": 80.0,
                "respiratory_rate": 16.0,
                "oxygen_saturation": 98.0,
                "temperature": 36.5
            }
        }
    )


class PatientRegistration(BaseModel):
    """Model for patient registration requests."""
    
    patient_id: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Unique patient identifier"
    )
    arrival_mode: ArrivalMode = Field(
        ...,
        description="How the patient arrived at the hospital"
    )
    acuity_level: int = Field(
        ..., 
        ge=1, 
        le=5,
        description="Clinical severity rating from 1 (least severe) to 5 (most severe)"
    )
    initial_vitals: VitalSignsWithTimestamp = Field(
        ...,
        description="Initial vital signs measurements with timestamp"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "P12345",
                "arrival_mode": "Ambulance",
                "acuity_level": 3,
                "initial_vitals": {
                    "heart_rate": 85.0,
                    "systolic_bp": 140.0,
                    "diastolic_bp": 90.0,
                    "respiratory_rate": 18.0,
                    "oxygen_saturation": 96.0,
                    "temperature": 37.2,
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    )


class RiskAssessment(BaseModel):
    """Model for risk assessment data."""
    
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Numerical risk score between 0 and 1"
    )
    risk_flag: bool = Field(
        ...,
        description="Boolean indicator of high deterioration risk"
    )
    assessment_time: datetime = Field(
        ...,
        description="When the risk assessment was performed"
    )
    model_version: Optional[str] = Field(
        None,
        description="Version of the ML model used for assessment"
    )

    model_config = ConfigDict(
        protected_namespaces=()  # Allow model_version field
    )


class PatientStatus(BaseModel):
    """Model for current patient status responses."""
    
    patient_id: str = Field(..., description="Unique patient identifier")
    arrival_mode: ArrivalMode = Field(..., description="Patient arrival mode")
    acuity_level: int = Field(..., description="Clinical severity rating")
    current_vitals: VitalSignsWithTimestamp = Field(
        ..., 
        description="Most recent vital signs"
    )
    current_risk: RiskAssessment = Field(
        ..., 
        description="Most recent risk assessment"
    )
    registration_time: datetime = Field(
        ..., 
        description="When the patient was registered"
    )
    last_updated: datetime = Field(
        ..., 
        description="When the patient data was last updated"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "P12345",
                "arrival_mode": "Ambulance",
                "acuity_level": 3,
                "current_vitals": {
                    "heart_rate": 78.0,
                    "systolic_bp": 135.0,
                    "diastolic_bp": 85.0,
                    "respiratory_rate": 17.0,
                    "oxygen_saturation": 97.0,
                    "temperature": 36.8,
                    "timestamp": "2024-01-15T11:00:00Z"
                },
                "current_risk": {
                    "risk_score": 0.25,
                    "risk_flag": False,
                    "assessment_time": "2024-01-15T11:00:05Z",
                    "model_version": "v1.2.3"
                },
                "registration_time": "2024-01-15T10:30:00Z",
                "last_updated": "2024-01-15T11:00:00Z"
            }
        }
    )


class HistoricalDataPoint(BaseModel):
    """Model for historical vital signs and risk assessment data."""
    
    vitals: VitalSignsWithTimestamp = Field(
        ..., 
        description="Vital signs at this point in time"
    )
    risk_assessment: RiskAssessment = Field(
        ..., 
        description="Risk assessment at this point in time"
    )


class HistoricalDataResponse(BaseModel):
    """Model for historical data query responses."""
    
    patient_id: str = Field(..., description="Patient identifier")
    start_time: datetime = Field(..., description="Start of requested time range")
    end_time: datetime = Field(..., description="End of requested time range")
    data_points: list[HistoricalDataPoint] = Field(
        ..., 
        description="Chronologically ordered historical data"
    )
    total_count: int = Field(
        ..., 
        description="Total number of data points in response"
    )


class HighRiskPatient(BaseModel):
    """Model for high-risk patient query responses."""
    
    patient_id: str = Field(..., description="Patient identifier")
    arrival_mode: ArrivalMode = Field(..., description="Patient arrival mode")
    acuity_level: int = Field(..., description="Clinical severity rating")
    current_risk_score: float = Field(..., description="Current risk score")
    last_assessment_time: datetime = Field(
        ..., 
        description="When the risk was last assessed"
    )
    registration_time: datetime = Field(
        ..., 
        description="When the patient was registered"
    )


class HighRiskPatientsResponse(BaseModel):
    """Model for high-risk patients list response."""
    
    patients: list[HighRiskPatient] = Field(
        ..., 
        description="List of high-risk patients"
    )
    total_count: int = Field(
        ..., 
        description="Total number of high-risk patients"
    )
    query_time: datetime = Field(
        ..., 
        description="When the query was executed"
    )


class ErrorResponse(BaseModel):
    """Model for error responses."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(
        None, 
        description="Additional error details (for validation errors)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Invalid vital signs data provided",
                "details": {
                    "heart_rate": ["Value must be between 30 and 200"],
                    "temperature": ["Value must be between 30 and 45"]
                },
                "timestamp": "2024-01-15T11:00:00Z"
            }
        }
    )


class SuccessResponse(BaseModel):
    """Model for successful operation responses."""
    
    success: bool = Field(True, description="Operation success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Additional response data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the operation completed"
    )