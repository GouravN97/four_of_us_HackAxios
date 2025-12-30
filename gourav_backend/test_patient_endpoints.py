"""Quick test for patient endpoints."""
from fastapi.testclient import TestClient
from src.api.main import app
from src.utils.database import reset_database

# Initialize test database
reset_database(test_mode=True)

client = TestClient(app)

# Test 1: Register a patient
print('Test 1: Register patient...')
registration_data = {
    'patient_id': 'TEST001',
    'arrival_mode': 'Ambulance',
    'acuity_level': 3,
    'initial_vitals': {
        'heart_rate': 85.0,
        'systolic_bp': 140.0,
        'diastolic_bp': 90.0,
        'respiratory_rate': 18.0,
        'oxygen_saturation': 96.0,
        'temperature': 37.2,
        'timestamp': '2024-01-15T10:30:00Z'
    }
}
response = client.post('/patients', json=registration_data)
print(f'  Status: {response.status_code}')
if response.status_code == 201:
    print('  Patient registered successfully!')
    data = response.json()
    print(f'  Patient ID: {data["patient_id"]}')
    print(f'  Risk Score: {data["current_risk"]["risk_score"]}')
else:
    print(f'  Error: {response.json()}')

# Test 2: Get patient status
print('Test 2: Get patient status...')
response = client.get('/patients/TEST001')
print(f'  Status: {response.status_code}')
if response.status_code == 200:
    print('  Patient status retrieved successfully!')
else:
    print(f'  Error: {response.json()}')

# Test 3: Get high-risk patients
print('Test 3: Get high-risk patients...')
response = client.get('/patients/high-risk')
print(f'  Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'  High-risk patients count: {data["total_count"]}')
else:
    print(f'  Error: {response.json()}')

# Test 4: Get non-existent patient
print('Test 4: Get non-existent patient...')
response = client.get('/patients/NONEXISTENT')
print(f'  Status: {response.status_code}')
if response.status_code == 404:
    print('  Correctly returned 404 for non-existent patient!')
else:
    print(f'  Unexpected response: {response.json()}')

# Test 5: Duplicate registration
print('Test 5: Duplicate registration...')
response = client.post('/patients', json=registration_data)
print(f'  Status: {response.status_code}')
if response.status_code == 409:
    print('  Correctly returned 409 for duplicate patient!')
else:
    print(f'  Unexpected response: {response.json()}')

print('All tests completed!')
