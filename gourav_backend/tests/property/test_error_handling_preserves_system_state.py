"""
Property-based tests for error handling preserves system state.

Tests Property 13: Error Handling Preserves System State
**Validates: Requirements 3.4, 4.5, 5.3, 5.5**

For any system error (model failures, invalid patient IDs), the system should 
maintain previous valid state and continue normal operations for other requests.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid

from src.services.patient_service import PatientService, PatientNotFoundError, ValidationError
from src.services.risk_assessment_service import RiskAssessmentService
from src.services.vital_signs_service import VitalSignsService
from src.utils.ml_client import MLModelError, MLModelTimeoutError, MLModelResponseError
from src.models.api_models import PatientRegistration, VitalSignsUpdate, VitalSignsWithTimestamp, ArrivalMode
from src.models.db_models import Patient, VitalSigns, RiskAssessment
from src.utils.database import get_test_db, create_test_database


class TestErrorHandlingPreservesSystemState:
    """
    Test that error handling preserves system state and allows continued operation.
    
    **Feature: patient-risk-classifier, Property 13: Error Handling Preserves System State**
    **Validates: Requirements 3.4, 4.5, 5.3, 5.5**
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        create_test_database()
        # Clear any existing data
        db_session = next(get_test_db())
        try:
            from src.models.db_models import Patient, VitalSigns, RiskAssessment
            db_session.query(RiskAssessment).delete()
            db_session.query(VitalSigns).delete()
            db_session.query(Patient).delete()
            db_session.commit()
        finally:
            db_session.close()
    
    @given(
        arrival_mode=st.sampled_from([ArrivalMode.AMBULANCE, ArrivalMode.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=60, max_value=100, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=100, max_value=140, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=60, max_value=90, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=12, max_value=20, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=95, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=36.0, max_value=37.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.property_tests
    def test_patient_service_error_handling_preserves_state(
        self, arrival_mode, acuity_level, heart_rate, systolic_bp, diastolic_bp,
        respiratory_rate, oxygen_saturation, temperature
    ):
        """
        Test that PatientService errors don't affect valid operations.
        
        Property: For any valid patient registration followed by an invalid operation,
        the system should preserve the valid patient data and allow subsequent 
        valid operations to succeed.
        
        **Validates: Requirements 4.5** - Database queries fail gracefully
        """
        # Ensure diastolic < systolic
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0
        
        patient_id = f"TEST_P_{uuid.uuid4().hex[:8]}"
        invalid_patient_id = f"INVALID_{uuid.uuid4().hex[:8]}"
        
        timestamp = datetime.utcnow()
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=heart_rate,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=oxygen_saturation,
            temperature=temperature,
            timestamp=timestamp
        )
        
        registration_data = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals
        )
        
        db_session = next(get_test_db())
        try:
            patient_service = PatientService(db_session)
            risk_service = RiskAssessmentService(db_session)
            
            # Step 1: Register a valid patient (should succeed)
            registered_patient = patient_service.register_patient(registration_data)
            assert registered_patient is not None
            assert registered_patient.patient_id == patient_id
            
            # Trigger initial risk assessment (required for get_patient_status)
            from src.repositories.vital_signs_repository import VitalSignsRepository
            vital_signs_repo = VitalSignsRepository(db_session)
            initial_vitals_record = vital_signs_repo.get_latest_for_patient(patient_id)
            risk_service.assess_risk_for_vital_signs(initial_vitals_record)
            
            # Verify patient exists and can be retrieved
            patient_status = patient_service.get_patient_status(patient_id)
            assert patient_status.patient_id == patient_id
            
            # Step 2: Attempt invalid operation (should fail gracefully)
            try:
                patient_service.get_patient_status(invalid_patient_id)
                # If this doesn't raise, the ID was somehow valid
            except (PatientNotFoundError, ValidationError, ValueError):
                # Expected errors - system should handle gracefully
                pass
            
            # Step 3: Verify original patient still exists and is accessible
            patient_status_after_error = patient_service.get_patient_status(patient_id)
            assert patient_status_after_error.patient_id == patient_id
            assert patient_status_after_error.arrival_mode == arrival_mode
            assert patient_status_after_error.acuity_level == acuity_level
            
            # Step 4: Verify new valid operations still work
            exists = patient_service.patient_exists(patient_id)
            assert exists is True
            
            updated = patient_service.update_patient_last_updated(patient_id)
            assert updated is True
            
        finally:
            db_session.close()

    
    @given(
        arrival_mode=st.sampled_from([ArrivalMode.AMBULANCE, ArrivalMode.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=60, max_value=100, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=100, max_value=140, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=60, max_value=90, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=12, max_value=20, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=95, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=36.0, max_value=37.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.property_tests
    def test_ml_model_error_preserves_vital_signs_and_uses_fallback(
        self, arrival_mode, acuity_level, heart_rate, systolic_bp, diastolic_bp,
        respiratory_rate, oxygen_saturation, temperature
    ):
        """
        Test that ML model errors don't prevent vital signs storage and system operation.
        
        Property: For any ML model failure during risk assessment, the system should
        preserve vital signs data, use fallback assessment, and continue normal operations.
        
        **Validates: Requirements 3.4, 5.3, 5.5**
        - 3.4: Log error and maintain previous risk status on failure
        - 5.3: Handle Risk_Model errors gracefully
        - 5.5: Log issue and continue storing vital signs when model unavailable
        """
        # Ensure diastolic < systolic
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0
        
        patient_id = f"TEST_ML_{uuid.uuid4().hex[:8]}"
        
        timestamp = datetime.utcnow()
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=heart_rate,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=oxygen_saturation,
            temperature=temperature,
            timestamp=timestamp
        )
        
        registration_data = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals
        )
        
        db_session = next(get_test_db())
        try:
            patient_service = PatientService(db_session)
            vital_signs_service = VitalSignsService(db_session)
            risk_service = RiskAssessmentService(db_session)
            
            # Step 1: Register patient and get initial state
            registered_patient = patient_service.register_patient(registration_data)
            
            # Trigger initial risk assessment
            from src.repositories.vital_signs_repository import VitalSignsRepository
            vital_signs_repo = VitalSignsRepository(db_session)
            initial_vitals_record = vital_signs_repo.get_latest_for_patient(patient_id)
            risk_service.assess_risk_for_vital_signs(initial_vitals_record)
            
            initial_patient_status = patient_service.get_patient_status(patient_id)
            
            # Step 2: Mock ML model to simulate failure
            with patch.object(risk_service.ml_client, 'predict_risk') as mock_predict:
                mock_predict.side_effect = MLModelTimeoutError("Model request timed out")
                
                # Step 3: Update vital signs (should succeed despite ML error)
                new_vitals = VitalSignsUpdate(
                    heart_rate=heart_rate + 5,  # Slightly different values
                    systolic_bp=systolic_bp,
                    diastolic_bp=diastolic_bp,
                    respiratory_rate=respiratory_rate,
                    oxygen_saturation=oxygen_saturation,
                    temperature=temperature
                )
                
                updated_vitals = vital_signs_service.update_vital_signs(patient_id, new_vitals)
                assert updated_vitals is not None
                assert updated_vitals.patient_id == patient_id
                
                # Trigger risk assessment (should use fallback)
                risk_assessment = risk_service.assess_risk_for_vital_signs(updated_vitals)
                
                # Step 4: Verify risk assessment was created with fallback
                assert risk_assessment is not None
                assert 0.0 <= risk_assessment.risk_score <= 1.0
                assert isinstance(risk_assessment.risk_flag, bool)
                # Should have error message indicating fallback was used
                assert risk_assessment.error_message is not None
                
                # Step 5: Verify patient data integrity is maintained
                current_status = patient_service.get_patient_status(patient_id)
                assert current_status.patient_id == patient_id
                assert current_status.arrival_mode == arrival_mode
                assert current_status.acuity_level == acuity_level
                
                # Step 6: Verify system continues to accept new operations
                history = vital_signs_service.get_vital_signs_history(patient_id)
                assert len(history) >= 2  # Initial + updated
                
                risk_history = risk_service.get_risk_assessment_history(patient_id)
                assert len(risk_history) >= 2  # Initial + updated
                
        finally:
            db_session.close()
    
    @given(
        num_patients=st.integers(min_value=2, max_value=4),
        arrival_mode=st.sampled_from([ArrivalMode.AMBULANCE, ArrivalMode.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=60, max_value=100, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=100, max_value=140, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=60, max_value=90, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=12, max_value=20, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=95, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=36.0, max_value=37.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.property_tests
    def test_database_error_isolation_preserves_other_operations(
        self, num_patients, arrival_mode, acuity_level, heart_rate, systolic_bp, 
        diastolic_bp, respiratory_rate, oxygen_saturation, temperature
    ):
        """
        Test that database errors for one operation don't affect other valid operations.
        
        Property: For any database error affecting one patient operation, other
        patient operations should continue to work normally.
        
        **Validates: Requirements 4.5** - Database queries fail gracefully
        """
        # Ensure diastolic < systolic
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0
        
        # Generate unique patient IDs
        patient_ids = [f"TEST_DB_{uuid.uuid4().hex[:8]}" for _ in range(num_patients)]
        invalid_patient_id = f"INVALID_{uuid.uuid4().hex[:8]}"
        
        db_session = next(get_test_db())
        try:
            patient_service = PatientService(db_session)
            risk_service = RiskAssessmentService(db_session)
            
            from src.repositories.vital_signs_repository import VitalSignsRepository
            vital_signs_repo = VitalSignsRepository(db_session)
            
            # Step 1: Register multiple valid patients
            registered_patients = []
            for patient_id in patient_ids:
                timestamp = datetime.utcnow()
                initial_vitals = VitalSignsWithTimestamp(
                    heart_rate=heart_rate,
                    systolic_bp=systolic_bp,
                    diastolic_bp=diastolic_bp,
                    respiratory_rate=respiratory_rate,
                    oxygen_saturation=oxygen_saturation,
                    temperature=temperature,
                    timestamp=timestamp
                )
                
                registration_data = PatientRegistration(
                    patient_id=patient_id,
                    arrival_mode=arrival_mode,
                    acuity_level=acuity_level,
                    initial_vitals=initial_vitals
                )
                
                registered = patient_service.register_patient(registration_data)
                registered_patients.append(registered)
                
                # Trigger risk assessment for each patient
                vitals_record = vital_signs_repo.get_latest_for_patient(patient_id)
                risk_service.assess_risk_for_vital_signs(vitals_record)
            
            # Step 2: Verify all patients are accessible
            for patient_id in patient_ids:
                status = patient_service.get_patient_status(patient_id)
                assert status.patient_id == patient_id
            
            # Step 3: Attempt operation with invalid patient ID (should fail)
            try:
                patient_service.get_patient_status(invalid_patient_id)
            except (PatientNotFoundError, ValidationError, ValueError):
                # Expected error - should be handled gracefully
                pass
            
            # Step 4: Verify all valid patients are still accessible after error
            for patient_id in patient_ids:
                status = patient_service.get_patient_status(patient_id)
                assert status.patient_id == patient_id
                assert status.arrival_mode == arrival_mode
                assert status.acuity_level == acuity_level
            
            # Step 5: Verify new operations on valid patients still work
            for patient_id in patient_ids[:2]:  # Test subset
                updated = patient_service.update_patient_last_updated(patient_id)
                assert updated is True
                
                exists = patient_service.patient_exists(patient_id)
                assert exists is True
                
        finally:
            db_session.close()

    
    @given(
        arrival_mode=st.sampled_from([ArrivalMode.AMBULANCE, ArrivalMode.WALK_IN]),
        acuity_level=st.integers(min_value=1, max_value=5),
        heart_rate=st.floats(min_value=60, max_value=100, allow_nan=False, allow_infinity=False),
        systolic_bp=st.floats(min_value=100, max_value=140, allow_nan=False, allow_infinity=False),
        diastolic_bp=st.floats(min_value=60, max_value=90, allow_nan=False, allow_infinity=False),
        respiratory_rate=st.floats(min_value=12, max_value=20, allow_nan=False, allow_infinity=False),
        oxygen_saturation=st.floats(min_value=95, max_value=100, allow_nan=False, allow_infinity=False),
        temperature=st.floats(min_value=36.0, max_value=37.5, allow_nan=False, allow_infinity=False),
        error_type=st.sampled_from([
            MLModelTimeoutError("Model request timed out"),
            MLModelResponseError("Invalid model response"),
            MLModelError("Model service unavailable"),
        ])
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.property_tests
    def test_multiple_ml_error_types_preserve_system_integrity(
        self, arrival_mode, acuity_level, heart_rate, systolic_bp, diastolic_bp,
        respiratory_rate, oxygen_saturation, temperature, error_type
    ):
        """
        Test that various ML model error types don't compromise system integrity.
        
        Property: For any type of ML model error (timeout, response error, general error),
        the system should maintain data integrity and continue operations.
        
        **Validates: Requirements 3.4, 5.3, 5.5**
        """
        # Ensure diastolic < systolic
        if diastolic_bp >= systolic_bp:
            diastolic_bp = systolic_bp - 1.0
            if diastolic_bp < 20:
                systolic_bp = 21.0
                diastolic_bp = 20.0
        
        patient_id = f"TEST_ERR_{uuid.uuid4().hex[:8]}"
        
        timestamp = datetime.utcnow()
        initial_vitals = VitalSignsWithTimestamp(
            heart_rate=heart_rate,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=oxygen_saturation,
            temperature=temperature,
            timestamp=timestamp
        )
        
        registration_data = PatientRegistration(
            patient_id=patient_id,
            arrival_mode=arrival_mode,
            acuity_level=acuity_level,
            initial_vitals=initial_vitals
        )
        
        db_session = next(get_test_db())
        try:
            patient_service = PatientService(db_session)
            vital_signs_service = VitalSignsService(db_session)
            risk_service = RiskAssessmentService(db_session)
            
            # Step 1: Establish baseline state
            registered_patient = patient_service.register_patient(registration_data)
            
            # Trigger initial risk assessment
            from src.repositories.vital_signs_repository import VitalSignsRepository
            vital_signs_repo = VitalSignsRepository(db_session)
            initial_vitals_record = vital_signs_repo.get_latest_for_patient(patient_id)
            risk_service.assess_risk_for_vital_signs(initial_vitals_record)
            
            initial_status = patient_service.get_patient_status(patient_id)
            
            # Step 2: Simulate ML model failure with specific error type
            with patch.object(risk_service.ml_client, 'predict_risk') as mock_predict:
                mock_predict.side_effect = error_type
                
                # Step 3: Update vital signs (should succeed)
                new_vitals = VitalSignsUpdate(
                    heart_rate=heart_rate + 2,
                    systolic_bp=systolic_bp,
                    diastolic_bp=diastolic_bp,
                    respiratory_rate=respiratory_rate,
                    oxygen_saturation=oxygen_saturation,
                    temperature=temperature
                )
                
                updated_vitals = vital_signs_service.update_vital_signs(patient_id, new_vitals)
                assert updated_vitals is not None
                
                # Trigger risk assessment (should use fallback)
                risk_assessment = risk_service.assess_risk_for_vital_signs(updated_vitals)
                
                # Step 4: Verify fallback assessment was created
                assert risk_assessment is not None
                assert 0.0 <= risk_assessment.risk_score <= 1.0
                assert isinstance(risk_assessment.risk_flag, bool)
                assert risk_assessment.error_message is not None
            
            # Step 5: Verify system integrity after error
            final_status = patient_service.get_patient_status(patient_id)
            assert final_status.patient_id == patient_id
            assert final_status.arrival_mode == arrival_mode
            assert final_status.acuity_level == acuity_level
            
            # Should have vital signs history
            history = vital_signs_service.get_vital_signs_history(patient_id)
            assert len(history) >= 2
            
            # Should have risk assessments (with fallbacks if needed)
            risk_history = risk_service.get_risk_assessment_history(patient_id)
            assert len(risk_history) >= 2
            
            # Step 6: Verify system can still perform new valid operations
            exists = patient_service.patient_exists(patient_id)
            assert exists is True
            
            latest_risk = risk_service.get_latest_risk_assessment(patient_id)
            assert latest_risk is not None
            
        finally:
            db_session.close()


if __name__ == "__main__":
    # Run the property tests
    pytest.main([__file__, "-v", "--tb=short"])
