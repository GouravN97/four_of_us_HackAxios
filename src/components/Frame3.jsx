import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { useSimulation } from '../contexts/SimulationContext';
import './Frame3.css';
import { getICUCapacity, getICUOccupancyHistory } from '../services/api';

const getYAxisMax = (data) => {
  if (!data || data.length === 0) return 10;
  const maxValue = Math.max(...data.map(d => Math.max(d.value || 0, d.upper || 0)));
  if (maxValue <= 5) return Math.max(5, maxValue + 2);
  if (maxValue <= 10) return Math.ceil(maxValue * 1.3);
  if (maxValue <= 20) return Math.ceil(maxValue / 5) * 5 + 5;
  return Math.ceil(maxValue / 10) * 10 + 10;
};

const Frame3 = () => {
  const navigate = useNavigate();
  const { isRunning, simulatedTime, startSimulation, tickCount, formatSimTime, generateTimeLabels } = useSimulation();
  const [capacity, setCapacity] = useState(null);
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initSimulation = async () => {
      if (!isRunning) {
        try { await startSimulation(); } catch (err) { console.warn('Could not auto-start simulation:', err); }
      }
    };
    initSimulation();
  }, []);

  const fetchAllData = useCallback(async () => {
    if (!simulatedTime) return;
    
    try {
      setLoading(true);
      const data = await getICUCapacity();
      setCapacity(data);
      generateForecast(data.beds_occupied);
    } catch (err) {
      console.warn('Could not fetch ICU capacity:', err);
      setCapacity({ total_beds: 15, beds_occupied: 7, beds_available: 8, occupancy_percentage: 46.67, high_risk_patients: 0 });
      generateForecast(7);
    } finally {
      setLoading(false);
    }
  }, [simulatedTime]);

  const generateForecast = useCallback((currentOccupancy) => {
    if (!simulatedTime) return;
    
    const futureLabels = generateTimeLabels(60, 6, 'future');
    const forecast = futureLabels.map((label, i) => {
      const variation = Math.floor(Math.random() * 5) - 2;
      const predicted = Math.max(0, currentOccupancy + variation);
      return {
        time: label.time,
        value: predicted,
        lower: Math.max(0, predicted - 2),
        upper: predicted + 2
      };
    });
    setForecastData(forecast);
  }, [simulatedTime, generateTimeLabels]);

  useEffect(() => { fetchAllData(); }, [tickCount, fetchAllData]);

  const handleLogout = () => navigate('/');
  const handleOverview = () => navigate('/dashboard');
  const handleER = () => navigate('/er');
  const handlePatientLog = () => navigate('/patient-log');

  return (
    <div className="frame3">
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item" onClick={handleOverview}><img src="/assets/images/treatment-dark-icon.png" alt="Overview" className="menu-icon" /><span>Overview</span></div>
          <div className="menu-item" onClick={handleER}><img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" /><span>ER</span></div>
          <div className="menu-item active"><img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" /><span>ICU</span></div>
          <div className="menu-item" onClick={handlePatientLog}><img src="/assets/images/people-icon.png" alt="Patient Log" className="menu-icon" /><span>Patient Log</span></div>
        </div>
      </div>

      <div className="header">
        <div className="header-left"><img src="/assets/images/logo.png" alt="Logo" className="header-logo" /><span className="header-brand">VERIQ</span></div>
        <div className="header-center"><span className="sim-time">{isRunning ? `🕐 ${formatSimTime('datetime')}` : 'Starting...'}</span></div>
        <div className="header-right"><span className="logout-text" onClick={handleLogout}>Logout</span><img src="/assets/images/logout-icon.png" alt="Logout" className="logout-icon" onClick={handleLogout} /></div>
      </div>

      <div className="main-content">
        <h2 className="section-title">Capacity Metrics</h2>
        <div className="metrics-container">
          <div className="metric-card beds-card">
            <span className="metric-label">Beds occupied</span>
            <div className="metric-values">
              <span className="metric-value">{capacity ? `${capacity.beds_occupied}/${capacity.total_beds}` : '7/15'}</span>
              <span className="metric-value">{capacity ? `${capacity.occupancy_percentage.toFixed(1)}%` : '50.0%'}</span>
            </div>
          </div>
          <div className="metrics-row-bottom">
            <div className="metric-card staff-card">
              <span className="metric-label">High Risk Patients</span>
              <div className="staff-info">
                <span className={`urgency-badge ${capacity && capacity.high_risk_patients > 5 ? 'high' : 'medium'}`}>{capacity && capacity.high_risk_patients > 5 ? 'HIGH' : 'MEDIUM'}</span>
                <span className="metric-value">{capacity ? capacity.high_risk_patients : 0}</span>
              </div>
            </div>
            <div className="metric-card staff-card">
              <span className="metric-label">Available Beds</span>
              <div className="staff-info">
                <span className={`urgency-badge ${capacity && capacity.beds_available < 10 ? 'high' : 'low'}`}>{capacity && capacity.beds_available < 10 ? 'LOW' : 'OK'}</span>
                <span className="metric-value">{capacity ? capacity.beds_available : 8}</span>
              </div>
            </div>
          </div>
        </div>

        <h2 className="section-title">ICU Load Forecast (Next 6 Hours)</h2>
        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, getYAxisMax(forecastData)]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={true} name="Predicted" />
              {forecastData[0]?.lower && <Line type="monotone" dataKey="lower" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Lower Bound" />}
              {forecastData[0]?.upper && <Line type="monotone" dataKey="upper" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Upper Bound" />}
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend"><span className="legend-line"></span><span className="legend-text">Predicted ICU occupancy for next 6 hours</span></div>
        </div>
      </div>
    </div>
  );
};

export default Frame3;
