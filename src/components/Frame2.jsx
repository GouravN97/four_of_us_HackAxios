import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { useSimulation } from '../contexts/SimulationContext';
import Frame2_1 from './Frame2_1';
import './Frame2.css';
import { getAllPatients, getPatientStatus } from '../services/api';

const getYAxisMax = (data, key = 'value') => {
  if (!data || data.length === 0) return 10;
  const maxValue = Math.max(...data.map(d => d[key] || 0));
  if (maxValue <= 5) return Math.max(5, maxValue + 2);
  if (maxValue <= 10) return Math.ceil(maxValue * 1.3);
  if (maxValue <= 20) return Math.ceil(maxValue / 5) * 5 + 5;
  return Math.ceil(maxValue / 10) * 10 + 10;
};

const Frame2 = () => {
  const navigate = useNavigate();
  const { isRunning, simulatedTime, startSimulation, tickCount, formatSimTime, generateTimeLabels } = useSimulation();
  const [showPrioritization, setShowPrioritization] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [erInflowRate, setErInflowRate] = useState(0);
  const [avgWaitTime, setAvgWaitTime] = useState(0);
  const [patientsExceedingThreshold, setPatientsExceedingThreshold] = useState(0);
  const [forecastData, setForecastData] = useState([]);
  const [arrivalData, setArrivalData] = useState([]);

  useEffect(() => {
    const initSimulation = async () => {
      if (!isRunning) {
        try { await startSimulation(); } catch (err) { console.warn('Could not auto-start simulation:', err); }
      }
    };
    initSimulation();
  }, []);

  const fetchERData = useCallback(async () => {
    if (!simulatedTime) return;
    
    try {
      setLoading(true);
      const allPatientsResponse = await getAllPatients();
      const patientIds = allPatientsResponse.patient_ids || [];
      
      const waitThreshold = 40;
      let totalWaitTime = 0;
      let exceedingThreshold = 0;
      
      for (const patientId of patientIds) {
        try {
          const status = await getPatientStatus(patientId);
          const registrationTime = new Date(status.registration_time);
          const waitTimeMinutes = Math.round((simulatedTime - registrationTime) / (1000 * 60));
          
          totalWaitTime += Math.min(waitTimeMinutes, 120);
          
          if (waitTimeMinutes > waitThreshold) {
            exceedingThreshold++;
          }
        } catch (err) {}
      }
      
      // Use patient count as inflow rate approximation
      setErInflowRate(patientIds.length);
      setAvgWaitTime(patientIds.length > 0 ? Math.round(totalWaitTime / patientIds.length) : 0);
      setPatientsExceedingThreshold(exceedingThreshold);
      
      // Generate arrival distribution data (past 2 hours, 10-min intervals)
      const pastLabels = generateTimeLabels(10, 12, 'past');
      const arrivalDistribution = pastLabels.map((label) => ({
        time: label.time,
        value: Math.max(0, Math.floor(Math.random() * 4) + 1)
      }));
      setArrivalData(arrivalDistribution);
      
      // Generate forecast data (next 60 mins)
      const futureLabels = generateTimeLabels(5, 12, 'future');
      const forecast = futureLabels.map(label => ({
        time: label.time,
        value: Math.max(0, Math.floor(Math.random() * 4) + 1)
      }));
      setForecastData(forecast);
      
    } catch (error) {
      console.error('Failed to fetch ER data:', error);
    } finally {
      setLoading(false);
    }
  }, [simulatedTime, generateTimeLabels, tickCount]);

  useEffect(() => { fetchERData(); }, [tickCount, fetchERData]);

  const handleLogout = () => navigate('/');
  const handleOverview = () => navigate('/dashboard');
  const handleICU = () => navigate('/icu');
  const handlePatientLog = () => navigate('/patient-log');

  return (
    <div className="frame2">
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item" onClick={handleOverview}><img src="/assets/images/treatment-dark-icon.png" alt="Overview" className="menu-icon" /><span>Overview</span></div>
          <div className="menu-item active"><img src="/assets/images/er-hospital-icon.png" alt="ER" className="menu-icon" /><span>ER</span></div>
          <div className="menu-item" onClick={handleICU}><img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" /><span>ICU</span></div>
          <div className="menu-item" onClick={handlePatientLog}><img src="/assets/images/people-icon.png" alt="Patient Log" className="menu-icon" /><span>Patient Log</span></div>
        </div>
      </div>

      <div className="header">
        <div className="header-left"><img src="/assets/images/logo.png" alt="Logo" className="header-logo" /><span className="header-brand">VERIQ</span></div>
        <div className="header-center"><span className="sim-time">{isRunning ? `🕐 ${formatSimTime('datetime')}` : 'Starting...'}</span></div>
        <div className="header-right"><span className="logout-text" onClick={handleLogout}>Logout</span><img src="/assets/images/logout-icon.png" alt="Logout" className="logout-icon" onClick={handleLogout} /></div>
      </div>

      <div className="main-content">
        <h2 className="section-title">Operational Metrics</h2>
        <div className="metrics-row">
          <div className="metric-card"><span className="metric-label">Current ER inflow rate</span><span className="metric-value">{loading ? '...' : `${erInflowRate} per 30 minutes`}</span></div>
          <div className="metric-card"><span className="metric-label">Average waiting time</span><span className="metric-value">{loading ? '...' : `${avgWaitTime} minutes`}</span></div>
        </div>
        <div className="metrics-row center">
          <div className="metric-card metric-card-tall"><span className="metric-label">Patients exceeding wait threshold</span><span className="metric-value-large">{loading ? '...' : patientsExceedingThreshold}</span><span className="metric-note">Wait threshold: 40 minutes</span></div>
        </div>

        <h2 className="section-title">Trends</h2>
        <div className="chart-card-wide">
          <div className="chart-title">FORECAST ER inflow for next 60 minutes</div>
          <ResponsiveContainer width="100%" height={140}><LineChart data={forecastData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(forecastData)]} tick={{ fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={true} name="Predicted Arrivals" /></LineChart></ResponsiveContainer>
        </div>

        <div className="chart-card-wide">
          <div className="chart-title">Patient arrivals in the past 2 hours</div>
          <ResponsiveContainer width="100%" height={140}><LineChart data={arrivalData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(arrivalData)]} tick={{ fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={true} name="Arrivals" /></LineChart></ResponsiveContainer>
        </div>

        <button className="prioritization-btn" onClick={() => setShowPrioritization(true)}>View patient prioritization</button>
      </div>

      {showPrioritization && <Frame2_1 onClose={() => setShowPrioritization(false)} />}
    </div>
  );
};

export default Frame2;
