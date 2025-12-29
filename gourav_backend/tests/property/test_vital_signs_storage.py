"""
Property-based tests for vital signs storage functionality.
Tests that vital signs storage maintains data integrity and chronological ordering.
"""

from datetime import datetime, timezone, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.db_models import ArrivalModeEnum
from src.repositories.patient_repository import PatientRepository
from src.repositories.vital_signs_repository import VitalSignsRepository
from src.utils.database import get_test_db, create_test_database


class TestVitalSignsStorage:
    """Property 5: Vital Signs Storage with Timestamps - Validates Requirements 2.2, 2.4"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up clean test database for each test."""
        create_test_database()

    @given(
        vital_signs_data=st.lists(
            st.tuples(
                st.floats(min_value=30, max_value=200),  # heart_rate
                st.floats(min_value=50, max_value=300),  # systolic_bp
                st.floats(min_value=20, max_value=200),  # diastolic_bp
                st.floats(min_value=5, max_value=60),    # respiratory_rate
                st.floats(min_value=50, max_value=100),  # oxygen_saturation
                st.floats(min_value=30, max_value=45),   # temperature
                st.datetimes(
                    min_value=datetime(2020, 1, 1),
                    max_value=datetime(2030, 12, 31)
                )  # timestamp - timezone-naive
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=1000)
    @pytest.mark.property_tests
    def test_vital_signs_storage_with_timestamps(self, vital_signs_data):
        """
        Property 5: Vital Signs Storage with Timestamps
        Validates: Requirements 2.2, 2.4

        For any valid vital signs update, the system should store the measurements 
        with accurate timestamps and maintain chronological order.
        """
        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            
            # Create a test patient first
            patient = patient_repo.create(
                patient_id=None,
                arrival_mode=ArrivalModeEnum.AMBULANCE,
                acuity_level=3
            )
            
            created_vital_signs = []
            
            # Store all vital signs
            for (heart_rate, systolic_bp, diastolic_bp, respiratory_rate, 
                 oxygen_saturation, temperature, timestamp) in vital_signs_data:
                
                # Ensure diastolic BP is less than systolic BP
                if diastolic_bp >= systolic_bp:
                    diastolic_bp = systolic_bp - 1.0
                    if diastolic_bp < 20:
                        systolic_bp = 21.0
                        diastolic_bp = 20.0
                
                vital_signs = vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=heart_rate,
                    systolic_bp=systolic_bp,
                    diastolic_bp=diastolic_bp,
                    respiratory_rate=respiratory_rate,
                    oxygen_saturation=oxygen_saturation,
                    temperature=temperature,
                    timestamp=timestamp,
                    recorded_by="test_system"
                )
                
                created_vital_signs.append(vital_signs)
            
            # Verify all vital signs were stored
            assert len(created_vital_signs) == len(vital_signs_data)
            
            # Retrieve all vital signs for the patient
            retrieved_vitals = vitals_repo.get_for_patient(patient.patient_id)
            assert len(retrieved_vitals) == len(vital_signs_data)
            
            # Verify chronological ordering (newest first by default)
            for i in range(len(retrieved_vitals) - 1):
                assert retrieved_vitals[i].timestamp >= retrieved_vitals[i + 1].timestamp, \
                    f"Vital signs should be ordered by timestamp (newest first): " \
                    f"{retrieved_vitals[i].timestamp} should be >= {retrieved_vitals[i + 1].timestamp}"
            
            # Verify each vital signs record matches what was stored
            retrieved_by_id = {vs.id: vs for vs in retrieved_vitals}
            
            for original_vs in created_vital_signs:
                retrieved_vs = retrieved_by_id[original_vs.id]
                
                # Verify all vital signs values match
                assert retrieved_vs.heart_rate == original_vs.heart_rate
                assert retrieved_vs.systolic_bp == original_vs.systolic_bp
                assert retrieved_vs.diastolic_bp == original_vs.diastolic_bp
                assert retrieved_vs.respiratory_rate == original_vs.respiratory_rate
                assert retrieved_vs.oxygen_saturation == original_vs.oxygen_saturation
                assert retrieved_vs.temperature == original_vs.temperature
                
                # Verify timestamps are preserved exactly
                assert retrieved_vs.timestamp == original_vs.timestamp
                assert retrieved_vs.patient_id == patient.patient_id
                assert retrieved_vs.recorded_by == "test_system"
                
                # Verify created_at timestamp exists and is reasonable
                assert retrieved_vs.created_at is not None
                assert retrieved_vs.created_at <= datetime.utcnow()
                
        finally:
            db_session.close()

    @given(
        base_time=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2025, 1, 1)
        ),
        num_records=st.integers(min_value=5, max_value=15)
    )
    @settings(max_examples=30, deadline=1000)
    @pytest.mark.property_tests
    def test_vital_signs_chronological_ordering(self, base_time, num_records):
        """
        Property 5: Vital Signs Storage with Timestamps
        Validates: Requirements 2.2, 2.4

        For any sequence of vital signs with different timestamps,
        the system should maintain proper chronological ordering.
        """
        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            
            # Create a test patient
            patient = patient_repo.create(
                patient_id=None,
                arrival_mode=ArrivalModeEnum.WALK_IN,
                acuity_level=2
            )
            
            # Generate timestamps in sequential order
            timestamps = []
            for i in range(num_records):
                # Create timestamps spread over several hours
                offset_minutes = i * 30  # 30 minutes apart
                timestamp = base_time + timedelta(minutes=offset_minutes)
                timestamps.append(timestamp)
            
            # Shuffle the timestamps to simulate out-of-order insertion
            import random
            shuffled_timestamps = timestamps.copy()
            random.shuffle(shuffled_timestamps)
            
            # Create vital signs with shuffled timestamps
            for timestamp in shuffled_timestamps:
                vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=75.0,
                    systolic_bp=120.0,
                    diastolic_bp=80.0,
                    respiratory_rate=16.0,
                    oxygen_saturation=98.0,
                    temperature=37.0,
                    timestamp=timestamp
                )
            
            # Retrieve vital signs - should be in chronological order (newest first)
            retrieved_vitals = vitals_repo.get_for_patient(patient.patient_id)
            
            # Verify correct number of records
            assert len(retrieved_vitals) == num_records
            
            # Verify chronological ordering (newest first)
            retrieved_timestamps = [vs.timestamp for vs in retrieved_vitals]
            sorted_timestamps = sorted(timestamps, reverse=True)  # Newest first
            
            assert retrieved_timestamps == sorted_timestamps, \
                f"Retrieved timestamps {retrieved_timestamps} should match sorted timestamps {sorted_timestamps}"
            
            # Test time range queries
            if num_records >= 3:
                # Get middle portion of time range
                start_time = sorted_timestamps[-2]  # Second oldest
                end_time = sorted_timestamps[1]     # Second newest
                
                range_vitals = vitals_repo.get_for_patient_in_time_range(
                    patient.patient_id, start_time, end_time
                )
                
                # Should get records within the range (inclusive)
                expected_count = sum(1 for ts in timestamps if start_time <= ts <= end_time)
                assert len(range_vitals) == expected_count
                
                # Verify all returned records are within range
                for vs in range_vitals:
                    assert start_time <= vs.timestamp <= end_time
                
                # Verify chronological ordering within range (oldest first for range queries)
                range_timestamps = [vs.timestamp for vs in range_vitals]
                assert range_timestamps == sorted(range_timestamps)
                
        finally:
            db_session.close()

    @given(
        patient_count=st.integers(min_value=2, max_value=5),
        vitals_per_patient=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=2000)
    @pytest.mark.property_tests
    def test_vital_signs_patient_isolation(self, patient_count, vitals_per_patient):
        """
        Property 5: Vital Signs Storage with Timestamps
        Validates: Requirements 2.2, 2.4

        For any set of patients with vital signs, each patient's vital signs
        should be properly isolated and retrievable independently.
        """
        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            
            # Create multiple patients
            patients = []
            for i in range(patient_count):
                patient = patient_repo.create(
                    patient_id=None,
                    arrival_mode=ArrivalModeEnum.AMBULANCE if i % 2 == 0 else ArrivalModeEnum.WALK_IN,
                    acuity_level=(i % 5) + 1
                )
                patients.append(patient)
            
            # Create vital signs for each patient
            patient_vital_counts = {}
            base_time = datetime.utcnow()
            
            for patient in patients:
                patient_vital_counts[patient.patient_id] = vitals_per_patient
                
                for j in range(vitals_per_patient):
                    timestamp = base_time + timedelta(minutes=j * 15)
                    
                    vitals_repo.create(
                        patient_id=patient.patient_id,
                        heart_rate=70.0 + j,  # Vary slightly per record
                        systolic_bp=110.0 + j,
                        diastolic_bp=70.0 + j,
                        respiratory_rate=15.0 + j,
                        oxygen_saturation=95.0 + j,
                        temperature=36.5 + (j * 0.1),
                        timestamp=timestamp
                    )
            
            # Verify each patient's vital signs are properly isolated
            for patient in patients:
                patient_vitals = vitals_repo.get_for_patient(patient.patient_id)
                
                # Verify correct count
                expected_count = patient_vital_counts[patient.patient_id]
                assert len(patient_vitals) == expected_count, \
                    f"Patient {patient.patient_id} should have {expected_count} vital signs, got {len(patient_vitals)}"
                
                # Verify all vital signs belong to this patient
                for vs in patient_vitals:
                    assert vs.patient_id == patient.patient_id, \
                        f"Vital signs {vs.id} should belong to patient {patient.patient_id}, got {vs.patient_id}"
                
                # Verify latest vital signs retrieval
                latest_vitals = vitals_repo.get_latest_for_patient(patient.patient_id)
                if patient_vitals:
                    assert latest_vitals is not None
                    assert latest_vitals.patient_id == patient.patient_id
                    assert latest_vitals.timestamp == max(vs.timestamp for vs in patient_vitals)
                
                # Verify count method
                count = vitals_repo.get_count_for_patient(patient.patient_id)
                assert count == expected_count
            
            # Verify total isolation - no cross-contamination
            all_patient_ids = {p.patient_id for p in patients}
            for patient in patients:
                patient_vitals = vitals_repo.get_for_patient(patient.patient_id)
                for vs in patient_vitals:
                    assert vs.patient_id in all_patient_ids, \
                        f"Vital signs should only reference valid patient IDs"
                    assert vs.patient_id == patient.patient_id, \
                        f"Patient {patient.patient_id} should not have vital signs from other patients"
                        
        finally:
            db_session.close()

    @given(
        hours_back=st.integers(min_value=1, max_value=24)
    )
    @settings(max_examples=10, deadline=2000)
    @pytest.mark.property_tests
    def test_vital_signs_time_range_queries(self, hours_back):
        """
        Property 5: Vital Signs Storage with Timestamps
        Validates: Requirements 2.2, 2.4

        For any time range query, the system should return only vital signs
        within the specified time range in correct chronological order.
        """
        db_session = next(get_test_db())
        try:
            patient_repo = PatientRepository(db_session)
            vitals_repo = VitalSignsRepository(db_session)
            
            # Create a test patient
            patient = patient_repo.create(
                patient_id=None,
                arrival_mode=ArrivalModeEnum.AMBULANCE,
                acuity_level=4
            )
            
            # Create vital signs over a longer time period
            now = datetime.utcnow()
            all_timestamps = []
            
            # Create records spanning more time than our query range
            total_hours = hours_back + 12  # Extra time outside our query range
            for hour in range(total_hours):
                timestamp = now - timedelta(hours=hour)
                all_timestamps.append(timestamp)
                
                vitals_repo.create(
                    patient_id=patient.patient_id,
                    heart_rate=80.0,
                    systolic_bp=130.0,
                    diastolic_bp=85.0,
                    respiratory_rate=18.0,
                    oxygen_saturation=96.0,
                    temperature=37.2,
                    timestamp=timestamp
                )
            
            # Query for recent vital signs within our time range
            recent_vitals = vitals_repo.get_recent_for_patient(patient.patient_id, hours_back)
            
            # Calculate expected timestamps within range
            cutoff_time = now - timedelta(hours=hours_back)
            expected_timestamps = [ts for ts in all_timestamps if ts >= cutoff_time]
            
            # Verify correct number of records returned (allow for small timing differences)
            assert len(recent_vitals) >= len(expected_timestamps) - 1, \
                f"Expected at least {len(expected_timestamps) - 1} recent vital signs, got {len(recent_vitals)}"
            assert len(recent_vitals) <= len(expected_timestamps) + 1, \
                f"Expected at most {len(expected_timestamps) + 1} recent vital signs, got {len(recent_vitals)}"
            
            # Verify all returned records are within time range
            for vs in recent_vitals:
                assert vs.timestamp >= cutoff_time, \
                    f"Vital signs timestamp {vs.timestamp} should be >= {cutoff_time}"
                assert vs.timestamp <= now, \
                    f"Vital signs timestamp {vs.timestamp} should be <= {now}"
            
            # Verify chronological ordering (oldest first for time range queries)
            retrieved_timestamps = [vs.timestamp for vs in recent_vitals]
            assert retrieved_timestamps == sorted(retrieved_timestamps), \
                f"Time range query results should be in chronological order"
            
            # Test specific time range query
            if len(expected_timestamps) >= 2:
                start_time = expected_timestamps[-1]  # Oldest in range
                end_time = expected_timestamps[0]     # Newest in range
                
                range_vitals = vitals_repo.get_for_patient_in_time_range(
                    patient.patient_id, start_time, end_time
                )
                
                # Should get all records in range
                assert len(range_vitals) == len(expected_timestamps)
                
                # Verify all are within range
                for vs in range_vitals:
                    assert start_time <= vs.timestamp <= end_time
                    
        finally:
            db_session.close()