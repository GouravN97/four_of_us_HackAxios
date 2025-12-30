import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Frame4_1 from './Frame4_1';
import './Frame4.css';
import { 
  getPatientHistory, 
  getPatientStatus, 
  registerPatient,
  getAllPatients,
  transformHistoryToLogs 
} from '../services/api';

const Frame4 = () => {
  const navigate = useNavigate();
  const [patientLogs, setPatientLogs] = useState([]);
  const [removePatientId, setRemovePatientId] = useState('');
  const [searchPatientId, setSearchPatientId] = useState('');
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch patient logs from the API
  useEffect(() => {
    fetchPatientLogs();
  }, []);

  const fetchPatientLogs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get all patient IDs from the API
      const allPatientsResponse = await getAllPatients();
      const patientIds = allPatientsResponse.patient_ids || [];
      
      const allLogs = [];
      
      for (const patientId of patientIds) {
        try {
          // Get patient history
          const history = await getPatientHistory(patientId, { limit: 10 });
          
          // Get patient status for arrival mode
          const status = await getPatientStatus(patientId);
          
          // Transform history to log format
          const logs = history.data_points.map(point => {
            const vitals = point.vitals;
            const risk = point.risk_assessment;
            const timestamp = new Date(vitals.timestamp);
            
            return {
              id: patientId,
              time: timestamp.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: true 
              }),
              heartRate: Math.round(vitals.heart_rate),
              systolicBP: Math.round(vitals.systolic_bp),
              respiratoryRate: Math.round(vitals.respiratory_rate),
              oxygenSat: Math.round(vitals.oxygen_saturation),
              temperature: parseFloat(vitals.temperature.toFixed(1)),
              arrivalMode: status.arrival_mode,
              riskScore: risk ? risk.risk_score.toFixed(1) : 'N/A',
              riskCategory: risk ? risk.risk_category : 'N/A',
            };
          });
          
          allLogs.push(...logs);
        } catch (err) {
          console.warn(`Could not fetch data for patient ${patientId}:`, err);
        }
      }
      
      // Sort by time (most recent first)
      allLogs.sort((a, b) => {
        const timeA = new Date(`1970/01/01 ${a.time}`);
        const timeB = new Date(`1970/01/01 ${b.time}`);
        return timeB - timeA;
      });
      
      setPatientLogs(allLogs);
    } catch (err) {
      console.error('Failed to fetch patient logs:', err);
      setError('Failed to load patient data. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    navigate('/');
  };

  const handleOverview = () => {
    navigate('/dashboard');
  };

  const handleER = () => {
    navigate('/er');
  };

  const handleICU = () => {
    navigate('/icu');
  };

  // Filter logs based on search
  const filteredLogs = searchPatientId 
    ? patientLogs.filter(log => log.id.toLowerCase().includes(searchPatientId.toLowerCase()))
    : patientLogs;

  const handleRemovePatient = () => {
    if (removePatientId) {
      // Remove from local state (in production, this would call a delete API)
      setPatientLogs(patientLogs.filter(log => log.id.toUpperCase() !== removePatientId.toUpperCase()));
      setRemovePatientId('');
    }
  };

  const handleAddPatient = async (newPatient) => {
    try {
      // Prepare data for API
      const patientData = {
        patient_id: newPatient.id,
        arrival_mode: newPatient.arrivalMode,
        acuity_level: 3, // Default acuity level
        initial_vitals: {
          heart_rate: newPatient.heartRate,
          systolic_bp: newPatient.systolicBP,
          diastolic_bp: Math.round(newPatient.systolicBP * 0.65), // Estimate diastolic
          respiratory_rate: newPatient.respiratoryRate,
          oxygen_saturation: newPatient.oxygenSat,
          temperature: (newPatient.temperature - 32) * 5/9 + 32 > 45 
            ? (newPatient.temperature - 32) * 5/9 // Convert if Fahrenheit
            : newPatient.temperature,
          timestamp: new Date().toISOString(),
        }
      };
      
      // Register patient via API
      await registerPatient(patientData);
      
      // Add to local state
      setPatientLogs([newPatient, ...patientLogs]);
      setShowAddPatient(false);
      
      // Refresh data
      fetchPatientLogs();
    } catch (err) {
      console.error('Failed to add patient:', err);
      // Still add to local state for demo purposes
      setPatientLogs([newPatient, ...patientLogs]);
      setShowAddPatient(false);
    }
  };

  return (
    <div className="frame4">
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
          <div className="menu-item" onClick={handleICU}>
            <img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" />
            <span>ICU</span>
          </div>
          <div className="menu-item active">
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
        <h2 className="section-title">Patient Log</h2>
        
        {/* Search Patient ID */}
        <div className="search-row">
          <label className="search-label">Search Patient ID :</label>
          <input
            type="text"
            className="search-input"
            placeholder=""
            value={searchPatientId}
            onChange={(e) => setSearchPatientId(e.target.value)}
          />
          <button 
            className="refresh-btn" 
            onClick={fetchPatientLogs}
            style={{ marginLeft: '10px', padding: '5px 15px', cursor: 'pointer' }}
          >
            Refresh
          </button>
        </div>

        {/* Loading/Error States */}
        {loading && (
          <div className="loading-message" style={{ padding: '20px', textAlign: 'center' }}>
            Loading patient data...
          </div>
        )}
        
        {error && (
          <div className="error-message" style={{ padding: '20px', textAlign: 'center', color: 'red' }}>
            {error}
          </div>
        )}

        {/* Patient Table */}
        {!loading && !error && (
          <div className="table-container">
            <table className="patient-table">
              <thead>
                <tr>
                  <th>Patient ID</th>
                  <th>Time</th>
                  <th>Heart Rate</th>
                  <th>Systolic BP</th>
                  <th>Respiratory Rate</th>
                  <th>Oxygen Saturation</th>
                  <th>Temperature</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Arrival Mode</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', padding: '20px' }}>
                      No patient data found. Run the database population script to add sample data.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log, index) => (
                    <tr key={index} className={log.riskCategory === 'HIGH' ? 'high-risk-row' : ''}>
                      <td>{log.id}</td>
                      <td>{log.time}</td>
                      <td>{log.heartRate}</td>
                      <td>{log.systolicBP}</td>
                      <td>{log.respiratoryRate}</td>
                      <td>{log.oxygenSat}</td>
                      <td>{log.temperature}</td>
                      <td>{log.riskScore}</td>
                      <td className={`risk-${log.riskCategory?.toLowerCase()}`}>{log.riskCategory}</td>
                      <td>{log.arrivalMode}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Actions Row */}
        <div className="actions-row">
          <button className="add-patient-btn" onClick={() => setShowAddPatient(true)}>
            Add Patient
          </button>
          <div className="action-group">
            <label className="action-label">Remove Patient:</label>
            <input
              type="text"
              className="action-input"
              value={removePatientId}
              onChange={(e) => setRemovePatientId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRemovePatient()}
            />
          </div>
        </div>
      </div>

      {/* Add Patient Popup */}
      {showAddPatient && (
        <Frame4_1 
          onClose={() => setShowAddPatient(false)} 
          onAdd={handleAddPatient}
        />
      )}
    </div>
  );
};

export default Frame4;