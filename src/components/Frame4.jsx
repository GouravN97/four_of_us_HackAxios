import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Frame4_1 from './Frame4_1';
import './Frame4.css';

// Mock patient data with 5-minute interval logs
// TODO: Replace with actual database connection
const mockPatientLogs = [
  { id: 'P001', time: '09:30 AM', heartRate: 72, systolicBP: 120, respiratoryRate: 16, oxygenSat: 98, temperature: 98.6, arrivalMode: 'Walk-in' },
  { id: 'P001', time: '09:35 AM', heartRate: 74, systolicBP: 122, respiratoryRate: 16, oxygenSat: 98, temperature: 98.6, arrivalMode: 'Walk-in' },
  { id: 'P001', time: '09:40 AM', heartRate: 73, systolicBP: 121, respiratoryRate: 17, oxygenSat: 97, temperature: 98.7, arrivalMode: 'Walk-in' },
  { id: 'P001', time: '09:45 AM', heartRate: 75, systolicBP: 123, respiratoryRate: 16, oxygenSat: 98, temperature: 98.6, arrivalMode: 'Walk-in' },
  { id: 'P001', time: '09:50 AM', heartRate: 72, systolicBP: 120, respiratoryRate: 16, oxygenSat: 98, temperature: 98.5, arrivalMode: 'Walk-in' },
  { id: 'P002', time: '09:45 AM', heartRate: 88, systolicBP: 140, respiratoryRate: 20, oxygenSat: 95, temperature: 99.2, arrivalMode: 'Ambulance' },
  { id: 'P002', time: '09:50 AM', heartRate: 90, systolicBP: 142, respiratoryRate: 21, oxygenSat: 94, temperature: 99.3, arrivalMode: 'Ambulance' },
  { id: 'P002', time: '09:55 AM', heartRate: 87, systolicBP: 138, respiratoryRate: 20, oxygenSat: 95, temperature: 99.1, arrivalMode: 'Ambulance' },
  { id: 'P002', time: '10:00 AM', heartRate: 85, systolicBP: 136, respiratoryRate: 19, oxygenSat: 96, temperature: 99.0, arrivalMode: 'Ambulance' },
  { id: 'P003', time: '10:00 AM', heartRate: 65, systolicBP: 115, respiratoryRate: 14, oxygenSat: 99, temperature: 98.4, arrivalMode: 'Walk-in' },
  { id: 'P003', time: '10:05 AM', heartRate: 66, systolicBP: 116, respiratoryRate: 14, oxygenSat: 99, temperature: 98.4, arrivalMode: 'Walk-in' },
  { id: 'P003', time: '10:10 AM', heartRate: 64, systolicBP: 114, respiratoryRate: 15, oxygenSat: 98, temperature: 98.5, arrivalMode: 'Walk-in' },
  { id: 'P004', time: '10:15 AM', heartRate: 95, systolicBP: 150, respiratoryRate: 22, oxygenSat: 92, temperature: 100.1, arrivalMode: 'Ambulance' },
  { id: 'P004', time: '10:20 AM', heartRate: 93, systolicBP: 148, respiratoryRate: 21, oxygenSat: 93, temperature: 100.0, arrivalMode: 'Ambulance' },
  { id: 'P005', time: '10:30 AM', heartRate: 78, systolicBP: 125, respiratoryRate: 18, oxygenSat: 97, temperature: 98.8, arrivalMode: 'Walk-in' },
  { id: 'P005', time: '10:35 AM', heartRate: 77, systolicBP: 124, respiratoryRate: 17, oxygenSat: 97, temperature: 98.7, arrivalMode: 'Walk-in' },
];

const Frame4 = () => {
  const navigate = useNavigate();
  const [patientLogs, setPatientLogs] = useState(mockPatientLogs);
  const [removePatientId, setRemovePatientId] = useState('');
  const [searchPatientId, setSearchPatientId] = useState('');
  const [showAddPatient, setShowAddPatient] = useState(false);

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

  // Filter logs based on search - show all if empty, filter if searching
  // TODO: Connect to database for search
  const filteredLogs = searchPatientId 
    ? patientLogs.filter(log => log.id.toLowerCase().includes(searchPatientId.toLowerCase()))
    : patientLogs;

  const handleRemovePatient = () => {
    // TODO: Connect to database to remove patient
    if (removePatientId) {
      setPatientLogs(patientLogs.filter(log => log.id.toUpperCase() !== removePatientId.toUpperCase()));
      setRemovePatientId('');
    }
  };

  const handleAddPatient = (newPatient) => {
    // TODO: Connect to database to add patient
    setPatientLogs([...patientLogs, newPatient]);
    setShowAddPatient(false);
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
            // TODO: Connect to database for patient search
          />
        </div>

        {/* Patient Table */}
        <div className="table-container">
          <table className="patient-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Heart Rate</th>
                <th>Systolic BP</th>
                <th>Respiratory Rate</th>
                <th>Oxygen Saturation</th>
                <th>Temparature</th>
                <th>Arrival Mode</th>
              </tr>
            </thead>
            <tbody>
              {/* TODO: Replace with data from database (5-minute intervals) */}
              {filteredLogs.map((log, index) => (
                <tr key={index}>
                  <td>{log.time}</td>
                  <td>{log.heartRate}</td>
                  <td>{log.systolicBP}</td>
                  <td>{log.respiratoryRate}</td>
                  <td>{log.oxygenSat}</td>
                  <td>{log.temperature}</td>
                  <td>{log.arrivalMode}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

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
              // TODO: Connect to database for patient removal
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
