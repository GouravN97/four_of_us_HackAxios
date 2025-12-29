import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import './Frame3.css';

// Random data for chart
const generateData = () => {
  return Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: Math.floor(Math.random() * 80) + 10
  }));
};

const forecastData = generateData();

// Mock recommendations data
// TODO: Connect to database
const recommendations = [
  { id: '58689', urgency: 'HIGH', reason: 'Rising respiratory rate and falling oxygen saturation over the last 30 minutes. ICU occupancy predicted to remain below safe limits for the next hour, making early admission beneficial' },
  { id: '53455', urgency: 'HIGH', reason: 'Rising respiratory rate and falling oxygen saturation over the last 30 minutes. ICU occupancy predicted to remain below safe limits for the next hour, making early admission beneficial' },
  { id: '53455', urgency: 'MEDIUM', reason: 'Rising respiratory rate and falling oxygen saturation over the last 30 minutes. ICU occupancy predicted to remain below safe limits for the next hour, making early admission beneficial' },
  { id: '53455', urgency: 'MEDIUM', reason: 'Rising respiratory rate and falling oxygen saturation over the last 30 minutes. ICU occupancy predicted to remain below safe limits for the next hour, making early admission beneficial' },
  { id: '53455', urgency: 'LOW', reason: 'Rising respiratory rate and falling oxygen saturation over the last 30 minutes. ICU occupancy predicted to remain below safe limits for the next hour, making early admission beneficial' },
];

const Frame3 = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    navigate('/');
  };

  const handleOverview = () => {
    navigate('/dashboard');
  };

  const handleER = () => {
    navigate('/er');
  };

  const handlePatientLog = () => {
    navigate('/patient-log');
  };

  return (
    <div className="frame3">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item" onClick={handleOverview}>
            <img src="/assets/images/treatment-dark-icon.png" alt="Overview" className="menu-icon" />
            <span>Overview</span>
          </div>
          <div className="menu-item" onClick={handleER}>
            <img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" />
            <span>ER</span>
          </div>
          <div className="menu-item active">
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
        {/* Capacity Metrics */}
        <h2 className="section-title">Capacity Metrics</h2>
        
        <div className="metrics-container">
          <div className="metric-card beds-card">
            <span className="metric-label">Beds occupied</span>
            <div className="metric-values">
              <span className="metric-value">30/60</span>
              <span className="metric-value">50.00%</span>
            </div>
          </div>

          <div className="metrics-row-bottom">
            <div className="metric-card staff-card">
              <span className="metric-label">Nurses on duty</span>
              <div className="staff-info">
                <span className="urgency-badge medium">MEDIUM</span>
                <span className="metric-value">20/35</span>
              </div>
            </div>
            
            <div className="metric-card staff-card">
              <span className="metric-label">Doctors on duty</span>
              <div className="staff-info">
                <span className="urgency-badge low">LOW</span>
                <span className="metric-value">5/15</span>
              </div>
            </div>
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
            <span className="legend-text">FORECAST ICU occupancy for next 60 minutes</span>
          </div>
        </div>

        {/* Recommendations */}
        <h2 className="section-title">Recommendations</h2>
        <div className="recommendations-container">
          {/* TODO: Connect to database for real recommendations */}
          {recommendations.map((rec, index) => (
            <div key={index} className="recommendation-card">
              <div className="rec-header">
                <span className="rec-label">Patient ID:</span>
                <span className="rec-id">{rec.id}</span>
              </div>
              <div className="rec-urgency">
                <span className="rec-label">Urgency:</span>
                <span className={`urgency-text ${rec.urgency.toLowerCase()}`}>{rec.urgency}</span>
              </div>
              <div className="rec-reason">
                <span className="rec-label">Reason:</span>
                <p className="rec-reason-text">{rec.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Frame3;
