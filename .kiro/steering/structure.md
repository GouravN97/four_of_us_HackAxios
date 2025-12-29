# Project Structure & Organization

## Current Structure (Specification Phase)

```
workspace/
├── .kiro/                          # Kiro framework directory
│   ├── hooks/                      # Automation hooks
│   │   └── readme-update-hook.kiro.hook  # Auto-updates README on code changes
│   ├── specs/                      # Specification documents
│   │   ├── patient-risk-classifier/
│   │   │   ├── README.md           # User-facing documentation
│   │   │   ├── requirements.md     # Functional requirements (6 requirements)
│   │   │   ├── design.md           # Architecture & design (15 properties)
│   │   │   └── tasks.md            # Implementation tasks (11 task groups)
│   │   └── hospital-management-system/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       └── tasks.md
│   └── steering/                   # Workflow guides (this directory)
```

## Planned Implementation Structure

```
patient-risk-classifier/
├── src/
│   ├── api/                        # FastAPI controllers
│   │   ├── __init__.py
│   │   ├── patients.py             # Patient endpoints
│   │   ├── vitals.py               # Vital signs endpoints
│   │   └── health.py               # Health check endpoints
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── patient_service.py      # Patient management logic
│   │   ├── vitals_service.py       # Vital signs processing
│   │   └── risk_service.py         # Risk assessment logic
│   ├── repositories/               # Data access layer
│   │   ├── __init__.py
│   │   ├── patient_repository.py   # Patient data operations
│   │   ├── vitals_repository.py    # Vital signs data operations
│   │   └── risk_repository.py      # Risk assessment data operations
│   ├── models/                     # Data models
│   │   ├── __init__.py
│   │   ├── api_models.py           # Pydantic request/response models
│   │   └── db_models.py            # SQLAlchemy database models
│   └── utils/                      # Shared utilities
│       ├── __init__.py
│       ├── validation.py           # Medical validation logic
│       └── ml_client.py            # ML model integration
├── tests/                          # Test suites
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── property/                   # Property-based tests
├── requirements.txt                # Python dependencies
├── run_demo.py                     # Demo startup script
└── README.md                       # Project documentation
```

## Organizational Conventions

### Kiro Framework Patterns
- **Specification-first development**: Requirements → Design → Tasks workflow
- **Property-based testing**: Correctness validation through universal properties
- **Automated documentation**: Hooks maintain README accuracy
- **Multi-project support**: Separate specs for related systems

### Code Organization Principles
- **Layered architecture**: Clear separation between API, business logic, and data access
- **Service-oriented design**: Separate services for each domain entity
- **Repository pattern**: Abstract data access behind interfaces
- **Dependency injection**: Loose coupling between layers

### File Naming Conventions
- **Snake_case**: For Python files and directories
- **Descriptive names**: Clear indication of purpose (e.g., `patient_service.py`)
- **Layer suffixes**: `_controller.py`, `_service.py`, `_repository.py`
- **Test organization**: Mirror source structure in test directories

### Import Structure
- **Absolute imports**: Use full package paths
- **Layer boundaries**: API layer imports services, services import repositories
- **No circular dependencies**: Enforce unidirectional dependency flow
- **External dependencies**: Isolate in utility modules for easy mocking