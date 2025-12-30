#!/usr/bin/env python3
"""
Database Population Script for VERIQ Hospital Management System

This script populates the database with realistic patient data that matches
the frontend component requirements (Frame2, Frame2_1, Frame3, Frame4).

Run this script after starting the backend server to populate the database
with sample patients and their vital signs history.
"""

import random
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DatabasePopulator:
    """Populates the database with realistic patient data."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Patient profiles for realistic data generation
        self.patient_profiles = self._create_patient_profiles()
    
    def _create_patient_profiles(self) -> List[Dict]:
        """Create diverse patient profiles with different risk levels."""
        return [
            # Critical patients (High risk)
            {
                "id": "P001",
                "arrival_mode": "Ambulance",
                "acuity_level": 5,
                "profile": "critical_cardiac",
                "base_vitals": {
                    "heart_rate": (95, 120),
                    "systolic_bp": (150, 180),
                    "diastolic_bp": (95, 110),
                    "respiratory_rate": (22, 28),
                    "oxygen_saturation": (88, 94),
                    "temperature": (37.8, 39.0)
                },
                "deterioration_risk": "High",
                "severity": "Critical",
                "explainability": "High blood pressure, chest pain symptoms, history of cardiac issues. Elevated heart rate and blood pressure indicate cardiac stress."
            },
            {
                "id": "P002",
                "arrival_mode": "Ambulance",
                "acuity_level": 5,
                "profile": "critical_respiratory",
                "base_vitals": {
                    "heart_rate": (100, 130),
                    "systolic_bp": (130, 150),
                    "diastolic_bp": (85, 100),
                    "respiratory_rate": (28, 38),
                    "oxygen_saturation": (85, 92),
                    "temperature": (38.0, 39.5)
                },
                "deterioration_risk": "High",
                "severity": "Critical",
                "explainability": "Breathing difficulties, oxygen levels dropping. Respiratory distress with elevated respiratory rate and low oxygen saturation."
            },
            {
                "id": "P003",
                "arrival_mode": "Ambulance",
                "acuity_level": 5,
                "profile": "critical_stroke",
                "base_vitals": {
                    "heart_rate": (85, 110),
                    "systolic_bp": (170, 200),
                    "diastolic_bp": (100, 120),
                    "respiratory_rate": (18, 24),
                    "oxygen_saturation": (92, 96),
                    "temperature": (37.0, 37.8)
                },
                "deterioration_risk": "High",
                "severity": "Critical",
                "explainability": "Stroke symptoms, time-sensitive treatment required. Severely elevated blood pressure with neurological symptoms."
            },
            # Moderate risk patients
            {
                "id": "P004",
                "arrival_mode": "Walk-in",
                "acuity_level": 3,
                "profile": "moderate_fever",
                "base_vitals": {
                    "heart_rate": (85, 100),
                    "systolic_bp": (120, 140),
                    "diastolic_bp": (75, 90),
                    "respiratory_rate": (18, 22),
                    "oxygen_saturation": (94, 97),
                    "temperature": (38.5, 39.5)
                },
                "deterioration_risk": "Medium",
                "severity": "Moderate",
                "explainability": "Moderate fever, respiratory symptoms, no underlying conditions. Monitoring for potential infection progression."
            },
            {
                "id": "P005",
                "arrival_mode": "Walk-in",
                "acuity_level": 3,
                "profile": "moderate_abdominal",
                "base_vitals": {
                    "heart_rate": (80, 95),
                    "systolic_bp": (115, 135),
                    "diastolic_bp": (70, 85),
                    "respiratory_rate": (16, 20),
                    "oxygen_saturation": (96, 99),
                    "temperature": (37.2, 38.2)
                },
                "deterioration_risk": "Medium",
                "severity": "Moderate",
                "explainability": "Abdominal pain, requires further diagnosis. Vital signs stable but pain assessment indicates need for monitoring."
            },
            {
                "id": "P006",
                "arrival_mode": "Ambulance",
                "acuity_level": 4,
                "profile": "moderate_diabetic",
                "base_vitals": {
                    "heart_rate": (90, 110),
                    "systolic_bp": (100, 120),
                    "diastolic_bp": (60, 75),
                    "respiratory_rate": (18, 24),
                    "oxygen_saturation": (95, 98),
                    "temperature": (36.5, 37.5)
                },
                "deterioration_risk": "High",
                "severity": "Critical",
                "explainability": "Diabetic emergency, blood sugar levels unstable, requires immediate attention. Risk of hypoglycemic shock."
            },
            # Low risk patients
            {
                "id": "P007",
                "arrival_mode": "Walk-in",
                "acuity_level": 2,
                "profile": "low_minor_injury",
                "base_vitals": {
                    "heart_rate": (65, 80),
                    "systolic_bp": (110, 125),
                    "diastolic_bp": (70, 80),
                    "respiratory_rate": (14, 18),
                    "oxygen_saturation": (97, 100),
                    "temperature": (36.5, 37.2)
                },
                "deterioration_risk": "Low",
                "severity": "Minor",
                "explainability": "Minor injury, no complications expected. Stable vital signs, routine treatment sufficient."
            },
            {
                "id": "P008",
                "arrival_mode": "Walk-in",
                "acuity_level": 1,
                "profile": "low_routine",
                "base_vitals": {
                    "heart_rate": (60, 75),
                    "systolic_bp": (115, 125),
                    "diastolic_bp": (70, 80),
                    "respiratory_rate": (12, 16),
                    "oxygen_saturation": (98, 100),
                    "temperature": (36.4, 37.0)
                },
                "deterioration_risk": "Low",
                "severity": "Minor",
                "explainability": "Routine checkup follow-up, minor concerns. All vital signs within normal range."
            },
            {
                "id": "P009",
                "arrival_mode": "Walk-in",
                "acuity_level": 2,
                "profile": "low_back_pain",
                "base_vitals": {
                    "heart_rate": (70, 85),
                    "systolic_bp": (120, 135),
                    "diastolic_bp": (75, 85),
                    "respiratory_rate": (14, 18),
                    "oxygen_saturation": (97, 99),
                    "temperature": (36.5, 37.2)
                },
                "deterioration_risk": "Medium",
                "severity": "Moderate",
                "explainability": "Back pain, possible disc issue. Requires imaging and pain management."
            },
            {
                "id": "P010",
                "arrival_mode": "Ambulance",
                "acuity_level": 5,
                "profile": "critical_allergic",
                "base_vitals": {
                    "heart_rate": (110, 140),
                    "systolic_bp": (85, 100),
                    "diastolic_bp": (50, 65),
                    "respiratory_rate": (24, 32),
                    "oxygen_saturation": (88, 94),
                    "temperature": (37.5, 38.5)
                },
                "deterioration_risk": "High",
                "severity": "Critical",
                "explainability": "Severe allergic reaction, anaphylaxis risk. Hypotension and respiratory distress require immediate intervention."
            },
        ]
    
    def generate_vitals(self, profile: Dict, variation: float = 0.1) -> Dict:
        """Generate vital signs based on patient profile with some variation."""
        base = profile["base_vitals"]
        
        def vary(range_tuple: Tuple[float, float]) -> float:
            base_val = random.uniform(range_tuple[0], range_tuple[1])
            variation_amount = base_val * variation
            return round(base_val + random.uniform(-variation_amount, variation_amount), 1)
        
        vitals = {
            "heart_rate": vary(base["heart_rate"]),
            "systolic_bp": vary(base["systolic_bp"]),
            "diastolic_bp": vary(base["diastolic_bp"]),
            "respiratory_rate": vary(base["respiratory_rate"]),
            "oxygen_saturation": min(100, vary(base["oxygen_saturation"])),
            "temperature": vary(base["temperature"])
        }
        
        # Ensure diastolic < systolic
        if vitals["diastolic_bp"] >= vitals["systolic_bp"]:
            vitals["diastolic_bp"] = vitals["systolic_bp"] - 20
        
        return vitals
    
    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def register_patient(self, profile: Dict, timestamp: datetime) -> bool:
        """Register a patient with initial vital signs."""
        vitals = self.generate_vitals(profile)
        vitals["timestamp"] = timestamp.isoformat() + "Z"
        
        patient_data = {
            "patient_id": profile["id"],
            "arrival_mode": profile["arrival_mode"],
            "acuity_level": profile["acuity_level"],
            "initial_vitals": vitals
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/patients",
                json=patient_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 201:
                return True
            elif response.status_code == 409:
                print(f"   ⚠️  Patient {profile['id']} already exists, skipping registration")
                return True  # Patient exists, continue with updates
            else:
                print(f"   ❌ Failed to register {profile['id']}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error registering {profile['id']}: {e}")
            return False
    
    def update_vitals(self, profile: Dict) -> bool:
        """Update vital signs for a patient."""
        vitals = self.generate_vitals(profile)
        
        try:
            response = self.session.put(
                f"{self.base_url}/patients/{profile['id']}/vitals",
                json=vitals,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"   ❌ Error updating vitals for {profile['id']}: {e}")
            return False
    
    def populate(self, history_minutes: int = 60, interval_minutes: int = 5):
        """
        Populate the database with patients and their vital signs history.
        
        Args:
            history_minutes: How many minutes of history to create
            interval_minutes: Interval between vital signs readings
        """
        print("🏥 VERIQ Database Population Script")
        print("=" * 60)
        
        # Health check
        print("\n1. Checking API health...")
        if not self.health_check():
            print("❌ Cannot connect to API. Make sure the backend server is running:")
            print("   cd backend && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
            return False
        print("✅ API is healthy")
        
        # Calculate timestamps
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=history_minutes)
        num_readings = history_minutes // interval_minutes
        
        print(f"\n2. Registering {len(self.patient_profiles)} patients...")
        print(f"   Creating {num_readings} vital signs readings per patient")
        print(f"   Time range: {start_time.strftime('%H:%M')} to {now.strftime('%H:%M')}")
        
        # Register all patients with initial vitals
        for profile in self.patient_profiles:
            initial_time = start_time + timedelta(minutes=random.randint(0, 30))
            if self.register_patient(profile, initial_time):
                risk_emoji = "🚨" if profile["deterioration_risk"] == "High" else "⚠️" if profile["deterioration_risk"] == "Medium" else "✅"
                print(f"   {risk_emoji} Registered {profile['id']} ({profile['deterioration_risk']} risk)")
        
        # Add historical vital signs updates
        print(f"\n3. Adding vital signs history ({interval_minutes}-minute intervals)...")
        
        for i in range(1, num_readings):
            current_time = start_time + timedelta(minutes=i * interval_minutes)
            time_str = current_time.strftime('%H:%M')
            
            updates_success = 0
            for profile in self.patient_profiles:
                if self.update_vitals(profile):
                    updates_success += 1
            
            print(f"   📊 {time_str} - Updated {updates_success}/{len(self.patient_profiles)} patients")
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 Database population complete!")
        print(f"   Total patients: {len(self.patient_profiles)}")
        print(f"   Vital signs readings per patient: {num_readings}")
        print(f"   Total records created: ~{len(self.patient_profiles) * num_readings}")
        
        # Print patient summary
        print("\n📋 Patient Summary:")
        print("-" * 60)
        print(f"{'ID':<8} {'Risk':<10} {'Severity':<12} {'Arrival':<12}")
        print("-" * 60)
        for profile in self.patient_profiles:
            print(f"{profile['id']:<8} {profile['deterioration_risk']:<10} {profile['severity']:<12} {profile['arrival_mode']:<12}")
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Populate VERIQ database with realistic patient data"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--history",
        type=int,
        default=60,
        help="Minutes of history to create (default: 60)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Interval between readings in minutes (default: 5)"
    )
    
    args = parser.parse_args()
    
    populator = DatabasePopulator(args.base_url)
    success = populator.populate(
        history_minutes=args.history,
        interval_minutes=args.interval
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()