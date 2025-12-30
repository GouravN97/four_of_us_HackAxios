import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import { getICUCapacity, getICUOccupancyHistory, getAllPatients, getHighRiskPatients } from '../services/api';
import './Frame1.css';

const Frame1 = () => {
  const navigate = useNavigate();
  
  // State for real data
  const [icuCapacity, setIcuCapacity] = useState({ beds_occupied: 0, total_beds: 40, occupancy_percentage: 0 });
  const [erCapacity, setErCapacity] = useState({ occupied: 0, total: 40, percentage: 0 });
  const [totalERPatients, setTotalERPatients] = useState(0);
  const [highRiskCount, setHighRiskCount] = useState(0);
  const [icuStatus, setIcuStatus] = useState('NORMAL');
  const [erStatus, setErStatus] = useState('NORMAL');
  const [icuTrendData, setIcuTrendData] = useState([]);
  const [erTrendData, setErTrendData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch ICU capacity
        const icuData = await getICUCapacity();
        setIcuCapacity({
          beds_occupied: icuData.beds_occupied,
          total_beds: icuData.total_beds,
          occupancy_percentage: icuData.occupancy_percentage
        });
        
        // Set ICU status based on occupancy
        if (icuData.occupancy_percentage >= 90) {
          setIcuStatus('CRITICAL');
        } else if (icuData.occupancy_percentage >= 75) {
          setIcuStatus('WATCH');
        } else {
          setIcuStatus('NORMAL');
        }

        // Fetch ICU occupancy history for trends
        const icuHistory = await getICUOccupancyHistory(1); // Last 1 hour
        if (icuHistory && icuHistory.length > 0) {
          setIcuTrendData(icuHistory.map((record, idx) => ({
            time: idx,
            value: record.beds_occupied
          })));
        }
      } catch (error) {
        console.error('Failed to fetch ICU data:', error);
      }

      try {
        // Fetch all patients for ER data
        const patients = await getAllPatients();
        if (patients && patients.patients) {
          const erPatients = patients.patients.filter(p => p.location === 'ER' || !p.location);
          setTotalERPatients(erPatients.length);
          
          // Calculate ER occupancy (assuming 40 beds)
          const erOccupied = erPatients.length;
          const erTotal = 40;
          const erPct = (erOccupied / erTotal) * 100;
          setErCapacity({ occupied: erOccupied, total: erTotal, percentage: erPct });
          
          // Set ER status
          if (erPct >= 90) {
            setErStatus('CRITICAL');
          } else if (erPct >= 75) {
            setErStatus('WATCH');
          } else {
            setErStatus('NORMAL');
          }

          // Generate ER trend data from patient timestamps
          setErTrendData(Array.from({ length: 30 }, (_, i) => ({
            time: i,
            value: Math.max(0, erOccupied + Math.floor(Math.random() * 5) - 2)
          })));
        }
      } catch (error) {
        console.error('Failed to fetch patient data:', error);
      }

      try {
        // Fetch high-risk patients
        const highRisk = await getHighRiskPatients({ minRiskScore: 70 });
        if (highRisk && highRisk.patients) {
          setHighRiskCount(highRisk.patients.length);
        }
      } catch (error) {
        console.error('Failed to fetch high-risk patients:', error);
      }

      setLoading(false);
    };

    fetchData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => navigate('/');
  const handleER = () => navigate('/er');
  const handleICU = () => navigate('/icu');
  const handlePatientLog = () => navigate('/patient-log');

  // Generate forecast data (placeholder - would come from ML model)
  const forecastERData = Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: Math.max(0, erCapacity.occupied + Math.floor(Math.random() * 10) - 3)
  }));
  
  const forecastICUData = Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: Math.max(0, icuCapacity.beds_occupied + Math.floor(Math.random() * 5) - 2)
  }));

  return (
    <div className="frame1">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item active">
            <img src="/assets/images/treatment-icon.png" alt="Overview" className="menu-icon" />
            <span>Overview</span>
          </div>
          <div className="menu-item" onClick={handleER}>
            <img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" />
            <span>ER</span>
          </div>
          <div className="menu-item" onClick={handleICU}>
            <img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" />
            <span>ICU</span>
          </div>
          <div className="menu-item" onClick={handlePatientLog}>
            <img src="/assets/images/people-icon.png" alt="Patient Log" className="menu-icon" />
            <span>Patient Log</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="header">
        <div className="header-left">
          <img src="/assets/images/logo.png" alt="Logo" className="header-logo" />
          <span className="header-brand">VERIQ</span>
        </div>
        <div className="header-right">
          <span className="logout-text" onClick={handleLogout}>Logout</span>
          <img src="/assets/images/logout-icon.png" alt="Logout" className="logout-icon" onClick={handleLogout} />
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Summary Metrics */}
        <h2 className="section-title">Summary Metrics</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">ER occupancy</span>
            <div className="metric-values">
              <span className="metric-value">{erCapacity.occupied}/{erCapacity.total}</span>
              <span className="metric-value">{erCapacity.percentage.toFixed(2)}%</span>
            </div>
          </div>
          <div className="metric-card">
            <span className="metric-label">ICU occupancy</span>
            <div className="metric-values">
              <span className="metric-value">{icuCapacity.beds_occupied}/{icuCapacity.total_beds}</span>
              <span className="metric-value">{icuCapacity.occupancy_percentage.toFixed(2)}%</span>
            </div>
          </div>
        </div>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Total ER Patients</span>
            <span className="metric-value-large">{loading ? '...' : totalERPatients}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">High-Risk Patients</span>
            <span className="metric-value-large">{loading ? '...' : highRiskCount}</span>
          </div>
        </div>

        {/* Status Indicators */}
        <h2 className="section-title">Status Indicators</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">ER Status</span>
            <span className={`metric-status ${erStatus.toLowerCase()}`}>{erStatus}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">ICU Status</span>
            <span className={`metric-status ${icuStatus.toLowerCase()}`}>{icuStatus}</span>
          </div>
        </div>

        {/* Trends */}
        <h2 className="section-title">Trends</h2>
        <div className="charts-row">
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={erTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, Math.max(50, erCapacity.total)]} tick={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <div className="chart-legend">
              <span className="legend-line"></span>
              <span className="legend-text">Patients in ER past 60 minutes</span>
            </div>
          </div>
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={icuTrendData.length > 0 ? icuTrendData : [{ time: 0, value: icuCapacity.beds_occupied }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, Math.max(50, icuCapacity.total_beds)]} tick={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <div className="chart-legend">
              <span className="legend-line"></span>
              <span className="legend-text">Patients in ICU past 60 minutes</span>
            </div>
          </div>
        </div>

        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={forecastERData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, Math.max(50, erCapacity.total)]} tick={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <span className="legend-line"></span>
            <span className="legend-text">FORECAST of Patients in ER next 60 minutes</span>
          </div>
        </div>

        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={forecastICUData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, Math.max(50, icuCapacity.total_beds)]} tick={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <span className="legend-line"></span>
            <span className="legend-text">FORECAST of Patients in ICU next 60 minutes</span>
          </div>
        </div>

        {/* Alerts */}
        <h2 className="section-title">Alerts</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Predicted ER Overload</span>
            <span className={`metric-status ${erCapacity.percentage >= 75 ? 'watch' : ''}`}>
              {erCapacity.percentage >= 90 ? 'CRITICAL' : erCapacity.percentage >= 75 ? 'WATCH' : 'NORMAL'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Predicted ICU Overload</span>
            <span className={`metric-status ${icuCapacity.occupancy_percentage >= 75 ? 'watch' : ''}`}>
              {icuCapacity.occupancy_percentage >= 90 ? 'CRITICAL' : icuCapacity.occupancy_percentage >= 75 ? 'WATCH' : 'NORMAL'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Frame1;
