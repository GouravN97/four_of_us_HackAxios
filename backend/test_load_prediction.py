"""
Test script to verify Load Prediction integration works correctly.
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ML_models', 'Load_prediction'))

import pandas as pd
from datetime import datetime, timedelta

def test_load_prediction():
    """Test the load prediction integration"""
    print("=" * 60)
    print("LOAD PREDICTION INTEGRATION TEST")
    print("=" * 60)
    
    # Import from ML_models
    from predictor import load_model, predict_next_6_hours
    
    # Load model
    model_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'ML_models', 'Load_prediction', 'er_load_model_enhanced.pkl'
    )
    
    print(f"\n1. Loading model from: {model_path}")
    model_data = load_model(model_path)
    print(f"   ✅ Model loaded successfully")
    print(f"   Model type: {model_data.get('model_type', 'unknown')}")
    print(f"   Features: {model_data['feature_cols']}")
    
    # Create sample recent data (last 3 hours)
    print("\n2. Creating sample ICU data (last 3 hours)...")
    now = datetime.now()
    sample_data = pd.DataFrame([
        {'timestamp': now - timedelta(hours=3), 'count': 5},
        {'timestamp': now - timedelta(hours=2), 'count': 7},
        {'timestamp': now - timedelta(hours=1), 'count': 6},
    ])
    print(sample_data.to_string(index=False))
    
    # Predict next 6 hours
    print("\n3. Predicting next 6 hours...")
    predictions = predict_next_6_hours(sample_data, model_data, '90%')
    
    print("\n4. Results Summary:")
    print("-" * 50)
    total = sum(p['predicted_arrivals'] for p in predictions)
    peak = max(predictions, key=lambda x: x['predicted_arrivals'])
    
    print(f"   Total expected arrivals: {total} patients")
    print(f"   Peak hour: {peak['timestamp'].strftime('%I:%M %p')} ({peak['predicted_arrivals']} patients)")
    
    print("\n" + "=" * 60)
    print("✅ LOAD PREDICTION INTEGRATION TEST PASSED!")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    test_load_prediction()
