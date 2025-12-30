# Quick Start: ICU Load Prediction API

## 🚀 Get Your API Running in 3 Steps

### Step 1: Install Dependencies
```bash
cd backend
pip install -r load_prediction_requirements.txt
```

### Step 2: Start the API
```bash
python src/load_prediction_api.py
```

You should see:
```
✅ Load Prediction Model loaded successfully
* Running on http://0.0.0.0:5001
```

### Step 3: Test It Works
```bash
python test_load_prediction_integration.py
```

## 🎯 Frontend Integration

Your API provides exactly what you need for the 6-hour graph:

```javascript
// Fetch forecast data for your graph
const response = await fetch('http://localhost:5001/api/load-prediction/forecast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        recent_data: [
            {timestamp: "2024-01-01T10:00:00", count: 5},
            {timestamp: "2024-01-01T11:00:00", count: 7}, 
            {timestamp: "2024-01-01T12:00:00", count: 6}
        ]
    })
});

const data = await response.json();

// data.forecast_data contains 6 hourly predictions perfect for graphing:
// [
//   {hour: 1, time_label: "01:00 PM", predicted_arrivals: 8, lower_bound: 6, upper_bound: 10},
//   {hour: 2, time_label: "02:00 PM", predicted_arrivals: 7, lower_bound: 5, upper_bound: 9},
//   ... 4 more hours
// ]
```

## 📊 What You Get

- **6 hourly predictions** - perfect for your graph
- **Confidence bounds** - show uncertainty ranges  
- **Time labels** - ready for x-axis
- **Peak hour detection** - highlight rush periods
- **AI explanations** - optional insights (needs GROQ_API_KEY)

## 🔧 Troubleshooting

**Model not loading?**
- Check that `ML_models/Load_prediction/er_load_model_enhanced.pkl` exists
- Make sure you're in the right directory

**Port conflicts?**
- API runs on port 5001 (not 5000) to avoid conflicts

**Need AI insights?**
- Set `GROQ_API_KEY` environment variable
- Use `/api/load-prediction/forecast-with-insights` endpoint

## ✅ You're Ready!

Your backend is now ready to provide 6-hour ICU load forecasts to your frontend. The data format is optimized for graphing and includes all the confidence intervals you need.