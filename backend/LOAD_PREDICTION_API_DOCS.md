# Load Prediction API Documentation

This API provides ICU occupancy forecasting for the next 6 hours using machine learning.

## Setup

1. Install additional dependencies:
```bash
pip install -r load_prediction_requirements.txt
```

2. (Optional) Set up Groq API key for AI insights:
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

3. Run the load prediction service:
```bash
python src/load_prediction_api.py
```

The service will be available at `http://localhost:5001`

## API Endpoints

### 1. Health Check
```
GET /api/load-prediction/health
```

**Response:**
```json
{
    "service": "load_prediction",
    "status": "healthy",
    "model_loaded": true,
    "timestamp": "2024-01-01T12:30:00"
}
```

### 2. ICU Load Forecast (Basic)
```
POST /api/load-prediction/forecast
```

**Request Body:**
```json
{
    "recent_data": [
        {"timestamp": "2024-01-01T10:00:00", "count": 5},
        {"timestamp": "2024-01-01T11:00:00", "count": 7},
        {"timestamp": "2024-01-01T12:00:00", "count": 6}
    ],
    "confidence_level": "90%"
}
```

**Response (Perfect for Frontend Graphing):**
```json
{
    "success": true,
    "service": "load_prediction",
    "forecast_data": [
        {
            "hour": 1,
            "timestamp": "2024-01-01T13:00:00",
            "time_label": "01:00 PM",
            "predicted_arrivals": 8,
            "lower_bound": 6,
            "upper_bound": 10,
            "confidence_level": "high",
            "confidence_interval": "90%",
            "expected_error": 1.2
        }
        // ... 5 more hours
    ],
    "summary": {
        "total_predicted": 42,
        "peak_hour": "03:00 PM",
        "peak_count": 12
    },
    "generated_at": "2024-01-01T12:30:00"
}
```

### 3. ICU Load Forecast with AI Insights
```
POST /api/load-prediction/forecast-with-insights
```

Same request format as basic forecast, but includes AI-generated explanations.

**Additional Response Fields:**
```json
{
    // ... same as basic forecast
    "ai_insights": {
        "explanation": "FORECAST: Moderate increase expected during evening rush hours...",
        "summary": {
            "total_expected": 42,
            "peak_hour": "03:00 PM",
            "peak_count": 12
        }
    }
}
```

### 4. Sample Data for Testing
```
GET /api/load-prediction/sample-data
```

Returns sample ICU occupancy data for testing the API.

## Frontend Integration Example

```javascript
// Fetch 6-hour ICU load forecast
const fetchICUForecast = async (recentData) => {
    try {
        const response = await fetch('http://localhost:5001/api/load-prediction/forecast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                recent_data: recentData,
                confidence_level: "90%"
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // data.forecast_data contains 6 hourly predictions
            // Perfect for plotting on your graph!
            return data.forecast_data.map(hour => ({
                x: hour.time_label,
                y: hour.predicted_arrivals,
                lower: hour.lower_bound,
                upper: hour.upper_bound
            }));
        }
    } catch (error) {
        console.error('Forecast error:', error);
    }
};

// Example usage
const recentICUData = [
    {timestamp: "2024-01-01T10:00:00", count: 5},
    {timestamp: "2024-01-01T11:00:00", count: 7},
    {timestamp: "2024-01-01T12:00:00", count: 6}
];

const forecastData = await fetchICUForecast(recentICUData);
// Use forecastData to plot your 6-hour graph
```

## Integration with Existing Backend

This API is designed to work alongside your existing backend:

1. **Different Port**: Runs on port 5001 (not 5000)
2. **Unique Endpoints**: All endpoints prefixed with `/api/load-prediction/`
3. **Separate Files**: No conflicts with existing code
4. **Independent Service**: Can be deployed separately if needed

## Notes

- Requires at least 3 hours of recent ICU occupancy data
- Returns exactly 6 hourly predictions for your graph
- Each prediction includes confidence bounds for uncertainty visualization
- CORS enabled for frontend integration
- Service identifier in all responses for debugging