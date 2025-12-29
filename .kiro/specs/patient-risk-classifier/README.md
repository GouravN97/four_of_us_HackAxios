# Patient Risk Classifier Backend

A real-time patient deterioration risk assessment system for hospital environments. This backend API continuously monitors patient vital signs and uses machine learning to predict short-term deterioration risk, enabling healthcare providers to prioritize critical cases.

## 🏥 Features

- **Real-time Risk Assessment**: Continuous monitoring with ML-powered risk scoring
- **Vital Signs Management**: Store and track patient vital signs over time
- **Medical Validation**: Input validation using healthcare standards
- **Historical Analytics**: Query patient data and risk trends
- **RESTful API**: Clean, documented endpoints for easy integration
- **Property-Based Testing**: Comprehensive correctness validation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone and setup**
```bash
git clone <repository-url>
cd patient-risk-classifier
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Start the demo**
```bash
python run_demo.py
```

3. **Access the API**
- API Server: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📋 API Usage

### Register a New Patient

```bash
curl -X POST "http://localhost:8000/patients" \
  -H "Content-Type: application/json" \
  -d '{
    "patientId": "P001",
    "arrivalMode": "Ambulance",
    "acuityLevel": 3,
    "initialVitals": {
      "heartRate": 85,
      "systolicBP": 120,
      "diastolicBP": 80,
      "respiratoryRate": 16,
      "oxygenSaturation": 98.5,
      "temperature": 37.0
    }
  }'
```

### Update Vital Signs

```bash
curl -X PUT "http://localhost:8000/patients/P001/vitals" \
  -H "Content-Type: application/json" \
  -d '{
    "heartRate": 92,
    "systolicBP": 130,
    "diastolicBP": 85,
    "respiratoryRate": 18,
    "oxygenSaturation": 97.8,
    "temperature": 37.2
  }'
```

### Get Current Patient Status

```bash
curl "http://localhost:8000/patients/P001"
```

### Query High-Risk Patients

```bash
curl "http://localhost:8000/patients/high-risk"
```

### Get Patient History

```bash
curl "http://localhost:8000/patients/P001/history?hours=24"
```

## 📊 Sample Response

```json
{
  "patientId": "P001",
  "arrivalMode": "Ambulance",
  "acuityLevel": 3,
  "currentVitals": {
    "heartRate": 92,
    "systolicBP": 130,
    "diastolicBP": 85,
    "respiratoryRate": 18,
    "oxygenSaturation": 97.8,
    "temperature": 37.2,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "currentRisk": {
    "riskScore": 0.23,
    "riskFlag": false,
    "assessmentTime": "2024-01-15T10:30:05Z"
  },
  "lastUpdated": "2024-01-15T10:30:00Z"
}
```

## 🔧 Demo Features

### Reset Demo Data
```bash
curl -X POST "http://localhost:8000/demo/reset"
```

### Sample Patients
The demo includes pre-loaded patients:
- **P001**: Normal vital signs, low risk
- **P002**: Elevated heart rate, moderate risk  
- **P003**: Critical vital signs, high risk
- **P004**: Elderly patient with comorbidities

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  Business Logic  │    │   Database      │
│   Controllers   │───▶│   Services       │───▶│   Repositories  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   ML Risk Model  │
                       │   (External)     │
                       └──────────────────┘
```

### Key Components
- **API Layer**: FastAPI controllers with request/response validation
- **Business Logic**: Patient, VitalSigns, and RiskAssessment services
- **Data Layer**: SQLAlchemy repositories with time-series optimization
- **ML Integration**: External risk model with error handling

## 📈 Vital Signs Validation

The system validates vital signs against medical standards:

| Vital Sign | Valid Range | Unit |
|------------|-------------|------|
| Heart Rate | 30-200 | bpm |
| Systolic BP | 50-300 | mmHg |
| Diastolic BP | 20-200 | mmHg |
| Respiratory Rate | 5-60 | breaths/min |
| Oxygen Saturation | 50-100 | % |
| Temperature | 30-45 | °C |

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### Run Property-Based Tests
```bash
pytest -m property_tests
```

### Check Coverage
```bash
pytest --cov=src --cov-report=html
```

## 🔒 Security Features

- Input sanitization to prevent injection attacks
- Medical range validation for all vital signs
- Error responses that don't expose system internals
- Rate limiting and request validation

## 🚨 Error Handling

The API returns structured error responses:

```json
{
  "error": "Validation Error",
  "message": "Heart rate must be between 30 and 200 bpm",
  "code": "INVALID_VITAL_SIGNS",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📝 Development

### Project Structure
```
patient-risk-classifier/
├── src/
│   ├── api/           # FastAPI controllers
│   ├── services/      # Business logic
│   ├── repositories/  # Data access
│   ├── models/        # Data models
│   └── utils/         # Utilities
├── tests/             # Test suites
├── requirements.txt   # Dependencies
└── run_demo.py       # Demo startup script
```

### Adding New Features
1. Update requirements in `requirements.md`
2. Modify design in `design.md`
3. Add implementation tasks to `tasks.md`
4. Follow the layered architecture pattern

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
- Check the interactive documentation at `/docs`
- Review the test cases for usage examples
- Open an issue on GitHub

---

**Built for healthcare innovation** 🏥 **Powered by machine learning** 🤖