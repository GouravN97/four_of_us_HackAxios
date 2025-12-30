import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSimulation } from '../contexts/SimulationContext';
import Frame4_1 from './Frame4_1';
import './Frame4.css';
import { getPatientHistory, getPatientStatus, registerPatient, getAllPatients, deletePatient } from '../services/api';

const ITEMS_PER_PAGE = 50;

const Frame4 = () => {
  const navigate = useNavigate();
  const { isRunning, simulatedTime, startSimulation, tickCount, formatSimTime } = useSimulation();
  const [patientLogs, setPatientLogs] = useState([]);
  const [removePatientId, setRemovePatientId] = useState('');
  const [searchPatientId, setSearchPatientId] = useState('');
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    const initSimulation = async () => {
      if (!isRunning) {
        try { await startSimulation(); } catch (err) { console.warn('Could not auto-start simulation:', err); }
      }
    };
    initSimulation();
  }, []);

  const fetchPatientLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const allPatientsResponse = await getAllPatients();
      const patientIds = allPatientsResponse.patient_ids || [];
      const allLogs = [];
      
      for (const patientId of patientIds) {
        try {
          const status = await getPatientStatus(patientId);
          const history = await getPatientHistory(patientId, { limit: 100 });
          
          // Show all data from database (no time filtering)
          const logs = history.data_points.map(point => {
            const vitals = point.vitals;
            const risk = point.risk_assessment;
            const timestamp = new Date(vitals.timestamp);
            
            return {
              id: patientId,
              time: timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
              timestamp: timestamp,
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
      
      // Sort by timestamp (most recent first)
      allLogs.sort((a, b) => b.timestamp - a.timestamp);
      setPatientLogs(allLogs);
    } catch (err) {
      console.error('Failed to fetch patient logs:', err);
      setError('Failed to load patient data. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  }, [tickCount]);

  useEffect(() => { fetchPatientLogs(); }, [tickCount, fetchPatientLogs]);

  const handleLogout = () => navigate('/');
  const handleOverview = () => navigate('/dashboard');
  const handleER = () => navigate('/er');
  const handleICU = () => navigate('/icu');

  const filteredLogs = searchPatientId 
    ? patientLogs.filter(log => log.id.toLowerCase().includes(searchPatientId.toLowerCase()))
    : patientLogs;

  const totalPages = Math.ceil(filteredLogs.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginatedLogs = filteredLogs.slice(startIndex, startIndex + ITEMS_PER_PAGE);

  useEffect(() => { setCurrentPage(1); }, [searchPatientId]);

  const handleRemovePatient = async () => {
    if (removePatientId) {
      try {
        await deletePatient(removePatientId.toUpperCase());
        setPatientLogs(patientLogs.filter(log => log.id.toUpperCase() !== removePatientId.toUpperCase()));
        setRemovePatientId('');
        fetchPatientLogs();
      } catch (err) {
        console.error('Failed to delete patient:', err);
        alert(`Failed to delete patient: ${err.message}`);
      }
    }
  };

  const handleAddPatient = async (newPatient) => {
    try {
      const patientData = {
        patient_id: newPatient.id,
        arrival_mode: newPatient.arrivalMode,
        acuity_level: newPatient.acuityLevel || 3,
        initial_vitals: {
          heart_rate: newPatient.heartRate,
          systolic_bp: newPatient.systolicBP,
          diastolic_bp: newPatient.diastolicBP || Math.round(newPatient.systolicBP * 0.65),
          respiratory_rate: newPatient.respiratoryRate,
          oxygen_saturation: newPatient.oxygenSat,
          temperature: newPatient.temperature,
          timestamp: simulatedTime ? simulatedTime.toISOString() : new Date().toISOString(),
        }
      };
      
      await registerPatient(patientData);
      setShowAddPatient(false);
      fetchPatientLogs();
    } catch (err) {
      console.error('Failed to add patient:', err);
      alert(`Failed to add patient: ${err.message}`);
    }
  };

  return (
    <div className="frame4">
      <div className="sidebar">
        <div className="sidebar-menu">
          <div className="menu-item" onClick={handleOverview}><img src="/assets/images/treatment-dark-icon.png" alt="Overview" className="menu-icon" /><span>Overview</span></div>
          <div className="menu-item" onClick={handleER}><img src="/assets/images/hospital-room-icon.png" alt="ER" className="menu-icon" /><span>ER</span></div>
          <div className="menu-item" onClick={handleICU}><img src="/assets/images/star-of-life-icon.png" alt="ICU" className="menu-icon" /><span>ICU</span></div>
          <div className="menu-item active"><img src="/assets/images/people-icon.png" alt="Patient Log" className="menu-icon" /><span>Patient Log</span></div>
        </div>
      </div>

      <div className="header">
        <div className="header-left"><img src="/assets/images/logo.png" alt="Logo" className="header-logo" /><span className="header-brand">VERIQ</span></div>
        <div className="header-center"><span className="sim-time">{isRunning ? `🕐 ${formatSimTime('datetime')}` : 'Starting...'}</span></div>
        <div className="header-right"><span className="logout-text" onClick={handleLogout}>Logout</span><img src="/assets/images/logout-icon.png" alt="Logout" className="logout-icon" onClick={handleLogout} /></div>
      </div>

      <div className="main-content">
        <h2 className="section-title">Patient Log</h2>
        
        <div className="search-row">
          <label className="search-label">Search Patient ID :</label>
          <input type="text" className="search-input" placeholder="" value={searchPatientId} onChange={(e) => setSearchPatientId(e.target.value)} />
          <button className="refresh-btn" onClick={fetchPatientLogs} style={{ marginLeft: '10px', padding: '5px 15px', cursor: 'pointer' }}>Refresh</button>
        </div>

        {loading && <div className="loading-message" style={{ padding: '20px', textAlign: 'center' }}>Loading patient data...</div>}
        {error && <div className="error-message" style={{ padding: '20px', textAlign: 'center', color: 'red' }}>{error}</div>}

        {!loading && !error && (
          <>
            <div className="table-info" style={{ marginBottom: '10px', color: '#666' }}>
              Showing {startIndex + 1}-{Math.min(startIndex + ITEMS_PER_PAGE, filteredLogs.length)} of {filteredLogs.length} records
            </div>
            <div className="table-container">
              <table className="patient-table">
                <thead>
                  <tr>
                    <th>Patient ID</th><th>Time</th><th>Heart Rate</th><th>Systolic BP</th><th>Respiratory Rate</th><th>Oxygen Saturation</th><th>Temperature</th><th>Risk Score</th><th>Risk Level</th><th>Arrival Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedLogs.length === 0 ? (
                    <tr><td colSpan="10" style={{ textAlign: 'center', padding: '20px' }}>No patient data found. Run the database population script to add sample data.</td></tr>
                  ) : (
                    paginatedLogs.map((log, index) => (
                      <tr key={index} className={log.riskCategory === 'HIGH' ? 'high-risk-row' : ''}>
                        <td>{log.id}</td><td>{log.time}</td><td>{log.heartRate}</td><td>{log.systolicBP}</td><td>{log.respiratoryRate}</td><td>{log.oxygenSat}</td><td>{log.temperature}</td><td>{log.riskScore}</td><td className={`risk-${log.riskCategory?.toLowerCase()}`}>{log.riskCategory}</td><td>{log.arrivalMode}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            {totalPages > 1 && (
              <div className="pagination" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginTop: '15px' }}>
                <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} style={{ padding: '5px 10px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}>First</button>
                <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} style={{ padding: '5px 10px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}>Prev</button>
                <span>Page {currentPage} of {totalPages}</span>
                <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} style={{ padding: '5px 10px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}>Next</button>
                <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} style={{ padding: '5px 10px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}>Last</button>
              </div>
            )}
          </>
        )}

        <div className="actions-row">
          <button className="add-patient-btn" onClick={() => setShowAddPatient(true)}>Add Patient</button>
          <div className="action-group">
            <label className="action-label">Remove Patient:</label>
            <input type="text" className="action-input" value={removePatientId} onChange={(e) => setRemovePatientId(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleRemovePatient()} />
          </div>
        </div>
      </div>

      {showAddPatient && <Frame4_1 onClose={() => setShowAddPatient(false)} onAdd={handleAddPatient} />}
    </div>
  );
};

export default Frame4;
