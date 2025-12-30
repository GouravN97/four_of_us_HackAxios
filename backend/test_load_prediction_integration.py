#!/usr/bin/env python3
"""
Test script for Load Prediction API integration
Run this to verify everything works before pushing to your branch
"""

import requests
import json
from datetime import datetime, timedelta

def test_load_prediction_api():
    """Test the load prediction API endpoints"""
    
    base_url = "http://localhost:5001"
    
    print("🧪 Testing Load Prediction API Integration")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/api/load-prediction/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check: {data['status']}")
            print(f"   Model Loaded: {data['model_loaded']}")
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        print("   Make sure the API is running: python src/load_prediction_api.py")
        return False
    
    # Test 2: Sample Data
    print("\n2️⃣ Getting Sample Data...")
    try:
        response = requests.get(f"{base_url}/api/load-prediction/sample-data")
        if response.status_code == 200:
            sample_data = response.json()
            print(f"✅ Sample Data Retrieved: {len(sample_data['recent_data'])} hours")
            recent_data = sample_data['recent_data']
        else:
            print(f"❌ Sample Data Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sample Data Error: {e}")
        return False
    
    # Test 3: Basic Forecast
    print("\n3️⃣ Testing Basic Forecast...")
    try:
        payload = {
            "recent_data": recent_data,
            "confidence_level": "90%"
        }
        
        response = requests.post(
            f"{base_url}/api/load-prediction/forecast",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            forecast = response.json()
            print(f"✅ Forecast Generated: {len(forecast['forecast_data'])} hours")
            print(f"   Total Predicted: {forecast['summary']['total_predicted']} patients")
            print(f"   Peak Hour: {forecast['summary']['peak_hour']}")
            
            # Show first prediction for verification
            first_pred = forecast['forecast_data'][0]
            print(f"   Hour 1: {first_pred['time_label']} → {first_pred['predicted_arrivals']} patients")
            
        else:
            print(f"❌ Forecast Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Forecast Error: {e}")
        return False
    
    # Test 4: Frontend Data Format
    print("\n4️⃣ Verifying Frontend Data Format...")
    try:
        # Check if data is ready for graphing
        graph_data = []
        for hour_data in forecast['forecast_data']:
            graph_data.append({
                'x': hour_data['time_label'],
                'y': hour_data['predicted_arrivals'],
                'lower': hour_data['lower_bound'],
                'upper': hour_data['upper_bound']
            })
        
        print(f"✅ Graph Data Ready: {len(graph_data)} points")
        print(f"   Sample Point: {graph_data[0]}")
        
    except Exception as e:
        print(f"❌ Data Format Error: {e}")
        return False
    
    print("\n🎉 All Tests Passed!")
    print("\nNext Steps:")
    print("1. Your API is ready for frontend integration")
    print("2. Use the forecast_data array to plot your 6-hour graph")
    print("3. Each point has predicted_arrivals, lower_bound, upper_bound")
    print("4. Commit and push your changes to the backend-api-integration branch")
    
    return True

if __name__ == "__main__":
    success = test_load_prediction_api()
    if not success:
        print("\n⚠️  Some tests failed. Check the API setup and try again.")
        exit(1)