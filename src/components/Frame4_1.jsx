import { useState } from 'react';
import './Frame4_1.css';

const Frame4_1 = ({ onClose, onAdd }) => {
  const [formData, setFormData] = useState({
    patientId: '',
    heartRate: '',
    systolicBP: '',
    respiratoryRate: '',
    oxygenSat: '',
    temperature: '',
    arrivalMode: '',
    time: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Connect to database to add patient
    const newPatient = {
      id: formData.patientId.toUpperCase(),
      heartRate: parseInt(formData.heartRate),
      systolicBP: parseInt(formData.systolicBP),
      respiratoryRate: parseInt(formData.respiratoryRate),
      oxygenSat: parseInt(formData.oxygenSat),
      temperature: parseFloat(formData.temperature),
      arrivalMode: formData.arrivalMode,
      time: formData.time
    };
    onAdd(newPatient);
  };

  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('add-patient-overlay')) {
      onClose();
    }
  };

  return (
    <div className="add-patient-overlay" onClick={handleOverlayClick}>
      <div className="add-patient-popup">
        <button className="close-btn" onClick={onClose}>×</button>
        <h2 className="popup-title">Adding New Patient</h2>
        
        <form onSubmit={handleSubmit} className="patient-form">
          <table className="form-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="field-label">Patient ID</td>
                <td>
                  <input
                    type="text"
                    name="patientId"
                    value={formData.patientId}
                    onChange={handleChange}
                    placeholder="e.g., P009"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Heart Rate</td>
                <td>
                  <input
                    type="number"
                    name="heartRate"
                    value={formData.heartRate}
                    onChange={handleChange}
                    placeholder="e.g., 72"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Systolic BP</td>
                <td>
                  <input
                    type="number"
                    name="systolicBP"
                    value={formData.systolicBP}
                    onChange={handleChange}
                    placeholder="e.g., 120"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Respiratory Rate</td>
                <td>
                  <input
                    type="number"
                    name="respiratoryRate"
                    value={formData.respiratoryRate}
                    onChange={handleChange}
                    placeholder="e.g., 16"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Oxygen Saturation</td>
                <td>
                  <input
                    type="number"
                    name="oxygenSat"
                    value={formData.oxygenSat}
                    onChange={handleChange}
                    placeholder="e.g., 98"
                    min="0"
                    max="100"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Temperature</td>
                <td>
                  <input
                    type="number"
                    name="temperature"
                    value={formData.temperature}
                    onChange={handleChange}
                    placeholder="e.g., 98.6"
                    step="0.1"
                    required
                  />
                </td>
              </tr>
              <tr>
                <td className="field-label">Arrival Mode</td>
                <td>
                  <select
                    name="arrivalMode"
                    value={formData.arrivalMode}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select</option>
                    <option value="Ambulance">Ambulance</option>
                    <option value="Walk-in">Walk-in</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td className="field-label">Time (HH:MM)</td>
                <td>
                  <input
                    type="text"
                    name="time"
                    value={formData.time}
                    onChange={handleChange}
                    placeholder="e.g., 09:30 AM"
                    required
                  />
                </td>
              </tr>
            </tbody>
          </table>

          <div className="form-actions">
            <button type="submit" className="add-btn">Add</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Frame4_1;
