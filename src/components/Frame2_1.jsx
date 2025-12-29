import { useState } from 'react';
import './Frame2_1.css';

// Mock data for patient prioritization table
// TODO: Replace with actual database connection
const mockPatients = [
  { id: 'P001', deteriorationRisk: 'High', severity: 'Critical', waitTime: '52 min', priority: 1, confidenceScore: '92%', explainability: 'High blood pressure, chest pain symptoms, history of cardiac issues' },
  { id: 'P002', deteriorationRisk: 'Medium', severity: 'Moderate', waitTime: '38 min', priority: 3, confidenceScore: '85%', explainability: 'Moderate fever, respiratory symptoms, no underlying conditions' },
  { id: 'P003', deteriorationRisk: 'High', severity: 'Critical', waitTime: '45 min', priority: 2, confidenceScore: '89%', explainability: 'Diabetic emergency, low blood sugar levels, requires immediate attention' },
  { id: 'P004', deteriorationRisk: 'Low', severity: 'Minor', waitTime: '25 min', priority: 6, confidenceScore: '78%', explainability: 'Minor injury, no complications expected' },
  { id: 'P005', deteriorationRisk: 'High', severity: 'Critical', waitTime: '60 min', priority: 1, confidenceScore: '95%', explainability: 'Stroke symptoms, time-sensitive treatment required' },
  { id: 'P006', deteriorationRisk: 'Medium', severity: 'Moderate', waitTime: '33 min', priority: 4, confidenceScore: '82%', explainability: 'Abdominal pain, requires further diagnosis' },
  { id: 'P007', deteriorationRisk: 'High', severity: 'Critical', waitTime: '48 min', priority: 1, confidenceScore: '91%', explainability: 'Breathing difficulties, oxygen levels dropping' },
  { id: 'P008', deteriorationRisk: 'Low', severity: 'Minor', waitTime: '20 min', priority: 7, confidenceScore: '75%', explainability: 'Routine checkup follow-up, minor concerns' },
  { id: 'P009', deteriorationRisk: 'Medium', severity: 'Moderate', waitTime: '42 min', priority: 5, confidenceScore: '80%', explainability: 'Back pain, possible disc issue' },
  { id: 'P010', deteriorationRisk: 'High', severity: 'Critical', waitTime: '55 min', priority: 2, confidenceScore: '93%', explainability: 'Severe allergic reaction, anaphylaxis risk' },
];

const Frame2_1 = ({ onClose }) => {
  const [searchId, setSearchId] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);

  // TODO: Connect to database for search functionality
  // Filter patients based on search ID and sort by priority
  const filteredPatients = (searchId 
    ? mockPatients.filter(p => p.id.toLowerCase().includes(searchId.toLowerCase()))
    : mockPatients
  ).sort((a, b) => a.priority - b.priority);

  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('popup-overlay')) {
      onClose();
    }
  };

  const handleRowClick = (patient) => {
    setSelectedPatient(patient);
  };

  const closeExplainability = (e) => {
    if (e.target.classList.contains('explainability-overlay')) {
      setSelectedPatient(null);
    }
  };

  return (
    <div className="popup-overlay" onClick={handleOverlayClick}>
      <div className="popup-content">
        <h2 className="popup-title">Patient Prioritization</h2>
        
        {/* Search Input */}
        <div className="search-container">
          <label className="search-label">Search Patient ID</label>
          <input 
            type="text" 
            className="search-input"
            placeholder="Enter Patient ID..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            // TODO: Connect to database search API
          />
        </div>

        {/* Patient Table */}
        <div className="table-container">
          <table className="patient-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Deterioration Risk</th>
                <th>Severity</th>
                <th>Waiting Time</th>
                <th>Priority</th>
                <th>Confidence Score</th>
              </tr>
            </thead>
            <tbody>
              {/* TODO: Replace with data from database */}
              {filteredPatients.map((patient) => (
                <tr 
                  key={patient.id} 
                  onClick={() => handleRowClick(patient)}
                  className={`table-row ${patient.deteriorationRisk === 'High' ? 'high-priority' : ''}`}
                >
                  <td>{patient.id}</td>
                  <td className={`risk-${patient.deteriorationRisk.toLowerCase()}`}>{patient.deteriorationRisk}</td>
                  <td className={`severity-${patient.severity.toLowerCase()}`}>{patient.severity}</td>
                  <td>{patient.waitTime}</td>
                  <td>{patient.priority}</td>
                  <td>{patient.confidenceScore}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Close button */}
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      {/* Explainability Popup */}
      {selectedPatient && (
        <div className="explainability-overlay" onClick={closeExplainability}>
          <div className="explainability-popup">
            <h3>Patient Explainability</h3>
            <p><strong>Patient ID:</strong> {selectedPatient.id}</p>
            <p><strong>Deterioration Risk:</strong> {selectedPatient.deteriorationRisk}</p>
            <p><strong>Severity:</strong> {selectedPatient.severity}</p>
            <p><strong>Priority:</strong> {selectedPatient.priority}</p>
            <p><strong>Reasoning:</strong></p>
            <p className="explainability-text">{selectedPatient.explainability}</p>
            {/* TODO: Fetch explainability from database based on patient ID */}
            <button className="close-explainability-btn" onClick={() => setSelectedPatient(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Frame2_1;
