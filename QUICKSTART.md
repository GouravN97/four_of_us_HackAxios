# VERIQ Hospital Management System - Quick Start Guide

This guide will help you get the complete system running with real data from the backend API.

## Prerequisites

1. **Python 3.8+** - For the backend server
2. **Node.js 18+** - For the frontend (optional, for development)

## Step 1: Start the Backend Server

Open a terminal and run:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

You should see:
```
🏥 Patient Risk Classifier Backend starting up...
✅ Application startup complete
```

## Step 2: Populate the Database

Open a **new terminal** and run:

```bash
cd backend
python populate_database.py
```

This will:
- Register 10 patients with different risk profiles
- Create 60 minutes of vital signs history (5-minute intervals)
- Generate realistic medical data for testing

Expected output:
```
🏥 VERIQ Database Population Script
============================================================

1. Checking API health...
✅ API is healthy

2. Registering 10 patients...
   🚨 Registered P001 (High risk)
   🚨 Registered P002 (High risk)
   ...

3. Adding vital signs history...
   📊 09:00 - Updated 10/10 patients
   📊 09:05 - Updated 10/10 patients
   ...

🎉 Database population complete!
```

## Step 3: Start the Frontend (Development)

Open a **new terminal** and run:

```bash
npm install
npm run dev
```

The app will start at `http://localhost:5173`

## Step 4: Login and Explore

Use these credentials:
- **Hospital ID**: H123
- **First Name**: Harsh
- **Last Name**: Mishra
- **Admin Email**: h123@gmail.com
- **Password**: orange@123

## Features Now Connected to Backend

### Patient Log (Frame4)
- Displays real patient vital signs from the database
- Shows 5-minute interval readings
- Search by Patient ID
- Add new patients (registers via API)

### Patient Prioritization (Frame2_1)
- Real-time risk assessment from ML model
- Deterioration risk levels (High/Medium/Low)
- Confidence scores from the ML model
- Explainability showing which vitals triggered the risk

### ICU Recommendations (Frame3)
- Dynamic recommendations based on patient risk scores
- Urgency levels derived from ML risk assessment
- Reasons generated from actual vital signs

## API Endpoints Used

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /patients` | Register new patient |
| `GET /patients/{id}` | Get patient status |
| `PUT /patients/{id}/vitals` | Update vital signs |
| `GET /patients/{id}/history` | Get vital signs history |
| `GET /patients/high-risk` | Get high-risk patients |

## Testing the CLI

You can also test the backend directly:

```bash
cd backend
python cli_test.py demo
```

## Troubleshooting

### "Cannot connect to API"
- Make sure the backend server is running on port 8000
- Check if another process is using port 8000

### "No patient data found"
- Run `python populate_database.py` to add sample data

### Frontend shows loading forever
- Check browser console for CORS errors
- Ensure backend is running at `http://localhost:8000`

### CORS Issues
The backend has CORS enabled for all origins in development mode.
If you still have issues, check the browser console.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│   FastAPI       │────▶│   SQLite DB     │
│   (Frontend)    │     │   (Backend)     │     │   + ML Model    │
│   Port 5173     │     │   Port 8000     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Patient Risk Profiles

The database is populated with diverse patient profiles:

| Patient | Risk Level | Condition |
|---------|------------|-----------|
| P001 | High | Cardiac issues |
| P002 | High | Respiratory distress |
| P003 | High | Stroke symptoms |
| P004 | Medium | Fever |
| P005 | Medium | Abdominal pain |
| P006 | High | Diabetic emergency |
| P007 | Low | Minor injury |
| P008 | Low | Routine checkup |
| P009 | Medium | Back pain |
| P010 | High | Allergic reaction |

## Next Steps

1. **Customize patient data**: Modify `populate_database.py` to add more patients
2. **Adjust risk thresholds**: Edit the frontend components to change risk categorization
3. **Add more features**: Extend the API service in `src/services/api.js`
4. **Production deployment**: Configure proper CORS and authentication