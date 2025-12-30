import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const API_BASE_URL = 'http://localhost:8000';

const SimulationContext = createContext(null);

export const useSimulation = () => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};

export const SimulationProvider = ({ children }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [simulatedTime, setSimulatedTime] = useState(null);
  const [startSimTime, setStartSimTime] = useState(null);
  const [realStartTime, setRealStartTime] = useState(null);
  const [timeScale] = useState(5); // 5 min sim = 60 sec real -> 5x
  const [tickCount, setTickCount] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const tickIntervalRef = useRef(null);
  const timeUpdateRef = useRef(null);

  // Start simulation - called automatically on first dashboard load
  const startSimulation = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/simulation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start simulation');
      }
      
      const data = await response.json();
      const simStartTime = new Date(data.simulated_start_time);
      setStartSimTime(simStartTime);
      setSimulatedTime(simStartTime);
      setRealStartTime(Date.now());
      setIsRunning(true);
      setInitialized(true);
      setTickCount(0);
      
      console.log('Simulation started from latest DB data:', data);
      return data;
    } catch (error) {
      console.error('Failed to start simulation:', error);
      throw error;
    }
  }, []);

  // Stop simulation
  const stopSimulation = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/simulation/stop`, { method: 'POST' });
      setIsRunning(false);
      
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current);
        tickIntervalRef.current = null;
      }
      if (timeUpdateRef.current) {
        clearInterval(timeUpdateRef.current);
        timeUpdateRef.current = null;
      }
    } catch (error) {
      console.error('Failed to stop simulation:', error);
    }
  }, []);

  // Trigger a simulation tick (generates new vitals for all patients)
  const triggerTick = useCallback(async () => {
    if (!isRunning) return null;
    
    try {
      const response = await fetch(`${API_BASE_URL}/simulation/tick`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Tick failed');
      }
      
      const data = await response.json();
      if (data.simulated_time) {
        setSimulatedTime(new Date(data.simulated_time));
      }
      setTickCount(prev => prev + 1);
      return data;
    } catch (error) {
      console.error('Simulation tick failed:', error);
      return null;
    }
  }, [isRunning]);

  // Get current simulation status
  const getStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/simulation/status`);
      if (!response.ok) throw new Error('Failed to get status');
      const data = await response.json();
      
      // Sync state with backend
      if (data.is_running && !isRunning) {
        setIsRunning(true);
        setSimulatedTime(new Date(data.simulated_time));
        if (data.start_sim_time) {
          setStartSimTime(new Date(data.start_sim_time));
        }
      }
      
      return data;
    } catch (error) {
      console.error('Failed to get simulation status:', error);
      return null;
    }
  }, [isRunning]);

  // Calculate current simulated time based on real elapsed time
  const getCurrentSimTime = useCallback(() => {
    if (!isRunning || !startSimTime || !realStartTime) {
      return simulatedTime || new Date();
    }
    
    const realElapsedMs = Date.now() - realStartTime;
    const simElapsedMs = realElapsedMs * timeScale;
    return new Date(startSimTime.getTime() + simElapsedMs);
  }, [isRunning, startSimTime, realStartTime, timeScale, simulatedTime]);

  // Update simulated time locally (smooth updates between ticks)
  useEffect(() => {
    if (!isRunning || !startSimTime || !realStartTime) return;

    // Update time display every 100ms for smooth display
    timeUpdateRef.current = setInterval(() => {
      const newSimTime = getCurrentSimTime();
      setSimulatedTime(newSimTime);
    }, 100);

    return () => {
      if (timeUpdateRef.current) {
        clearInterval(timeUpdateRef.current);
      }
    };
  }, [isRunning, startSimTime, realStartTime, getCurrentSimTime]);

  // Auto-tick every 60 real seconds (= 30 simulated minutes)
  useEffect(() => {
    if (!isRunning) return;

    // Trigger tick every 60 seconds
    tickIntervalRef.current = setInterval(() => {
      triggerTick();
    }, 60000);

    // Initial tick after a short delay
    const initialTick = setTimeout(() => {
      triggerTick();
    }, 500);

    return () => {
      if (tickIntervalRef.current) {
        clearInterval(tickIntervalRef.current);
      }
      clearTimeout(initialTick);
    };
  }, [isRunning, triggerTick]);

  // Format simulated time for display
  const formatSimTime = useCallback((format = 'time') => {
    const time = simulatedTime || new Date();
    
    if (format === 'time') {
      return time.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } else if (format === 'datetime') {
      return time.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } else if (format === 'full') {
      return time.toISOString();
    }
    return time.toLocaleTimeString();
  }, [simulatedTime]);

  // Calculate time relative to simulated time (in minutes)
  const getRelativeTime = useCallback((timestamp) => {
    if (!simulatedTime || !timestamp) return 0;
    const ts = new Date(timestamp);
    return Math.round((simulatedTime - ts) / (1000 * 60)); // minutes
  }, [simulatedTime]);

  // Check if a timestamp is before current simulated time
  const isBeforeSimTime = useCallback((timestamp) => {
    if (!simulatedTime || !timestamp) return true;
    return new Date(timestamp) <= simulatedTime;
  }, [simulatedTime]);

  // Get data points that fall within a time window relative to simulated time
  const getDataInTimeWindow = useCallback((dataPoints, windowMinutes, timestampKey = 'timestamp') => {
    if (!simulatedTime || !dataPoints || dataPoints.length === 0) return [];
    
    const windowStart = new Date(simulatedTime.getTime() - windowMinutes * 60 * 1000);
    
    return dataPoints.filter(point => {
      const ts = new Date(point[timestampKey]);
      return ts >= windowStart && ts <= simulatedTime;
    });
  }, [simulatedTime]);

  // Generate time labels for charts based on simulated time
  const generateTimeLabels = useCallback((intervalMinutes, count, direction = 'past') => {
    if (!simulatedTime) return [];
    
    const labels = [];
    for (let i = 0; i < count; i++) {
      const offset = direction === 'past' ? -(count - 1 - i) : (i + 1);
      const time = new Date(simulatedTime.getTime() + offset * intervalMinutes * 60 * 1000);
      labels.push({
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
        timestamp: time.toISOString(),
        date: time
      });
    }
    return labels;
  }, [simulatedTime]);

  const value = {
    isRunning,
    simulatedTime,
    startSimTime,
    timeScale,
    tickCount,
    initialized,
    startSimulation,
    stopSimulation,
    triggerTick,
    getStatus,
    formatSimTime,
    getRelativeTime,
    isBeforeSimTime,
    getCurrentSimTime,
    getDataInTimeWindow,
    generateTimeLabels,
  };

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
};

export default SimulationContext;
