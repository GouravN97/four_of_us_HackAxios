import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import './Frame1.css';

// Random data for charts
const generateData = () => {
  return Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: Math.floor(Math.random() * 80) + 10
  }));
};

const erData = generateData();
const icuData = generateData();
const forecastERData = generateData();
const forecastICUData = generateData();

const Frame1 = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    navigate('/');
  };

  return (
    <div className="frame1">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item active">
            <img src="/assets/images/treatment-icon.png" alt="Overview" className="menu-icon" />
            <span>Overview</span>
          </div>
          <div className="menu-item">
            <img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" />
            <span>ER</span>
          </div>
          <div className="menu-item">
            <img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" />
            <span>ICU</span>
          </div>
          <div className="menu-item">
            <img src="/assets/images/people-icon.png" alt="Patient Log" className="menu-icon" />
            <span>Patient Log</span>
          </div>
          <div className="menu-item">
            <img src="/assets/images/checkmark-icon.png" alt="Reasoning" className="menu-icon" />
            <span>Reasoning</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="header">
        <div className="header-left">
          <img src="/assets/images/logo.png" alt="Logo" className="header-logo" />
          <span className="header-brand">VERIQ</span>
        </div>
        <button className="logout-btn" onClick={handleLogout}>Logout</button>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Summary Metrics */}
        <h2 className="section-title">Summary Metrics</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">ER occupancy</span>
            <div className="metric-values">
              <span className="metric-value">20/40</span>
              <span className="metric-value">50.00%</span>
            </div>
          </div>
          <div className="metric-card">
            <span className="metric-label">ICU occupancy</span>
            <div className="metric-values">
              <span className="metric-value">20/40</span>
              <span className="metric-value">50.00%</span>
            </div>
          </div>
        </div>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">Total ER Patients</span>
            <span className="metric-value-large">49</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">High-Risk Patients</span>
            <span className="metric-value-large">14</span>
          </div>
        </div>

        {/* Status Indicators */}
        <h2 className="section-title">Status Indicators</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <span className="metric-label">ER Status</span>
            <span className="metric-status">NORMAL</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">ICU Status</span>
            <span className="metric-status">NORMAL</span>
          </div>
        </div>

        {/* Trends */}
        <h2 className="section-title">Trends</h2>
        <div className="charts-row">
          <div className="chart-card">
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={erData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
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
              <LineChart data={icuData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,26,0.15)" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
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
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
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
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
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
            <span className="metric-status watch">WATCH</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">Predicted ICU Overload</span>
            <span className="metric-status">NORMAL</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Frame1;
