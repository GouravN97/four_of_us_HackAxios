import { useState, useEffect } from 'react';
import { useSimulation } from '../contexts/SimulationContext';
import './Frame2_1.css';
import { getAllPatients, getPatientStatus, getPatientExplanation } from '../services/api';

const Frame2_1 = ({ onClose }) => {
  const { simulatedTime } = useSimulation();
  const [searchId, setSearchId] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [explanationData, setExplanationData] = useState(null);

  useEffect(() => { fetchPatients(); }, []);

  const fetchPatients = async () => {
    setLoading(true);
    try {
      const allPatientsResponse = await getAllPatients();
      const patientIds = allPatientsResponse.patient_ids || [];
      
      const patientPromises = patientIds.map(async (patientId) => {
        try {
          const status = await getPatientStatus(patientId);
          const registrationTime = new Date(status.registration_time);
          
          const waitTimeMinutes = simulatedTime ? Math.round((simulatedTime - registrationTime) / (1000 * 60)) : 0;
          const risk = status.current_risk;
          const vitals = status.current_vitals;
          
          let deteriorationRisk = 'Low';
          let severity = 'Minor';
          let priority = 7;
          
          if (risk.risk_category === 'HIGH' || risk.risk_score >= 65) {
            deteriorationRisk = 'High';
            severity = 'Critical';
            priority = 1;
          } else if (risk.risk_category === 'MODERATE' || risk.risk_score >= 45) {
            deteriorationRisk = 'Medium';
            severity = 'Moderate';
            priority = 4;
          }
          
          if (waitTimeMinutes > 45 && priority > 1) {
            priority = Math.max(1, priority - 1);
          }
          
          const confidenceScore = Math.min(95, Math.max(75, 80 + (risk.risk_score / 10)));
          const explainability = generateExplainability(vitals, risk);
          
          return {
            id: patientId,
            deteriorationRisk,
            severity,
            waitTimeMinutes,
            priority,
            confidenceScore: `${Math.round(confidenceScore)}%`,
            explainability,
            riskScore: risk.risk_score,
            riskCategory: risk.risk_category,
            vitals: vitals
          };
        } catch (err) {
          console.warn(`Could not fetch status for ${patientId}:`, err);
          return null;
        }
      });
      
      const results = await Promise.all(patientPromises);
      const patientData = results.filter(p => p !== null);
      patientData.sort((a, b) => a.priority - b.priority || b.riskScore - a.riskScore);
      setPatients(patientData);
    } catch (error) {
      console.error('Failed to fetch patients:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateExplainability = (vitals, risk) => {
    const reasons = [];
    if (vitals.heart_rate > 100) reasons.push('elevated heart rate (tachycardia)');
    else if (vitals.heart_rate < 60) reasons.push('low heart rate (bradycardia)');
    if (vitals.systolic_bp > 140) reasons.push('high blood pressure');
    else if (vitals.systolic_bp < 90) reasons.push('low blood pressure (hypotension)');
    if (vitals.respiratory_rate > 20) reasons.push('elevated respiratory rate');
    if (vitals.oxygen_saturation < 95) reasons.push('low oxygen saturation');
    if (vitals.temperature > 38.0) reasons.push('fever');
    
    if (reasons.length === 0) return 'Vital signs within normal range. Routine monitoring recommended.';
    const riskLevel = risk.risk_flag ? 'requires immediate attention' : 'requires monitoring';
    return `Patient presents with ${reasons.join(', ')}. Current condition ${riskLevel}. Risk score: ${risk.risk_score.toFixed(1)}.`;
  };

  const filteredPatients = (searchId 
    ? patients.filter(p => p.id.toLowerCase().includes(searchId.toLowerCase()))
    : patients
  ).sort((a, b) => a.priority - b.priority);

  const handleOverlayClick = (e) => { if (e.target.classList.contains('popup-overlay')) onClose(); };

  const handleRowClick = async (patient) => {
    setSelectedPatient(patient);
    setExplanationData(null);
    setExplanationLoading(true);
    
    try {
      const explanation = await getPatientExplanation(patient.id);
      setExplanationData(explanation);
    } catch (err) {
      console.warn('Could not fetch LLM explanation:', err);
      setExplanationData(null);
    } finally {
      setExplanationLoading(false);
    }
  };

  const closeExplainability = (e) => {
    if (e.target.classList.contains('explainability-overlay')) {
      setSelectedPatient(null);
      setExplanationData(null);
    }
  };

  return (
    <div className="popup-overlay" onClick={handleOverlayClick}>
      <div className="popup-content">
        <h2 className="popup-title">Patient Prioritization</h2>
        
        <div className="search-container">
          <label className="search-label">Search Patient ID</label>
          <input type="text" className="search-input" placeholder="Enter Patient ID..." value={searchId} onChange={(e) => setSearchId(e.target.value)} />
        </div>

        <div className="table-container">
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center' }}>Loading patient data...</div>
          ) : (
            <table className="patient-table">
              <thead><tr><th>Patient ID</th><th>Deterioration Risk</th><th>Severity</th><th>Priority</th><th>Confidence Score</th></tr></thead>
              <tbody>
                {filteredPatients.length === 0 ? (
                  <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>No patients found.</td></tr>
                ) : (
                  filteredPatients.map((patient) => (
                    <tr key={patient.id} onClick={() => handleRowClick(patient)} className={patient.deteriorationRisk === 'High' ? 'high-priority' : ''}>
                      <td>{patient.id}</td>
                      <td className={`risk-${patient.deteriorationRisk.toLowerCase()}`}>{patient.deteriorationRisk}</td>
                      <td className={`severity-${patient.severity.toLowerCase()}`}>{patient.severity}</td>
                      <td>{patient.priority}</td>
                      <td>{patient.confidenceScore}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>

        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      {selectedPatient && (
        <div className="explainability-overlay" onClick={closeExplainability}>
          <div className="explainability-popup">
            <h3>Patient Risk Explainability {explanationData?.llm_generated && <span className="llm-badge">AI Generated</span>}</h3>
            <p><strong>Patient ID:</strong> {selectedPatient.id}</p>
            <p><strong>Risk Score:</strong> {selectedPatient.riskScore?.toFixed(1) || 'N/A'}/100</p>
            <p><strong>Risk Category:</strong> {selectedPatient.riskCategory || selectedPatient.deteriorationRisk}</p>
            <p><strong>Severity:</strong> {selectedPatient.severity}</p>
            <p><strong>Priority:</strong> {selectedPatient.priority}</p>
            
            {selectedPatient.vitals && (
              <>
                <p><strong>Current Vitals:</strong></p>
                <div className="vitals-summary">
                  <span>HR: {Math.round(selectedPatient.vitals.heart_rate)} bpm</span>
                  <span>BP: {Math.round(selectedPatient.vitals.systolic_bp)}/{Math.round(selectedPatient.vitals.diastolic_bp)}</span>
                  <span>SpO₂: {Math.round(selectedPatient.vitals.oxygen_saturation)}%</span>
                  <span>RR: {Math.round(selectedPatient.vitals.respiratory_rate)}/min</span>
                  <span>Temp: {selectedPatient.vitals.temperature.toFixed(1)}°C</span>
                </div>
              </>
            )}
            
            {explanationData?.contributing_factors && explanationData.contributing_factors.length > 0 && (
              <>
                <p><strong>Contributing Factors:</strong></p>
                <ul className="contributing-factors">
                  {explanationData.contributing_factors.map((factor, idx) => <li key={idx}>{factor}</li>)}
                </ul>
              </>
            )}
            
            <p><strong>Reasoning:</strong></p>
            <p className={`explainability-text ${explanationLoading ? 'loading' : ''}`}>
              {explanationLoading ? 'Generating AI explanation...' : (explanationData?.explanation || selectedPatient.explainability)}
            </p>
            
            <button className="close-explainability-btn" onClick={() => { setSelectedPatient(null); setExplanationData(null); }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Frame2_1;
