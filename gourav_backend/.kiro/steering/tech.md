# Technology Stack & Build System

## Core Technologies

### Backend Framework
- **Python 3.8+**: Primary language
- **FastAPI**: RESTful API framework with automatic OpenAPI documentation
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: ORM for database operations

### Database & Storage
- **PostgreSQL**: Primary relational database
- **Time-series database**: Optimized storage for vital signs history
- **Redis**: Caching layer (planned)

### Machine Learning
- **Pre-trained ML models**: Risk assessment algorithms
- **Ensemble models**: Gradient boosting, logistic regression, LSTM
- **scikit-learn/tensorflow**: ML framework support

### Testing & Quality
- **pytest**: Unit testing framework
- **Hypothesis**: Property-based testing (100+ iterations minimum)
- **Coverage target**: 90% minimum for core business logic

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Workflow
```bash
# Start development server
python run_demo.py

# Run all tests
pytest

# Run property-based tests specifically
pytest -m property_tests

# Generate coverage report
pytest --cov=src --cov-report=html

# Reset demo data
curl -X POST http://localhost:8000/demo/reset
```

### API Access Points
- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

## Architecture Patterns

### Layered Architecture
- **API Layer**: FastAPI controllers and request/response handling
- **Business Logic Layer**: Services for Patient, VitalSigns, RiskAssessment
- **Data Access Layer**: Repository pattern for database operations

### Key Conventions
- RESTful API design with standard HTTP methods
- JSON request/response format
- Structured error responses with descriptive messages
- Multi-layer validation (API, business logic, database)
- Time-series optimization for vital signs storage
- Loose coupling with external ML models