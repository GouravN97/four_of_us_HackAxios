# Implementation Plan: Patient Risk Classifier Backend

## Overview

This implementation plan creates a Python-based RESTful API system for patient risk classification. The system will use FastAPI for the web framework, SQLAlchemy for database operations, and Pydantic for data validation. The implementation follows a layered architecture with clear separation between API, business logic, and data access layers.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create Python project structure with proper package organization
  - Set up virtual environment and install dependencies (FastAPI, SQLAlchemy, Pydantic, pytest, hypothesis)
  - Configure development tools (linting, formatting, testing)
  - _Requirements: All requirements (foundational setup)_

- [-] 2. Implement core data models and validation
  - [x] 2.1 Create Pydantic models for API requests and responses
    - Define PatientRegistration, VitalSignsUpdate, and response models
    - Implement medical range validation for vital signs
    - _Requirements: 1.1, 1.2, 2.1, 6.1_

  - [x] 2.2 Write property test for data validation

    - **Property 4: Invalid Data Rejection**
    - **Validates: Requirements 1.5, 2.1, 6.1**

  - [x] 2.3 Create SQLAlchemy database models
    - Define Patient, VitalSigns, and RiskAssessment entities
    - Set up proper relationships and constraints
    - _Requirements: 1.1, 1.2, 3.2, 3.3_

  - [x] 2.4 Write property test for patient registration round trip

    - **Property 1: Patient Registration Round Trip**
    - **Validates: Requirements 1.1, 1.2**

- [x] 3. Implement database layer and repositories
  - [x] 3.1 Create database connection and session management
    - Set up SQLAlchemy engine and session factory
    - Implement database initialization and migration support
    - _Requirements: 4.4_

  - [x] 3.2 Implement PatientRepository
    - Create CRUD operations for patient records
    - Implement unique ID generation and validation
    - _Requirements: 1.1, 1.4, 4.1_

  - [x] 3.3 Write property test for patient ID uniqueness

    - **Property 2: Patient ID Uniqueness**
    - **Validates: Requirements 1.4**

  - [x] 3.4 Implement VitalSignsRepository
    - Create time-series storage for vital signs
    - Implement historical data queries with time range filtering
    - _Requirements: 2.2, 2.4, 4.2_

  - [x] 3.5 Write property test for vital signs storage

    - **Property 5: Vital Signs Storage with Timestamps**
    - **Validates: Requirements 2.2, 2.4**

  - [x] 3.6 Implement RiskAssessmentRepository
    - Create storage for risk assessments with proper linkage
    - Implement risk-based patient queries
    - _Requirements: 3.2, 3.3, 4.3_

- [x] 4. Checkpoint - Database layer validation
  - Ensure all repository tests pass, ask the user if questions arise.

- [-] 5. Implement business logic services
  - [x] 5.1 Create PatientService
    - Implement patient registration logic
    - Add business rule validation and error handling
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [ ] 5.2 Write property test for registration triggers risk assessment

    - **Property 3: Registration Triggers Risk Assessment**
    - **Validates: Requirements 1.3**

  - [ ] 5.3 Create VitalSignsService
    - Implement vital signs update logic with validation
    - Add error handling for invalid updates
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

  - [ ]* 5.4 Write property test for data integrity under invalid updates
    - **Property 7: Data Integrity Under Invalid Updates**
    - **Validates: Requirements 2.5**

  - [ ] 5.5 Create RiskAssessmentService with ML model integration
    - Implement risk model interface and error handling
    - Add model input validation and response parsing
    - _Requirements: 3.1, 3.2, 3.4, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 5.6 Write property test for risk model input format compliance

    - **Property 8: Risk Model Input Format Compliance**
    - **Validates: Requirements 5.1, 5.4**

  - [ ]* 5.7 Write property test for vital signs update triggers risk assessment
    - **Property 6: Vital Signs Update Triggers Risk Assessment**
    - **Validates: Requirements 2.3**

- [ ] 6. Implement REST API controllers
  - [ ] 6.1 Create FastAPI application setup
    - Configure FastAPI app with middleware and error handlers
    - Set up request/response logging and validation
    - _Requirements: 6.4, 6.5_

  - [ ] 6.2 Implement PatientController endpoints
    - POST /patients - Patient registration
    - GET /patients/{id} - Current patient status
    - GET /patients/high-risk - Risk-based queries
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.3_

  - [ ]* 6.3 Write property test for current patient status retrieval
    - **Property 10: Current Patient Status Retrieval**
    - **Validates: Requirements 4.1**

  - [ ] 6.4 Implement VitalSignsController endpoints
    - PUT /patients/{id}/vitals - Update vital signs
    - GET /patients/{id}/history - Historical data
    - _Requirements: 2.1, 2.2, 2.3, 4.2_

  - [ ]* 6.5 Write property test for historical data chronological ordering
    - **Property 11: Historical Data Chronological Ordering**
    - **Validates: Requirements 4.2**

  - [ ] 6.6 Implement comprehensive error handling
    - Add input sanitization and security measures
    - Implement proper error responses without information leakage
    - _Requirements: 6.2, 6.4, 6.5_

  - [ ]* 6.7 Write property test for input sanitization security
    - **Property 14: Input Sanitization Security**
    - **Validates: Requirements 6.4**

- [ ] 7. Checkpoint - API layer validation
  - Ensure all API tests pass, ask the user if questions arise.

- [ ] 8. Implement comprehensive error handling and resilience
  - [ ] 8.1 Add system-wide error handling
    - Implement error logging and monitoring
    - Add graceful degradation for external service failures
    - _Requirements: 3.4, 4.5, 5.3, 5.5, 6.3_

  - [ ]* 8.2 Write property test for error handling preserves system state
    - **Property 13: Error Handling Preserves System State**
    - **Validates: Requirements 3.4, 4.5, 5.3, 5.5**

  - [ ] 8.3 Add security and validation enhancements
    - Implement comprehensive input sanitization
    - Add rate limiting and authentication middleware
    - _Requirements: 6.4, 6.5_

  - [ ]* 8.4 Write property test for error response security
    - **Property 15: Error Response Security**
    - **Validates: Requirements 6.2, 6.5**

- [ ] 9. Integration and testing
  - [ ] 9.1 Create mock risk model for testing
    - Implement mock ML model that returns predictable results
    - Add configurable failure modes for testing error handling
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 9.2 Write property test for risk assessment storage completeness
    - **Property 9: Risk Assessment Storage Completeness**
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 9.3 Write property test for risk-based patient filtering
    - **Property 12: Risk-Based Patient Filtering**
    - **Validates: Requirements 4.3**

  - [ ] 9.4 Create integration test suite
    - Test end-to-end workflows with real database
    - Validate API contracts and error scenarios
    - _Requirements: All requirements (integration validation)_

- [ ] 10. Demo and sharing preparation
  - [ ] 10.1 Create demo setup script
    - Write setup.py or requirements.txt for easy installation
    - Create sample data loading script with realistic patient scenarios
    - Add simple startup script (run_demo.py) that initializes database and starts server
    - _Requirements: All requirements (demo setup)_

  - [ ] 10.2 Create interactive API documentation
    - Generate OpenAPI/Swagger UI accessible at /docs endpoint
    - Add example requests and responses for all endpoints
    - Include sample patient data for testing
    - _Requirements: All requirements (documentation)_

  - [ ] 10.3 Add demo endpoints and utilities
    - Create /demo/reset endpoint to clear and reload sample data
    - Add /health endpoint for system status checking
    - Implement simple web interface or Postman collection for easy testing
    - _Requirements: All requirements (demo utilities)_

- [ ] 11. Final validation and packaging
  - [ ] 11.1 Run complete test suite and validate coverage
    - Ensure all property tests pass with 100+ iterations
    - Validate minimum 90% code coverage
    - _Requirements: All requirements_

  - [ ] 11.2 Create README with quick start guide
    - Document installation steps (pip install -r requirements.txt)
    - Provide API usage examples with curl commands
    - Include sample patient registration and vital signs update flows
    - _Requirements: All requirements (documentation)_

  - [ ] 11.3 Final system validation
    - Test complete demo flow from fresh installation
    - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and integration points
- Mock ML model allows testing without external dependencies
- Checkpoints ensure incremental validation and early error detection