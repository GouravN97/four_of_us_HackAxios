# Patient Risk Classifier Backend

A real-time patient deterioration risk assessment system for hospital environments. This backend API continuously monitors patient vital signs and uses machine learning to predict short-term deterioration risk, enabling healthcare providers to prioritize critical cases.

## 🏥 Features

- **Real-time Risk Assessment**: ML-powered continuous monitoring with risk scoring
- **Vital Signs Management**: Comprehensive time-series storage, validation, and historical queries with REST API
- **Medical Validation**: Healthcare standards-compliant input validation with medical ranges and business rules
- **Historical Analytics**: Query patient data and risk trends over time with chronological ordering and time-range filtering
- **RESTful API**: Clean, documented endpoints with comprehensive data models and automatic OpenAPI documentation
- **Automatic Risk Triggering**: Vital signs updates automatically trigger ML risk assessments
- **Graceful Degradation**: System continues storing vital signs even when ML model is unavailable
- **Property-Based Testing**: Robust validation through automated correctness testing
- **Business Logic Services**: Complete service layer with patient, vital signs, and risk assessment management
- **Error Handling**: Comprehensive exception handling with structured error responses

## 📊 Vital Signs Validation

The system validates all vital signs against medical standards:

| Vital Sign | Valid Range | Unit |
|------------|-------------|------|
| Heart Rate | 30-200 | bpm |
| Systolic BP | 50-300 | mmHg |
| Diastolic BP | 20-200 | mmHg |
| Respiratory Rate | 5-60 | breaths/min |
| Oxygen Saturation | 50-100 | % |
| Temperature | 30-45 | °C |

Additional validation ensures diastolic BP < systolic BP and all values are within safe medical ranges.

## 🔍 Business Rules & Validation

The system implements comprehensive business logic validation:

### Vital Signs Business Rules
- **Change Detection**: Monitors for extreme changes between consecutive readings that may indicate data entry errors
- **Duplicate Prevention**: Prevents identical vital signs entries within short time windows (5 minutes)
- **Physiological Validation**: Warns about unusual combinations (e.g., very high heart rate with low temperature)
- **Medical Constraints**: Enforces relationships like diastolic < systolic blood pressure

### Data Integrity
- **Patient Existence**: All vital signs updates validate patient existence before processing
- **Timestamp Management**: Automatic timestamp assignment with UTC standardization
- **Error Recovery**: Graceful handling of database errors with detailed logging
- **Audit Trail**: Complete tracking of who recorded vital signs and when

## 🗄️ Database Features

The system uses SQLAlchemy with PostgreSQL for robust data persistence:

### Entity Relationships
- **Patient** → **VitalSigns** (one-to-many with cascade delete)
- **Patient** → **RiskAssessment** (one-to-many with cascade delete)  
- **VitalSigns** → **RiskAssessment** (one-to-many for assessment history)

### Data Integrity
- **Medical Constraints**: Database-level check constraints enforce vital sign ranges
- **Unique Constraints**: Prevent duplicate risk assessments per vital signs record
- **Cascade Operations**: Automatic cleanup when patients are removed
- **Indexed Queries**: Optimized for time-series and risk-based lookups

### Time-Series Optimization
- Indexed timestamps for efficient historical queries
- Chronological ordering built into relationships
- Efficient storage for high-frequency vital signs updates

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager
- PostgreSQL (recommended for production)

### Installation

1. **Clone and setup**
```bash
git clone <repository-url>
cd patient-risk-classifier
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Environment setup**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start the demo**
```bash
python run_demo.py
```

4. **Access the API**
- API Server: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 🧪 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run property-based tests only
pytest -m property_tests
```

### Code Quality
```bash
# Format code
black src tests

# Sort imports
isort src tests

# Type checking
mypy src
```

## 📋 Project Structure

```
src/
├── api/                    # FastAPI controllers
│   ├── main.py            # ✅ Application setup with middleware and error handling
│   ├── patients.py        # ✅ Patient registration and status endpoints
│   └── vitals.py          # ✅ Vital signs update and historical data endpoints
├── services/               # Business logic layer
│   ├── patient_service.py # ✅ Patient registration and management
│   ├── vital_signs_service.py # ✅ Vital signs updates and historical queries
│   └── risk_assessment_service.py # ✅ ML-powered risk assessment
├── repositories/           # Data access layer
├── models/                 # Data models (Pydantic + SQLAlchemy)
│   ├── api_models.py      # ✅ Pydantic request/response models with validation
│   └── db_models.py       # ✅ SQLAlchemy database models with relationships
└── utils/                  # Shared utilities

tests/
├── unit/                   # Unit tests
│   └── test_api_models.py # ✅ API model validation tests
├── integration/            # Integration tests
└── property/               # Property-based tests
    ├── test_error_response_security.py # ✅ Security testing for error responses
    └── test_error_handling_preserves_system_state.py # ✅ System resilience tests
```

## 🏗️ Architecture

The system follows a layered architecture with comprehensive data validation:

- **API Layer**: FastAPI controllers with Pydantic request/response validation
- **Business Logic Layer**: Services for Patient, VitalSigns, and RiskAssessment domains
- **Data Access Layer**: Repository pattern for database operations
- **ML Integration**: External risk model with structured input/output handling

### Data Models (✅ Implemented)

**API Models (Pydantic):**
- **VitalSignsBase**: Core vital signs with medical range validation
- **PatientRegistration**: Patient registration with initial vitals and metadata
- **RiskAssessment**: ML model output with risk scores and flags
- **PatientStatus**: Complete patient state for status queries
- **HistoricalDataResponse**: Time-series data with chronological ordering
- **ErrorResponse**: Structured error handling with validation details

**Database Models (SQLAlchemy):**
- **Patient**: Patient entity with arrival mode, acuity level, and timestamps
- **VitalSigns**: Time-series vital signs storage with medical validation constraints
- **RiskAssessment**: ML risk predictions linked to vital signs and patients
- **Relationships**: Proper foreign keys and cascading for data integrity

### Business Logic Services (✅ Implemented)

**PatientService:**
- Patient registration with automatic risk assessment triggering
- Unique ID validation and duplicate prevention
- Patient status retrieval and management

**VitalSignsService:**
- Comprehensive vital signs update workflow with medical validation
- Historical data queries with time range filtering and chronological ordering
- Business rule validation including duplicate detection and change monitoring
- Integration with risk assessment triggering on vital signs updates

**RiskAssessmentService:**
- ML model integration with structured input/output handling
- Risk score calculation and storage with assessment history
- Error handling for model unavailability and graceful degradation

## 🔒 Data Validation & Security

- **Medical Range Validation**: All vital signs validated against clinical standards at both API and database levels
- **Database Constraints**: SQLAlchemy check constraints enforce medical ranges in the database
- **Input Sanitization**: Comprehensive validation prevents malformed data and injection attacks
- **Secure Error Responses**: Error messages are sanitized to prevent information disclosure while remaining user-friendly
- **Authentication Security**: API key validation with rate limiting and session tracking
- **Security Testing**: Comprehensive property-based tests validate error response security and input sanitization
- **Structured Errors**: Detailed validation feedback without system exposure
- **Type Safety**: Pydantic models ensure data integrity throughout the system
- **Referential Integrity**: Foreign key relationships maintain data consistency

## 📖 API Endpoints

### Patient Management
- **POST /patients** - Register new patient with initial vital signs
- **GET /patients/{patient_id}** - Get current patient status
- **GET /patients/high-risk** - Query high-risk patients

### Vital Signs Management (✅ Implemented)
- **PUT /patients/{patient_id}/vitals** - Update patient vital signs
  - Validates vital signs against medical ranges
  - Stores measurements with automatic timestamps
  - Triggers ML risk assessment automatically
  - Returns success confirmation with vital signs ID
  
- **GET /patients/{patient_id}/history** - Get historical vital signs and risk assessments
  - Optional time range filtering (start_time, end_time)
  - Optional result limiting (max 1000 data points)
  - Returns chronologically ordered data (oldest first)
  - Includes paired vital signs and risk assessments

### Interactive Documentation
Visit http://localhost:8000/docs for interactive API documentation with live examples and request/response schemas.

## 📋 API Usage Examples

### Register a New Patient

```bash
curl -X POST "http://localhost:8000/patients" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

### Update Vital Signs

```bash
curl -X PUT "http://localhost:8000/patients/P12345/vitals" \
  -H "Content-Type: application/json" \
  -d '{
    "heart_rate": 72.0,
    "systolic_bp": 120.0,
    "diastolic_bp": 80.0,
    "respiratory_rate": 16.0,
    "oxygen_saturation": 98.0,
    "temperature": 36.5
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Vital signs updated successfully for patient P12345",
  "data": {
    "patient_id": "P12345",
    "vital_signs_id": "vs_abc123",
    "timestamp": "2024-01-15T11:00:00Z"
  }
}
```

**Note:** This endpoint automatically triggers a risk assessment using the ML model. If the model is unavailable, vital signs are still stored successfully.

### Get Current Patient Status

```bash
curl "http://localhost:8000/patients/P12345"
```

### Query High-Risk Patients

```bash
curl "http://localhost:8000/patients/high-risk"
```

### Get Patient History

```bash
# Get all historical data
curl "http://localhost:8000/patients/P12345/history"

# Get data within time range
curl "http://localhost:8000/patients/P12345/history?start_time=2024-01-15T00:00:00Z&end_time=2024-01-15T23:59:59Z"

# Limit number of results
curl "http://localhost:8000/patients/P12345/history?limit=100"
```

**Response:**
```json
{
  "patient_id": "P12345",
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": "2024-01-15T11:00:00Z",
  "data_points": [
    {
      "vitals": {
        "heart_rate": 85.0,
        "systolic_bp": 140.0,
        "diastolic_bp": 90.0,
        "respiratory_rate": 18.0,
        "oxygen_saturation": 96.0,
        "temperature": 37.2,
        "timestamp": "2024-01-15T10:30:00Z"
      },
      "risk_assessment": {
        "risk_score": 0.35,
        "risk_flag": false,
        "assessment_time": "2024-01-15T10:30:05Z",
        "model_version": "v1.0.0"
      }
    }
  ],
  "total_count": 1
}
```

## 📊 Sample API Response

```json
{
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
    "risk_flag": false,
    "assessment_time": "2024-01-15T11:00:05Z",
    "model_version": "v1.2.3"
  },
  "registration_time": "2024-01-15T10:30:00Z",
  "last_updated": "2024-01-15T11:00:00Z"
}
```

## 🤝 Contributing

This project follows specification-driven development. See `.kiro/specs/` for detailed requirements and design documentation.

## 📄 License

[Add your license here]