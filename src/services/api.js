/**
 * API Service for VERIQ Hospital Management System
 * 
 * This service provides functions to interact with the Patient Risk Classifier Backend API.
 * It replaces the mock data in the frontend components with real database data.
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Helper function to handle API responses
 */
async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new Error(error.message || `HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Check if the API is healthy
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}

/**
 * Register a new patient
 * @param {Object} patientData - Patient registration data
 */
export async function registerPatient(patientData) {
  try {
    const response = await fetch(`${API_BASE_URL}/patients`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(patientData),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to register patient:', error);
    throw error;
  }
}

/**
 * Get patient status by ID
 * @param {string} patientId - Patient ID
 */
export async function getPatientStatus(patientId) {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/${patientId}`);
    return await handleResponse(response);
  } catch (error) {
    console.error(`Failed to get patient ${patientId}:`, error);
    throw error;
  }
}

/**
 * Update patient vital signs
 * @param {string} patientId - Patient ID
 * @param {Object} vitals - Vital signs data
 */
export async function updateVitalSigns(patientId, vitals) {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/${patientId}/vitals`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(vitals),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Failed to update vitals for ${patientId}:`, error);
    throw error;
  }
}

/**
 * Get high-risk patients
 * @param {Object} options - Query options
 * @param {number} options.minRiskScore - Minimum risk score filter
 * @param {number} options.limit - Maximum number of results
 */
export async function getHighRiskPatients(options = {}) {
  try {
    const params = new URLSearchParams();
    if (options.minRiskScore !== undefined) {
      params.append('min_risk_score', options.minRiskScore);
    }
    if (options.limit !== undefined) {
      params.append('limit', options.limit);
    }
    
    const url = `${API_BASE_URL}/patients/high-risk${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get high-risk patients:', error);
    throw error;
  }
}

/**
 * Get patient history
 * @param {string} patientId - Patient ID
 * @param {Object} options - Query options
 * @param {string} options.startTime - Start time (ISO format)
 * @param {string} options.endTime - End time (ISO format)
 * @param {number} options.limit - Maximum number of data points
 */
export async function getPatientHistory(patientId, options = {}) {
  try {
    const params = new URLSearchParams();
    if (options.startTime) {
      params.append('start_time', options.startTime);
    }
    if (options.endTime) {
      params.append('end_time', options.endTime);
    }
    if (options.limit !== undefined) {
      params.append('limit', options.limit);
    }
    
    const url = `${API_BASE_URL}/patients/${patientId}/history${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);
    return await handleResponse(response);
  } catch (error) {
    console.error(`Failed to get history for ${patientId}:`, error);
    throw error;
  }
}

/**
 * Get AI-generated risk explanation for a patient
 * @param {string} patientId - Patient ID
 * @returns {Object} - Risk explanation with LLM-generated text
 */
export async function getPatientExplanation(patientId) {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/${patientId}/explanation`);
    return await handleResponse(response);
  } catch (error) {
    console.error(`Failed to get explanation for ${patientId}:`, error);
    throw error;
  }
}

/**
 * Delete a patient and all associated records
 * @param {string} patientId - Patient ID to delete
 * @returns {Object} - Deletion result with counts of deleted records
 */
export async function deletePatient(patientId) {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/${patientId}`, {
      method: 'DELETE',
    });
    return await handleResponse(response);
  } catch (error) {
    console.error(`Failed to delete patient ${patientId}:`, error);
    throw error;
  }
}

/**
 * Get all patients with their latest status
 * This fetches high-risk patients and can be extended to fetch all patients
 */
export async function getAllPatients() {
  try {
    const response = await fetch(`${API_BASE_URL}/patients/all`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get all patients:', error);
    throw error;
  }
}

/**
 * Transform backend patient data to frontend format for Frame4 (Patient Log)
 * @param {Object} patientStatus - Patient status from API
 * @returns {Object} - Formatted patient log entry
 */
export function transformToPatientLog(patientStatus) {
  const vitals = patientStatus.current_vitals;
  const timestamp = new Date(vitals.timestamp);
  
  return {
    id: patientStatus.patient_id,
    time: timestamp.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    }),
    heartRate: Math.round(vitals.heart_rate),
    systolicBP: Math.round(vitals.systolic_bp),
    respiratoryRate: Math.round(vitals.respiratory_rate),
    oxygenSat: Math.round(vitals.oxygen_saturation),
    temperature: vitals.temperature.toFixed(1),
    arrivalMode: patientStatus.arrival_mode,
  };
}

/**
 * Transform backend patient data to frontend format for Frame2_1 (Patient Prioritization)
 * @param {Object} patientStatus - Patient status from API
 * @param {number} waitTimeMinutes - Calculated wait time in minutes
 * @returns {Object} - Formatted patient prioritization entry
 */
export function transformToPrioritization(patientStatus, waitTimeMinutes = 30) {
  const risk = patientStatus.current_risk;
  
  // Determine deterioration risk based on risk score
  let deteriorationRisk = 'Low';
  let severity = 'Minor';
  let priority = 7;
  
  if (risk.risk_score >= 70) {
    deteriorationRisk = 'High';
    severity = 'Critical';
    priority = 1;
  } else if (risk.risk_score >= 40) {
    deteriorationRisk = 'Medium';
    severity = 'Moderate';
    priority = 4;
  }
  
  // Calculate confidence score (simulated based on risk score consistency)
  const confidenceScore = Math.min(95, Math.max(75, 80 + (risk.risk_score / 10)));
  
  return {
    id: patientStatus.patient_id,
    deteriorationRisk,
    severity,
    waitTime: `${waitTimeMinutes} min`,
    priority,
    confidenceScore: `${Math.round(confidenceScore)}%`,
    explainability: generateExplainability(patientStatus),
  };
}

/**
 * Generate explainability text based on patient vitals
 * @param {Object} patientStatus - Patient status from API
 * @returns {string} - Explainability text
 */
function generateExplainability(patientStatus) {
  const vitals = patientStatus.current_vitals;
  const risk = patientStatus.current_risk;
  const reasons = [];
  
  // Check heart rate
  if (vitals.heart_rate > 100) {
    reasons.push('elevated heart rate (tachycardia)');
  } else if (vitals.heart_rate < 60) {
    reasons.push('low heart rate (bradycardia)');
  }
  
  // Check blood pressure
  if (vitals.systolic_bp > 140) {
    reasons.push('high blood pressure');
  } else if (vitals.systolic_bp < 90) {
    reasons.push('low blood pressure (hypotension)');
  }
  
  // Check respiratory rate
  if (vitals.respiratory_rate > 20) {
    reasons.push('elevated respiratory rate');
  }
  
  // Check oxygen saturation
  if (vitals.oxygen_saturation < 95) {
    reasons.push('low oxygen saturation');
  }
  
  // Check temperature
  if (vitals.temperature > 38.0) {
    reasons.push('fever');
  }
  
  if (reasons.length === 0) {
    return 'Vital signs within normal range. Routine monitoring recommended.';
  }
  
  const riskLevel = risk.risk_flag ? 'requires immediate attention' : 'requires monitoring';
  return `Patient presents with ${reasons.join(', ')}. Current condition ${riskLevel}. Risk score: ${risk.risk_score.toFixed(1)}.`;
}

/**
 * Transform history data to frontend format
 * @param {Object} historyResponse - History response from API
 * @returns {Array} - Array of formatted log entries
 */
export function transformHistoryToLogs(historyResponse) {
  return historyResponse.data_points.map(point => {
    const vitals = point.vitals;
    const timestamp = new Date(vitals.timestamp);
    
    return {
      id: historyResponse.patient_id,
      time: timestamp.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
      }),
      heartRate: Math.round(vitals.heart_rate),
      systolicBP: Math.round(vitals.systolic_bp),
      respiratoryRate: Math.round(vitals.respiratory_rate),
      oxygenSat: Math.round(vitals.oxygen_saturation),
      temperature: vitals.temperature.toFixed(1),
      arrivalMode: 'N/A', // History doesn't include arrival mode per reading
      riskScore: point.risk_assessment.risk_score,
      riskCategory: point.risk_assessment.risk_category,
    };
  });
}

/**
 * Fetch all patient logs for Frame4
 * This fetches history for multiple patients and combines them
 * @param {Array} patientIds - Array of patient IDs to fetch
 * @param {number} limit - Limit per patient
 */
export async function fetchAllPatientLogs(patientIds = [], limit = 10) {
  try {
    const allLogs = [];
    
    for (const patientId of patientIds) {
      try {
        const history = await getPatientHistory(patientId, { limit });
        const logs = transformHistoryToLogs(history);
        
        // Add arrival mode from patient status
        const status = await getPatientStatus(patientId);
        logs.forEach(log => {
          log.arrivalMode = status.arrival_mode;
        });
        
        allLogs.push(...logs);
      } catch (error) {
        console.warn(`Could not fetch logs for ${patientId}:`, error);
      }
    }
    
    // Sort by time (most recent first)
    return allLogs.sort((a, b) => {
      const timeA = new Date(`1970/01/01 ${a.time}`);
      const timeB = new Date(`1970/01/01 ${b.time}`);
      return timeB - timeA;
    });
  } catch (error) {
    console.error('Failed to fetch patient logs:', error);
    throw error;
  }
}

export default {
  checkHealth,
  registerPatient,
  getPatientStatus,
  updateVitalSigns,
  getHighRiskPatients,
  getPatientHistory,
  getAllPatients,
  deletePatient,
  transformToPatientLog,
  transformToPrioritization,
  transformHistoryToLogs,
  fetchAllPatientLogs,
};


// ============================================
// ICU API Functions
// ============================================

const LOAD_PREDICTION_URL = 'http://localhost:5001';

/**
 * Get all patients currently in ICU
 */
export async function getICUPatients() {
  try {
    const response = await fetch(`${API_BASE_URL}/icu/patients`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get ICU patients:', error);
    throw error;
  }
}

/**
 * Get current ICU capacity metrics
 */
export async function getICUCapacity() {
  try {
    const response = await fetch(`${API_BASE_URL}/icu/capacity`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get ICU capacity:', error);
    throw error;
  }
}

/**
 * Get ICU occupancy history for load prediction
 * @param {number} hours - Number of hours of history to retrieve
 */
export async function getICUOccupancyHistory(hours = 24) {
  try {
    const response = await fetch(`${API_BASE_URL}/icu/occupancy-history?hours=${hours}`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get ICU occupancy history:', error);
    throw error;
  }
}

/**
 * Admit a patient to ICU
 * @param {Object} data - Admission data
 */
export async function admitToICU(data) {
  try {
    const response = await fetch(`${API_BASE_URL}/icu/admit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to admit patient to ICU:', error);
    throw error;
  }
}

/**
 * Discharge a patient from ICU
 * @param {string} patientId - Patient ID to discharge
 */
export async function dischargeFromICU(patientId) {
  try {
    const response = await fetch(`${API_BASE_URL}/icu/discharge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId }),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to discharge patient from ICU:', error);
    throw error;
  }
}

/**
 * Get ICU load forecast for next 6 hours
 * @param {Array} recentData - Recent occupancy data [{timestamp, count}, ...]
 */
export async function getICULoadForecast(recentData) {
  try {
    const response = await fetch(`${LOAD_PREDICTION_URL}/api/load-prediction/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recent_data: recentData }),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get ICU load forecast:', error);
    throw error;
  }
}


// ============================================
// Simulation API Functions
// ============================================

/**
 * Start the time simulation
 * @param {number} hoursAfterFirstPatient - Hours after first patient to start simulation
 */
export async function startSimulation(hoursAfterFirstPatient = 3) {
  try {
    const response = await fetch(`${API_BASE_URL}/simulation/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hours_after_first_patient: hoursAfterFirstPatient }),
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to start simulation:', error);
    throw error;
  }
}

/**
 * Stop the time simulation
 */
export async function stopSimulation() {
  try {
    const response = await fetch(`${API_BASE_URL}/simulation/stop`, {
      method: 'POST',
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to stop simulation:', error);
    throw error;
  }
}

/**
 * Get current simulation time
 */
export async function getSimulationTime() {
  try {
    const response = await fetch(`${API_BASE_URL}/simulation/time`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get simulation time:', error);
    throw error;
  }
}

/**
 * Trigger a simulation tick (generates new vitals for all patients)
 */
export async function simulationTick() {
  try {
    const response = await fetch(`${API_BASE_URL}/simulation/tick`, {
      method: 'POST',
    });
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to trigger simulation tick:', error);
    throw error;
  }
}

/**
 * Get simulation status
 */
export async function getSimulationStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/simulation/status`);
    return await handleResponse(response);
  } catch (error) {
    console.error('Failed to get simulation status:', error);
    throw error;
  }
}
