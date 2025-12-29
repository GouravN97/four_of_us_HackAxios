import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import Frame2_1 from './Frame2_1';
import './Frame2.css';

// Random data for charts
const generateData = () => {
  return Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: Math.floor(Math.random() * 80) + 10
  }));
};

const forecastData = generateData();
const waitingTimeData = generateData();

const Frame2 = () => {
  const navigate = useNavigate();
  const [showPrioritization, setShowPrioritization] = useState(false);

  const handleLogout = () => {
    navigate('/');
  };

  const handleOverview = () => {
    navigate('/dashboard');
  };

  const handleICU = () => {
    navigate('/icu');
  };

  const handlePatientLog = () => {
    navigate('/patient-log');
  };

  return (
    <div className="frame2">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item" onClick={handleOverview}>
            <img src="/assets/images/treatment-dark-icon.png" alt="Overview" className="menu-icon" />
            <span>Overview</span>
          </div>
          <div className="menu-item active">
            <img src="/assets/images/er-hospital-icon.png" alt="ER" className="menu-icon" />
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
        {/* Operational Metrics */}
        <h2 className="section-title">Operational Metrics</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Current ER inflow rate</span>
            <span className="metric-value">5 per 30 minutes</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Average waiting time</span>
            <span className="metric-value">36 minutes</span>
          </div>
        </div>
        <div className="metrics-row center">
          <div className="metric-card metric-card-tall">
            <span className="metric-label">Patients exceeding wait threshold</span>
            <span className="metric-value-large">6</span>
            <span className="metric-note">Wait threshold: 40 minutes</span>
          </div>
        </div>

        {/* Trends */}
        <h2 className="section-title">Trends</h2>
        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <span className="legend-line"></span>
            <span className="legend-text">FORECAST ER inflow for next 60 minutes</span>
          </div>
        </div>

        <div className="chart-card-wide">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={waitingTimeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#00B6B0" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <span className="legend-line"></span>
            <span className="legend-text">Waiting time distribution for the past 2 hours</span>
          </div>
        </div>

        {/* View Patient Prioritization Button */}
        <button className="prioritization-btn" onClick={() => setShowPrioritization(true)}>
          View patient prioritization
        </button>
      </div>

      {/* Patient Prioritization Popup */}
      {showPrioritization && (
        <Frame2_1 onClose={() => setShowPrioritization(false)} />
      )}
    </div>
  );
};

export default Frame2;
