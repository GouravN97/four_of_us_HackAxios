# 🏥 VERIQ  
## AI-Powered Hospital Operations & Decision Support System

VERIQ is an intelligent hospital management platform designed to **predict, prioritize, and explain** critical care decisions in **Emergency Rooms (ER)** and **Intensive Care Units (ICU)**.

Instead of reacting to overload, VERIQ enables hospitals to **anticipate patient deterioration, forecast ICU demand, and act early** using real-time data and machine learning.

---

## 🚨 Problem Statement

Hospitals face persistent operational challenges:

- Delayed triage due to manual assessment  
- Poor short-term visibility into ICU capacity  
- Inefficient patient prioritization during peak load  
- Reactive decision-making instead of proactive planning  
- Lack of explainability in AI-assisted decisions  

These issues directly impact patient outcomes and staff efficiency.

---

## 💡 Solution Overview

VERIQ addresses these gaps by providing:

- ML-based **patient deterioration risk prediction**
- Real-time **ER patient prioritization**
- **6-hour ICU bed occupancy forecasting**
- **Explainable AI** for clinical trust
- Data-driven **ICU admission and resource recommendations**

The system is designed to degrade gracefully if ML services are unavailable.

---

## 🎯 Target Users

- ER nurses and physicians  
- ICU administrators  
- Hospital operations teams  
- Healthcare systems handling high patient volumes  

---

## ✨ Core Features

### Patient Risk Assessment
- ML-powered deterioration prediction  
- Risk levels: **HIGH / MODERATE / LOW**  
- Confidence scores (75–95%)  
- Explainable AI highlighting contributing vitals  

### ER Patient Prioritization
- Dynamic priority queue  
- Sorting by severity and wait time  
- Patient-level drill-down with explanations  

### ICU Capacity Management
- Real-time bed occupancy tracking  
- Status indicators: NORMAL / WATCH / CRITICAL  
- ICU patient list with risk levels  

### ICU Load Forecasting
- 6-hour ahead predictions  
- Confidence intervals  
- Peak-load detection  
- AI-generated explanations  

### Vital Signs Logging
- Time-series vitals (5-minute intervals)  
- Patient-level history  
- Validated data entry  

### Medical Validation
- Healthcare-compliant ranges  
- Business rules (e.g., systolic > diastolic BP)  
- Duplicate and anomaly detection  

---

## 🧱 System Architecture

### Backend (Layered Architecture)

API Layer (FastAPI)
│
├── Business Logic Layer
│ ├── Patient Service
│ ├── Vital Signs Service
│ └── Risk Assessment Service
│
├── Data Access Layer
│ ├── Patient Repository
│ └── Vital Signs Repository
│
└── Database (SQLAlchemy ORM)
├── Patient
├── VitalSigns (time-series)
└── RiskAssessment

### Frontend Flow

Login
↓
Dashboard
├─ ER View (Prioritization)
├─ ICU View (Capacity & Forecast)
└─ Patient Logs
└─ Add / Update Vitals


---

## 🛠️ Tech Stack

### Frontend
- React 19  
- React Router  
- Recharts  
- Vite  
- Custom CSS  
- Figma (UI/UX design)  

### Backend
- Python 3.8+  
- FastAPI  
- Uvicorn  
- SQLAlchemy  
- PostgreSQL / SQLite  
- Pydantic  

### Machine Learning
- Scikit-learn  
- Time-series forecasting models  
- Joblib  
- Optional GROQ API integration  

### Dev & Testing
- Git & GitHub  
- pytest  
- Property-based testing  

---

## 🚀 Installation & Setup

### Clone Repository
```bash
git clone https://github.com/GouravN97/four_of_us_HackAxios
cd four_of_us_HackAxios
Frontend
bash
npm install
npm run dev
Backend
bash
cd backend
pip install -r requirements.txt
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Optional: Populate Database
bash
###
python .\populate_db_direct.py

🔐 Demo Credentials
yaml
Username: H123
First Name: Harsh
Last Name: Mishra
Email: h123@gmail.com
Password: orange@123
🌐 Deployment
Live Application: [Deployed link coming soon]

Demo Video: [Demo video link coming soon]

🏁 Hackathon Context
Event: HackAxios

Theme: Healthcare / Hospital Management

Track: AI/ML for Healthcare Operations

Highlights:

Real-time ML integration

Explainable AI

Predictive analytics

🔮 Future Roadmap
Sepsis early warning system

Multi-organ failure prediction

EMR/EHR integration (FHIR, HL7)

Advanced resource and staff optimization

Native mobile applications

📎 Repository
https://github.com/GouravN97/four_of_us_HackAxios

