from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import os
import sys

# Add ML_models to path to import the predictor modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ML_models/Load_prediction'))

from predictor import load_model, predict_next_6_hours
from llm_explainer import explain_6_hour_forecast

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Global variables to store model
model_data = None
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')  # Set this in your environment

def initialize_load_prediction_model():
    """Load the load prediction model on startup"""
    global model_data
    try:
        # Path to the model in ML_models folder
        model_path = os.path.join(
            os.path.dirname(__file__), 
            '../../ML_models/Load_prediction/er_load_model_enhanced.pkl'
        )
        model_data = load_model(model_path)
        print("✅ Load Prediction Model loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error loading load prediction model: {e}")
        model_data = None
        return False

@app.route('/api/load-prediction/health', methods=['GET'])
def load_prediction_health():
    """Health check endpoint for load prediction service"""
    return jsonify({
        "service": "load_prediction",
        "status": "healthy",
        "model_loaded": model_data is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/load-prediction/forecast', methods=['POST'])
def forecast_icu_load():
    """
    Predict ICU occupancy for next 6 hours
    
    Expected JSON payload:
    {
        "recent_data": [
            {"timestamp": "2024-01-01T10:00:00", "count": 5},
            {"timestamp": "2024-01-01T11:00:00", "count": 7},
            {"timestamp": "2024-01-01T12:00:00", "count": 6}
        ],
        "confidence_level": "90%"  // optional, defaults to "90%"
    }
    """
    try:
        if model_data is None:
            return jsonify({
                "error": "Load prediction model not loaded",
                "service": "load_prediction"
            }), 500
        
        data = request.get_json()
        
        if not data or 'recent_data' not in data:
            return jsonify({
                "error": "Missing 'recent_data' in request",
                "service": "load_prediction"
            }), 400
        
        # Convert to DataFrame
        recent_data = pd.DataFrame(data['recent_data'])
        recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp'])
        
        # Validate data
        if len(recent_data) < 3:
            return jsonify({
                "error": "Need at least 3 hours of recent data",
                "service": "load_prediction"
            }), 400
        
        confidence_level = data.get('confidence_level', '90%')
        
        # Make predictions
        predictions = predict_next_6_hours(recent_data, model_data, confidence_level)
        
        # Format response for frontend graphing
        formatted_predictions = []
        for i, pred in enumerate(predictions, 1):
            formatted_predictions.append({
                "hour": i,
                "timestamp": pred["timestamp"].isoformat(),
                "time_label": pred["timestamp"].strftime("%I:%M %p"),
                "predicted_arrivals": pred["predicted_arrivals"],
                "lower_bound": pred["lower_bound"],
                "upper_bound": pred["upper_bound"],
                "confidence_level": pred["confidence_level"],
                "confidence_interval": pred["confidence_interval"],
                "expected_error": pred["expected_error"]
            })
        
        return jsonify({
            "success": True,
            "service": "load_prediction",
            "forecast_data": formatted_predictions,
            "summary": {
                "total_predicted": sum(p["predicted_arrivals"] for p in predictions),
                "peak_hour": max(predictions, key=lambda x: x["predicted_arrivals"])["timestamp"].strftime("%I:%M %p"),
                "peak_count": max(p["predicted_arrivals"] for p in predictions)
            },
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "load_prediction"
        }), 500

@app.route('/api/load-prediction/forecast-with-insights', methods=['POST'])
def forecast_with_ai_insights():
    """
    Predict ICU occupancy for next 6 hours with AI-generated insights
    Requires GROQ_API_KEY environment variable
    """
    try:
        if model_data is None:
            return jsonify({
                "error": "Load prediction model not loaded",
                "service": "load_prediction"
            }), 500
        
        if not GROQ_API_KEY:
            return jsonify({
                "error": "GROQ_API_KEY not configured for AI insights",
                "service": "load_prediction"
            }), 500
        
        data = request.get_json()
        
        if not data or 'recent_data' not in data:
            return jsonify({
                "error": "Missing 'recent_data' in request",
                "service": "load_prediction"
            }), 400
        
        # Convert to DataFrame
        recent_data = pd.DataFrame(data['recent_data'])
        recent_data['timestamp'] = pd.to_datetime(recent_data['timestamp'])
        
        # Validate data
        if len(recent_data) < 3:
            return jsonify({
                "error": "Need at least 3 hours of recent data",
                "service": "load_prediction"
            }), 400
        
        confidence_level = data.get('confidence_level', '90%')
        
        # Make predictions
        predictions = predict_next_6_hours(recent_data, model_data, confidence_level)
        
        # Get AI insights
        explanation_data = explain_6_hour_forecast(predictions, GROQ_API_KEY)
        
        # Format response for frontend
        formatted_predictions = []
        for i, pred in enumerate(predictions, 1):
            formatted_predictions.append({
                "hour": i,
                "timestamp": pred["timestamp"].isoformat(),
                "time_label": pred["timestamp"].strftime("%I:%M %p"),
                "predicted_arrivals": pred["predicted_arrivals"],
                "lower_bound": pred["lower_bound"],
                "upper_bound": pred["upper_bound"],
                "confidence_level": pred["confidence_level"],
                "confidence_interval": pred["confidence_interval"],
                "expected_error": pred["expected_error"]
            })
        
        return jsonify({
            "success": True,
            "service": "load_prediction",
            "forecast_data": formatted_predictions,
            "ai_insights": {
                "explanation": explanation_data["overall_explanation"],
                "summary": {
                    "total_expected": explanation_data["total_expected"],
                    "peak_hour": explanation_data["peak_hour"].strftime("%I:%M %p"),
                    "peak_count": explanation_data["peak_count"]
                }
            },
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "load_prediction"
        }), 500

@app.route('/api/load-prediction/sample-data', methods=['GET'])
def get_sample_icu_data():
    """
    Generate sample ICU occupancy data for testing
    """
    try:
        # Generate sample recent data (last 3 hours)
        now = datetime.now()
        sample_data = []
        
        for i in range(3, 0, -1):
            timestamp = now - timedelta(hours=i)
            # Generate realistic sample count based on hour
            hour = timestamp.hour
            if 8 <= hour <= 18:  # Day shift
                count = np.random.randint(4, 8)
            elif 19 <= hour <= 23:  # Evening
                count = np.random.randint(6, 10)
            else:  # Night
                count = np.random.randint(2, 5)
            
            sample_data.append({
                "timestamp": timestamp.isoformat(),
                "count": count
            })
        
        return jsonify({
            "service": "load_prediction",
            "recent_data": sample_data,
            "note": "This is sample data for testing. Replace with real ICU occupancy data."
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "load_prediction"
        }), 500

# Initialize model when module is imported
if __name__ == '__main__':
    initialize_load_prediction_model()
    app.run(debug=True, host='0.0.0.0', port=5001)  # Different port to avoid conflicts