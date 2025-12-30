import sqlite3
import os
db_path = os.path.join(os.path.dirname(__file__), 'patient_risk_dev.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print('=== DATABASE SUMMARY ===')
c.execute('SELECT COUNT(*) FROM patients')
print(f'Total Patients: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM vital_signs')
print(f'Total Vital Signs: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM risk_assessments')
print(f'Total Risk Assessments: {c.fetchone()[0]}')

print('\n=== PATIENTS ===')
c.execute('SELECT patient_id, arrival_mode, acuity_level, registration_time FROM patients ORDER BY patient_id')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}, Acuity={r[2]}, Registered={r[3]}')

print('\n=== VITALS PER PATIENT ===')
c.execute('SELECT patient_id, COUNT(*), MIN(timestamp), MAX(timestamp) FROM vital_signs GROUP BY patient_id ORDER BY patient_id')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} readings, from {r[2][:16]} to {r[3][:16]}')

print('\n=== SAMPLE VITALS (P001) - checking 5-min intervals ===')
c.execute('SELECT timestamp, heart_rate, systolic_bp, oxygen_saturation FROM vital_signs WHERE patient_id="P001" ORDER BY timestamp')
rows = c.fetchall()
for i, r in enumerate(rows):
    print(f'  {r[0][:19]}: HR={r[1]}, BP={r[2]}, O2={r[3]}')
