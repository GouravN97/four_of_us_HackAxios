"""
Simple test to verify vital signs endpoints are working correctly.
"""

import sys
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.models.db_models import Base
from src.utils.database import get_db

# Create test database
TEST_DATABASE_URL = "sqlite:///./test_vitals.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_vital_signs_endpoints():
    """Test vital signs update and history endpoints."""
    print("\n=== Testing Vital Signs Endpoints ===\n")
    
    # Step 1: Register a patient
    print("1. Registering a patient...")
    registration_data = {
        "patient_id": "TEST_VITALS_001",
        "arrival_mode": "Ambulance",
        "acuity_level": 3,
        "initial_vitals": {
            "heart_rate": 85.0,
            "systolic_bp": 140.0,
            "diastolic_bp": 90.0,
            "respiratory_rate": 18.0,
            "oxygen_saturation": 96.0,
            "temperature": 37.2,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    response = client.post("/patients", json=registration_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        print(f"   ✓ Patient registered successfully")
        patient_data = response.json()
        print(f"   Initial risk score: {patient_data['current_risk']['risk_score']}")
    else:
        print(f"   ✗ Failed to register patient: {response.text}")
        return False
    
    # Step 2: Update vital signs
    print("\n2. Updating vital signs...")
    vital_signs_update = {
        "heart_rate": 92.0,
        "systolic_bp": 145.0,
        "diastolic_bp": 95.0,
        "respiratory_rate": 20.0,
        "oxygen_saturation": 94.0,
        "temperature": 37.5
    }
    
    response = client.put("/patients/TEST_VITALS_001/vitals", json=vital_signs_update)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Vital signs updated successfully")
        update_response = response.json()
        print(f"   Message: {update_response['message']}")
    else:
        print(f"   ✗ Failed to update vital signs: {response.text}")
        return False
    
    # Step 3: Update vital signs again (to have more history)
    print("\n3. Updating vital signs again...")
    vital_signs_update_2 = {
        "heart_rate": 88.0,
        "systolic_bp": 138.0,
        "diastolic_bp": 88.0,
        "respiratory_rate": 17.0,
        "oxygen_saturation": 97.0,
        "temperature": 37.0
    }
    
    response = client.put("/patients/TEST_VITALS_001/vitals", json=vital_signs_update_2)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Vital signs updated successfully")
    else:
        print(f"   ✗ Failed to update vital signs: {response.text}")
        return False
    
    # Step 4: Get patient history
    print("\n4. Retrieving patient history...")
    response = client.get("/patients/TEST_VITALS_001/history")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ History retrieved successfully")
        history_data = response.json()
        print(f"   Total data points: {history_data['total_count']}")
        print(f"   Time range: {history_data['start_time']} to {history_data['end_time']}")
        
        # Verify chronological ordering (Requirement 4.2)
        if history_data['data_points']:
            print("\n   Data points (chronological order):")
            for i, point in enumerate(history_data['data_points'], 1):
                vitals = point['vitals']
                risk = point['risk_assessment']
                print(f"   {i}. Time: {vitals['timestamp']}")
                print(f"      HR: {vitals['heart_rate']}, BP: {vitals['systolic_bp']}/{vitals['diastolic_bp']}")
                print(f"      Risk: {risk['risk_score']:.3f} (flag: {risk['risk_flag']})")
            
            # Verify ordering
            timestamps = [point['vitals']['timestamp'] for point in history_data['data_points']]
            is_ordered = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            if is_ordered:
                print(f"\n   ✓ Data is correctly ordered chronologically")
            else:
                print(f"\n   ✗ Data is NOT correctly ordered chronologically")
                return False
    else:
        print(f"   ✗ Failed to retrieve history: {response.text}")
        return False
    
    # Step 5: Test history with time range
    print("\n5. Testing history with time range...")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    response = client.get(
        f"/patients/TEST_VITALS_001/history",
        params={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ History with time range retrieved successfully")
        history_data = response.json()
        print(f"   Data points in range: {history_data['total_count']}")
    else:
        print(f"   ✗ Failed to retrieve history with time range: {response.text}")
        return False
    
    # Step 6: Test with non-existent patient
    print("\n6. Testing with non-existent patient...")
    response = client.put("/patients/NONEXISTENT/vitals", json=vital_signs_update)
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print(f"   ✓ Correctly returned 404 for non-existent patient")
    else:
        print(f"   ✗ Expected 404, got {response.status_code}")
        return False
    
    response = client.get("/patients/NONEXISTENT/history")
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print(f"   ✓ Correctly returned 404 for non-existent patient")
    else:
        print(f"   ✗ Expected 404, got {response.status_code}")
        return False
    
    # Step 7: Test with invalid vital signs
    print("\n7. Testing with invalid vital signs...")
    invalid_vitals = {
        "heart_rate": 250.0,  # Out of range
        "systolic_bp": 140.0,
        "diastolic_bp": 90.0,
        "respiratory_rate": 18.0,
        "oxygen_saturation": 96.0,
        "temperature": 37.2
    }
    
    response = client.put("/patients/TEST_VITALS_001/vitals", json=invalid_vitals)
    print(f"   Status: {response.status_code}")
    if response.status_code == 422:  # Validation error
        print(f"   ✓ Correctly rejected invalid vital signs")
    else:
        print(f"   ✗ Expected 422, got {response.status_code}")
        return False
    
    print("\n=== All Tests Passed! ===\n")
    return True


if __name__ == "__main__":
    try:
        success = test_vital_signs_endpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
