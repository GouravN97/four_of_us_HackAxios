"""
Property-based tests for historical data chronological ordering.
Tests that historical data queries return vital signs and risk assessments
in correct chronological order within specified time ranges.

Property 11: Historical Data Chronological Ordering
Validates: Requirements 4.2
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.db_models import ArrivalModeEnum
from src.repositories.patient_repository import PatientRepository
from src.repositories.risk_assessment_repository import RiskAssessmentRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.services.vital_signs_service import VitalSignsService
from src.utils.database import create_test_database, get_test_db


def generate_unique_patient_id() -> str:
    """Generate a unique patient ID to avoid collisions."""
    return f"P_{uuid4().hex[:12]}"


class TestHistoricalDataChronologicalOrdering:
    """Property 11: Historical Data Chronological Ordering - Validates Requirements 4.2"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        create_test_database()

    @given(
        num_records=st.integers(min_value=3, max_value=15),
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property_tests
    def test_historical_data_returns_chronological_order(self, num_records):
        """
        Property 11: Historical Data Chronological Ordering
        Validates: Requirements 4.2

        For any historical data query, the system should return vital signs
        and risk assessments in correct chronological order within the
        specified time range.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vitals_service = VitalSignsService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=ArrivalModeEnum.AMBULANCE,
                acuity_level=3
            )

            # Create vital signs records with timestamps spread over time
            base_time = datetime.utcnow() - timedelta(hours=num_records)
            created_timestamps = []
            
            for i in range(num_records):
                timestamp = base_time + timedelta(hours=i)
                created_timestamps.append(timestamp)
                
                # Create vital signs with varying values
                vitals = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=70.0 + i * 2,
                    systolic_bp=120.0 + i,
                    diastolic_bp=80.0 + i * 0.5,
                    respiratory_rate=16.0 + i * 0.5,
                    oxygen_saturation=98.0 - i * 0.2,
                    temperature=36.5 + i * 0.1,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )

                # Create corresponding risk assessment
                risk_repo.create(
                    patient_id=patient.patient_id,
                    vital_signs_id=vitals.id,
                    risk_score=0.2 + i * 0.05,
                    risk_flag=(i * 0.05) >= 0.4,
                    assessment_time=timestamp + timedelta(seconds=5),
                    model_version="test_v1"
                )

            # Get historical data without time range (should return all in chronological order)
            history = vitals_service.get_vital_signs_history(patient.patient_id)

            # Verify correct number of records
            assert len(history) == num_records, \
                f"Expected {num_records} records, got {len(history)}"

            # Verify chronological ordering (oldest first)
            for i in range(len(history) - 1):
                assert history[i].timestamp <= history[i + 1].timestamp, \
                    f"Historical data should be in chronological order (oldest first): " \
                    f"record {i} timestamp {history[i].timestamp} should be <= " \
                    f"record {i+1} timestamp {history[i + 1].timestamp}"

            # Verify timestamps match what we created (in order)
            retrieved_timestamps = [vs.timestamp for vs in history]
            expected_timestamps = sorted(created_timestamps)
            assert retrieved_timestamps == expected_timestamps, \
                f"Retrieved timestamps should match created timestamps in chronological order"

        finally:
            db_session.close()

    @given(
        num_records=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.property_tests
    def test_time_range_query_returns_chronological_order(self, num_records):
        """
        Property 11: Historical Data Chronological Ordering
        Validates: Requirements 4.2

        For any historical data query with a time range, the system should
        return only data within that range in correct chronological order.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vitals_service = VitalSignsService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=ArrivalModeEnum.WALK_IN,
                acuity_level=2
            )

            # Create vital signs records spread over time
            base_time = datetime.utcnow() - timedelta(hours=num_records * 2)
            all_timestamps = []
            
            for i in range(num_records):
                timestamp = base_time + timedelta(hours=i * 2)
                all_timestamps.append(timestamp)
                
                vitals = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=75.0 + i,
                    systolic_bp=115.0 + i,
                    diastolic_bp=75.0 + i * 0.5,
                    respiratory_rate=15.0 + i * 0.3,
                    oxygen_saturation=97.0 - i * 0.1,
                    temperature=36.8 + i * 0.05,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )

                risk_repo.create(
                    patient_id=patient.patient_id,
                    vital_signs_id=vitals.id,
                    risk_score=0.15 + i * 0.03,
                    risk_flag=(i * 0.03) >= 0.3,
                    assessment_time=timestamp + timedelta(seconds=5),
                    model_version="test_v1"
                )

            # Query a subset of the time range (middle portion)
            if num_records >= 5:
                # Get middle 60% of records
                start_index = int(num_records * 0.2)
                end_index = int(num_records * 0.8)
                start_time = all_timestamps[start_index]
                end_time = all_timestamps[end_index]

                # Get historical data within time range
                history = vitals_service.get_vital_signs_history(
                    patient.patient_id,
                    start_time=start_time,
                    end_time=end_time
                )

                # Calculate expected records in range
                expected_timestamps = [ts for ts in all_timestamps if start_time <= ts <= end_time]
                expected_count = len(expected_timestamps)

                # Verify correct number of records
                assert len(history) == expected_count, \
                    f"Expected {expected_count} records in time range, got {len(history)}"

                # Verify all records are within time range
                for vs in history:
                    assert start_time <= vs.timestamp <= end_time, \
                        f"All records should be within time range: " \
                        f"{start_time} <= {vs.timestamp} <= {end_time}"

                # Verify chronological ordering (oldest first)
                for i in range(len(history) - 1):
                    assert history[i].timestamp <= history[i + 1].timestamp, \
                        f"Time range query results should be in chronological order: " \
                        f"record {i} timestamp {history[i].timestamp} should be <= " \
                        f"record {i+1} timestamp {history[i + 1].timestamp}"

                # Verify timestamps match expected (in order)
                retrieved_timestamps = [vs.timestamp for vs in history]
                assert retrieved_timestamps == sorted(expected_timestamps), \
                    f"Retrieved timestamps should match expected timestamps in chronological order"

        finally:
            db_session.close()

    @given(
        num_records=st.integers(min_value=5, max_value=15),
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.property_tests
    def test_out_of_order_insertion_maintains_chronological_retrieval(self, num_records):
        """
        Property 11: Historical Data Chronological Ordering
        Validates: Requirements 4.2

        For any sequence of vital signs inserted in random order, historical
        data queries should still return them in correct chronological order.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vitals_service = VitalSignsService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=ArrivalModeEnum.AMBULANCE,
                acuity_level=4
            )

            # Generate timestamps in sequential order
            base_time = datetime.utcnow() - timedelta(hours=num_records)
            timestamps = []
            for i in range(num_records):
                timestamp = base_time + timedelta(hours=i)
                timestamps.append(timestamp)

            # Shuffle timestamps to simulate out-of-order insertion
            import random
            shuffled_timestamps = timestamps.copy()
            random.shuffle(shuffled_timestamps)

            # Create vital signs with shuffled timestamps
            for idx, timestamp in enumerate(shuffled_timestamps):
                vitals = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=80.0 + idx,
                    systolic_bp=125.0 + idx,
                    diastolic_bp=82.0 + idx * 0.5,
                    respiratory_rate=17.0 + idx * 0.3,
                    oxygen_saturation=96.0 - idx * 0.1,
                    temperature=37.0 + idx * 0.05,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )

                risk_repo.create(
                    patient_id=patient.patient_id,
                    vital_signs_id=vitals.id,
                    risk_score=0.25 + idx * 0.04,
                    risk_flag=(idx * 0.04) >= 0.35,
                    assessment_time=timestamp + timedelta(seconds=5),
                    model_version="test_v1"
                )

            # Get historical data - should be in chronological order despite insertion order
            history = vitals_service.get_vital_signs_history(patient.patient_id)

            # Verify correct number of records
            assert len(history) == num_records, \
                f"Expected {num_records} records, got {len(history)}"

            # Verify chronological ordering (oldest first)
            retrieved_timestamps = [vs.timestamp for vs in history]
            expected_timestamps = sorted(timestamps)
            
            assert retrieved_timestamps == expected_timestamps, \
                f"Historical data should be in chronological order regardless of insertion order"

            # Verify strict ordering
            for i in range(len(history) - 1):
                assert history[i].timestamp < history[i + 1].timestamp, \
                    f"Each record should have an earlier timestamp than the next: " \
                    f"{history[i].timestamp} < {history[i + 1].timestamp}"

        finally:
            db_session.close()

    @given(
        num_patients=st.integers(min_value=2, max_value=4),
        records_per_patient=st.integers(min_value=3, max_value=8),
    )
    @settings(max_examples=30, deadline=15000)
    @pytest.mark.property_tests
    def test_chronological_ordering_isolated_per_patient(self, num_patients, records_per_patient):
        """
        Property 11: Historical Data Chronological Ordering
        Validates: Requirements 4.2

        For any set of patients with historical data, each patient's historical
        data should be properly ordered independently of other patients.
        """
        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vitals_service = VitalSignsService(db_session)

            # Create multiple patients with their own historical data
            patient_data = {}
            base_time = datetime.utcnow() - timedelta(hours=records_per_patient * num_patients)

            for p_idx in range(num_patients):
                # Generate unique patient ID
                patient_id = generate_unique_patient_id()
                
                # Create patient
                patient = patient_repo.create(
                    patient_id=patient_id,
                    arrival_mode=ArrivalModeEnum.AMBULANCE if p_idx % 2 == 0 else ArrivalModeEnum.WALK_IN,
                    acuity_level=(p_idx % 5) + 1
                )

                # Create vital signs for this patient
                patient_timestamps = []
                for r_idx in range(records_per_patient):
                    # Offset timestamps for each patient to create interleaved data
                    timestamp = base_time + timedelta(hours=r_idx * num_patients + p_idx)
                    patient_timestamps.append(timestamp)
                    
                    vitals = vitals_repo.create(
                        patient_id=patient.patient_id,
                        heart_rate=70.0 + p_idx * 10 + r_idx,
                        systolic_bp=110.0 + p_idx * 5 + r_idx,
                        diastolic_bp=70.0 + p_idx * 3 + r_idx * 0.5,
                        respiratory_rate=14.0 + p_idx + r_idx * 0.3,
                        oxygen_saturation=95.0 + p_idx - r_idx * 0.1,
                        temperature=36.0 + p_idx * 0.2 + r_idx * 0.05,
                        timestamp=timestamp,
                        recorded_by="test_system"
                    )

                    risk_repo.create(
                        patient_id=patient.patient_id,
                        vital_signs_id=vitals.id,
                        risk_score=0.1 + p_idx * 0.1 + r_idx * 0.05,
                        risk_flag=(p_idx * 0.1 + r_idx * 0.05) >= 0.4,
                        assessment_time=timestamp + timedelta(seconds=5),
                        model_version="test_v1"
                    )

                patient_data[patient.patient_id] = sorted(patient_timestamps)

            # Verify each patient's historical data is properly ordered
            for patient_id, expected_timestamps in patient_data.items():
                history = vitals_service.get_vital_signs_history(patient_id)

                # Verify correct number of records
                assert len(history) == records_per_patient, \
                    f"Patient {patient_id} should have {records_per_patient} records, got {len(history)}"

                # Verify chronological ordering
                retrieved_timestamps = [vs.timestamp for vs in history]
                assert retrieved_timestamps == expected_timestamps, \
                    f"Patient {patient_id} historical data should be in chronological order"

                # Verify strict ordering
                for i in range(len(history) - 1):
                    assert history[i].timestamp < history[i + 1].timestamp, \
                        f"Patient {patient_id} records should be strictly ordered: " \
                        f"{history[i].timestamp} < {history[i + 1].timestamp}"

                # Verify all records belong to this patient
                for vs in history:
                    assert vs.patient_id == patient_id, \
                        f"All records should belong to patient {patient_id}"

        finally:
            db_session.close()

    @given(
        num_records=st.integers(min_value=10, max_value=20),
        limit=st.integers(min_value=3, max_value=8),
    )
    @settings(max_examples=30, deadline=10000)
    @pytest.mark.property_tests
    def test_limited_query_maintains_chronological_order(self, num_records, limit):
        """
        Property 11: Historical Data Chronological Ordering
        Validates: Requirements 4.2

        For any historical data query with a limit, the system should return
        the specified number of records in correct chronological order.
        """
        # Generate unique patient ID for each test iteration
        patient_id = generate_unique_patient_id()

        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            risk_repo = RiskAssessmentRepository(db_session)
            vitals_service = VitalSignsService(db_session)

            # Create patient
            patient = patient_repo.create(
                patient_id=patient_id,
                arrival_mode=ArrivalModeEnum.WALK_IN,
                acuity_level=3
            )

            # Create many vital signs records
            base_time = datetime.utcnow() - timedelta(hours=num_records)
            all_timestamps = []
            
            for i in range(num_records):
                timestamp = base_time + timedelta(hours=i)
                all_timestamps.append(timestamp)
                
                vitals = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=72.0 + i,
                    systolic_bp=118.0 + i,
                    diastolic_bp=78.0 + i * 0.5,
                    respiratory_rate=16.0 + i * 0.2,
                    oxygen_saturation=97.5 - i * 0.1,
                    temperature=36.7 + i * 0.05,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )

                risk_repo.create(
                    patient_id=patient.patient_id,
                    vital_signs_id=vitals.id,
                    risk_score=0.18 + i * 0.03,
                    risk_flag=(i * 0.03) >= 0.35,
                    assessment_time=timestamp + timedelta(seconds=5),
                    model_version="test_v1"
                )

            # Get limited historical data
            history = vitals_service.get_vital_signs_history(
                patient.patient_id,
                limit=limit
            )

            # Verify correct number of records (should be limited)
            assert len(history) <= limit, \
                f"Should return at most {limit} records, got {len(history)}"

            # Verify chronological ordering (oldest first)
            for i in range(len(history) - 1):
                assert history[i].timestamp <= history[i + 1].timestamp, \
                    f"Limited query results should be in chronological order: " \
                    f"record {i} timestamp {history[i].timestamp} should be <= " \
                    f"record {i+1} timestamp {history[i + 1].timestamp}"

            # Verify timestamps are in order
            retrieved_timestamps = [vs.timestamp for vs in history]
            assert retrieved_timestamps == sorted(retrieved_timestamps), \
                f"Limited query should return chronologically ordered results"

        finally:
            db_session.close()
