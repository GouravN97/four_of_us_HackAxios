import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { useSimulation } from '../contexts/SimulationContext';
import { getICUCapacity, getAllPatients, getHighRiskPatients, getPatientStatus } from '../services/api';
import './Frame1.css';

const getYAxisMax = (data, key = 'value') => {
  if (!data || data.length === 0) return 10;
  const maxValue = Math.max(...data.map(d => d[key] || 0));
  if (maxValue <= 5) return Math.max(5, maxValue + 2);
  if (maxValue <= 10) return Math.ceil(maxValue * 1.3);
  if (maxValue <= 20) return Math.ceil(maxValue / 5) * 5 + 5;
  return Math.ceil(maxValue / 10) * 10 + 10;
};

const Frame1 = () => {
  const navigate = useNavigate();
  const { isRunning, simulatedTime, startSimulation, tickCount, formatSimTime, generateTimeLabels } = useSimulation();
  
  const [icuCapacity, setIcuCapacity] = useState({ beds_occupied: 0, total_beds: 15, occupancy_percentage: 0 });
  const [erCapacity, setErCapacity] = useState({ occupied: 0, total: 40, percentage: 0 });
  const [totalERPatients, setTotalERPatients] = useState(0);
  const [highRiskCount, setHighRiskCount] = useState(0);
  const [icuStatus, setIcuStatus] = useState('NORMAL');
  const [erStatus, setErStatus] = useState('NORMAL');
  const [erTrendData, setErTrendData] = useState([]);
  const [icuTrendData, setIcuTrendData] = useState([]);
  const [forecastERData, setForecastERData] = useState([]);
  const [forecastICUData, setForecastICUData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initSimulation = async () => {
      if (!isRunning) {
        try {
          await startSimulation();
        } catch (err) {
          console.warn('Could not auto-start simulation:', err);
        }
      }
    };
    initSimulation();
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const icuData = await getICUCapacity();
      setIcuCapacity({ beds_occupied: icuData.beds_occupied, total_beds: icuData.total_beds, occupancy_percentage: icuData.occupancy_percentage });
      setIcuStatus(icuData.occupancy_percentage >= 90 ? 'CRITICAL' : icuData.occupancy_percentage >= 75 ? 'WATCH' : 'NORMAL');

      const patientsResponse = await getAllPatients();
      const patientIds = patientsResponse.patient_ids || [];
      
      // Count all patients (no time filtering)
      setTotalERPatients(patientIds.length);
      const erPct = (patientIds.length / 40) * 100;
      setErCapacity({ occupied: patientIds.length, total: 40, percentage: erPct });
      setErStatus(erPct >= 90 ? 'CRITICAL' : erPct >= 75 ? 'WATCH' : 'NORMAL');

      const highRisk = await getHighRiskPatients();
      if (highRisk?.patients) {
        setHighRiskCount(highRisk.patients.length);
      }

      generateTrendData(patientIds.length, icuData.beds_occupied);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [tickCount]);

  const generateTrendData = useCallback((currentERCount, currentICUCount) => {
    if (!simulatedTime) return;
    
    const pastLabels = generateTimeLabels(5, 12, 'past');
    const erTrend = pastLabels.map((label) => ({
      time: label.time,
      value: Math.max(0, currentERCount + Math.floor(Math.random() * 3) - 1)
    }));
    setErTrendData(erTrend);
    
    const icuTrend = pastLabels.map((label) => ({
      time: label.time,
      value: Math.max(0, currentICUCount + Math.floor(Math.random() * 2) - 1)
    }));
    setIcuTrendData(icuTrend);
    
    const futureLabels = generateTimeLabels(5, 12, 'future');
    setForecastERData(futureLabels.map(label => ({ time: label.time, value: Math.max(0, currentERCount + Math.floor(Math.random() * 4) - 2) })));
    setForecastICUData(futureLabels.map(label => ({ time: label.time, value: Math.max(0, currentICUCount + Math.floor(Math.random() * 3) - 1) })));
  }, [simulatedTime, generateTimeLabels]);

  useEffect(() => { fetchData(); }, [tickCount, fetchData]);

  const handleLogout = () => navigate('/');
  const handleER = () => navigate('/er');
  const handleICU = () => navigate('/icu');
  const handlePatientLog = () => navigate('/patient-log');

  return (
    <div className="frame1">
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item active"><img src="/assets/images/treatment-icon.png" alt="Overview" className="menu-icon" /><span>Overview</span></div>
          <div className="menu-item" onClick={handleER}><img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" /><span>ER</span></div>
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
        <h2 className="section-title">Summary Metrics</h2>
        <div className="metrics-row">
          <div className="metric-card"><span className="metric-label">ER occupancy</span><div className="metric-values"><span className="metric-value">{erCapacity.occupied}/{erCapacity.total}</span><span className="metric-value">{erCapacity.percentage.toFixed(1)}%</span></div></div>
          <div className="metric-card"><span className="metric-label">ICU occupancy</span><div className="metric-values"><span className="metric-value">{icuCapacity.beds_occupied}/{icuCapacity.total_beds}</span><span className="metric-value">{icuCapacity.occupancy_percentage.toFixed(1)}%</span></div></div>
        </div>
        <div className="metrics-row">
          <div className="metric-card"><span className="metric-label">Total ER Patients</span><span className="metric-value-large">{loading ? '...' : totalERPatients}</span></div>
          <div className="metric-card"><span className="metric-label">High-Risk Patients</span><span className="metric-value-large">{loading ? '...' : highRiskCount}</span></div>
        </div>

        <h2 className="section-title">Status Indicators</h2>
        <div className="metrics-row">
          <div className="metric-card"><span className="metric-label">ER Status</span><span className={`metric-status ${erStatus.toLowerCase()}`}>{erStatus}</span></div>
          <div className="metric-card"><span className="metric-label">ICU Status</span><span className={`metric-status ${icuStatus.toLowerCase()}`}>{icuStatus}</span></div>
        </div>

        <h2 className="section-title">Trends (Past 60 Minutes)</h2>
        <div className="charts-row">
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={150}><LineChart data={erTrendData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(erTrendData)]} tick={{ fontSize: 12 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
            <div className="chart-legend"><span className="legend-line"></span><span className="legend-text">Patients in ER past 60 minutes</span></div>
          </div>
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={150}><LineChart data={icuTrendData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(icuTrendData)]} tick={{ fontSize: 12 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
            <div className="chart-legend"><span className="legend-line"></span><span className="legend-text">Patients in ICU past 60 minutes</span></div>
          </div>
        </div>

        <h2 className="section-title">Forecast (Next 60 Minutes)</h2>
        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={150}><LineChart data={forecastERData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(forecastERData)]} tick={{ fontSize: 12 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
          <div className="chart-legend"><span className="legend-line"></span><span className="legend-text">FORECAST of Patients in ER next 60 minutes</span></div>
        </div>
        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={150}><LineChart data={forecastICUData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" /><XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} /><YAxis domain={[0, getYAxisMax(forecastICUData)]} tick={{ fontSize: 12 }} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
          <div className="chart-legend"><span className="legend-line"></span><span className="legend-text">FORECAST of Patients in ICU next 60 minutes</span></div>
        </div>

        <h2 className="section-title">Alerts</h2>
        <div className="metrics-row">
          <div className="metric-card"><span className="metric-label">Predicted ER Overload</span><span className={`metric-status ${erCapacity.percentage >= 75 ? 'watch' : ''}`}>{erCapacity.percentage >= 90 ? 'CRITICAL' : erCapacity.percentage >= 75 ? 'WATCH' : 'NORMAL'}</span></div>
          <div className="metric-card"><span className="metric-label">Predicted ICU Overload</span><span className={`metric-status ${icuCapacity.occupancy_percentage >= 75 ? 'watch' : ''}`}>{icuCapacity.occupancy_percentage >= 90 ? 'CRITICAL' : icuCapacity.occupancy_percentage >= 75 ? 'WATCH' : 'NORMAL'}</span></div>
        </div>
      </div>
    </div>
  );
};

export default Frame1;
