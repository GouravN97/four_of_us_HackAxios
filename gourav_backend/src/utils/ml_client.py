"""
ML model client for risk assessment integration.
Provides interface to the pre-trained risk assessment model.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.utils.error_handling import (
    handle_service_error,
    error_context,
    monitor_external_service,
    log_performance_warning,
    ErrorCategory,
    ErrorSeverity,
    global_error_handler
)

logger = logging.getLogger(__name__)


class MLModelError(Exception):
    """Base exception for ML model errors."""
    pass


class MLModelTimeoutError(MLModelError):
    """Raised when ML model request times out."""
    pass


class MLModelValidationError(MLModelError):
    """Raised when ML model input validation fails."""
    pass


class MLModelResponseError(MLModelError):
    """Raised when ML model response is invalid."""
    pass


class RiskModelClient:
    """Client for interfacing with the risk assessment ML model."""
    
    def __init__(self, model_endpoint: Optional[str] = None, timeout_seconds: int = 5,
                 model_version: str = "v1.0.0"):
        """
        Initialize ML model client.
        
        Args:
            model_endpoint: URL endpoint for the ML model (None for mock mode)
            timeout_seconds: Request timeout in seconds
            model_version: Version of the ML model
        """
        self.model_endpoint = model_endpoint
        self.timeout_seconds = timeout_seconds
        self.model_version = model_version
        self.is_mock_mode = model_endpoint is None
        
        if self.is_mock_mode:
            logger.info("RiskModelClient initialized in mock mode")
        else:
            logger.info(f"RiskModelClient initialized with endpoint: {model_endpoint}")
    
    @monitor_external_service("ml_risk_model", timeout_seconds=5.0, retry_attempts=1)
    def predict_risk(self, heart_rate: float, systolic_bp: float, diastolic_bp: float,
                    respiratory_rate: float, oxygen_saturation: float, temperature: float,
                    arrival_mode: str, acuity_level: int) -> Tuple[float, bool, int]:
        """
        Get risk prediction from the ML model.
        
        Args:
            heart_rate: Heart rate in bpm
            systolic_bp: Systolic blood pressure in mmHg
            diastolic_bp: Diastolic blood pressure in mmHg
            respiratory_rate: Respiratory rate in breaths/min
            oxygen_saturation: Oxygen saturation percentage
            temperature: Body temperature in Celsius
            arrival_mode: Patient arrival mode ("Ambulance" or "Walk-in")
            acuity_level: Clinical severity rating (1-5)
            
        Returns:
            Tuple of (risk_score, risk_flag, processing_time_ms)
            
        Raises:
            MLModelValidationError: If input validation fails
            MLModelTimeoutError: If request times out
            MLModelResponseError: If response is invalid
            MLModelError: For other model errors
        """
        start_time = time.time()
        
        with error_context(
            "ml_model_risk_prediction",
            ErrorCategory.EXTERNAL_SERVICE,
            context={
                "model_version": self.model_version,
                "is_mock_mode": self.is_mock_mode,
                "timeout_seconds": self.timeout_seconds
            }
        ):
            # Validate inputs
            self._validate_inputs(
                heart_rate, systolic_bp, diastolic_bp, respiratory_rate,
                oxygen_saturation, temperature, arrival_mode, acuity_level
            )
            
            # Prepare model input
            model_input = {
                "heart_rate": heart_rate,
                "systolic_bp": systolic_bp,
                "diastolic_bp": diastolic_bp,
                "respiratory_rate": respiratory_rate,
                "oxygen_saturation": oxygen_saturation,
                "temperature": temperature,
                "arrival_mode": arrival_mode,
                "acuity_level": acuity_level
            }
            
            logger.debug(f"Sending risk prediction request: {model_input}")
            
            # Get prediction (mock or real)
            if self.is_mock_mode:
                risk_score, risk_flag = self._mock_predict(model_input)
            else:
                risk_score, risk_flag = self._real_predict(model_input)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Validate response
            self._validate_response(risk_score, risk_flag)
            
            # Log performance warning if prediction took too long
            log_performance_warning(
                "ml_model_prediction",
                processing_time_ms / 1000.0,  # Convert to seconds
                self.timeout_seconds,
                {"model_version": self.model_version, "is_mock": self.is_mock_mode}
            )
            
            logger.debug(f"Risk prediction completed: score={risk_score}, flag={risk_flag}, "
                        f"time={processing_time_ms}ms")
            
            return risk_score, risk_flag, processing_time_ms
    
    def _validate_inputs(self, heart_rate: float, systolic_bp: float, diastolic_bp: float,
                        respiratory_rate: float, oxygen_saturation: float, temperature: float,
                        arrival_mode: str, acuity_level: int) -> None:
        """
        Validate ML model inputs according to expected ranges.
        
        Args:
            heart_rate: Heart rate in bpm
            systolic_bp: Systolic blood pressure in mmHg
            diastolic_bp: Diastolic blood pressure in mmHg
            respiratory_rate: Respiratory rate in breaths/min
            oxygen_saturation: Oxygen saturation percentage
            temperature: Body temperature in Celsius
            arrival_mode: Patient arrival mode
            acuity_level: Clinical severity rating
            
        Raises:
            MLModelValidationError: If any input is invalid
        """
        errors = []
        
        # Validate vital signs ranges (extended ranges for ML model)
        if not (30 <= heart_rate <= 200):
            errors.append(f"Heart rate must be between 30-200 bpm, got {heart_rate}")
        
        if not (50 <= systolic_bp <= 300):
            errors.append(f"Systolic BP must be between 50-300 mmHg, got {systolic_bp}")
        
        if not (20 <= diastolic_bp <= 200):
            errors.append(f"Diastolic BP must be between 20-200 mmHg, got {diastolic_bp}")
        
        if not (5 <= respiratory_rate <= 60):
            errors.append(f"Respiratory rate must be between 5-60 breaths/min, got {respiratory_rate}")
        
        if not (50 <= oxygen_saturation <= 100):
            errors.append(f"Oxygen saturation must be between 50-100%, got {oxygen_saturation}")
        
        if not (30 <= temperature <= 45):
            errors.append(f"Temperature must be between 30-45°C, got {temperature}")
        
        # Validate blood pressure relationship
        if diastolic_bp >= systolic_bp:
            errors.append(f"Diastolic BP ({diastolic_bp}) must be less than systolic BP ({systolic_bp})")
        
        # Validate arrival mode
        if arrival_mode not in ["Ambulance", "Walk-in"]:
            errors.append(f"Arrival mode must be 'Ambulance' or 'Walk-in', got '{arrival_mode}'")
        
        # Validate acuity level
        if not (1 <= acuity_level <= 5):
            errors.append(f"Acuity level must be between 1-5, got {acuity_level}")
        
        if errors:
            error_message = "ML model input validation failed: " + "; ".join(errors)
            logger.error(error_message)
            raise MLModelValidationError(error_message)
    
    def _validate_response(self, risk_score: float, risk_flag: bool) -> None:
        """
        Validate ML model response.
        
        Args:
            risk_score: Risk score from model
            risk_flag: Risk flag from model
            
        Raises:
            MLModelResponseError: If response is invalid
        """
        if not isinstance(risk_score, (int, float)):
            raise MLModelResponseError(f"Risk score must be numeric, got {type(risk_score)}")
        
        if not (0.0 <= risk_score <= 1.0):
            raise MLModelResponseError(f"Risk score must be between 0.0-1.0, got {risk_score}")
        
        if not isinstance(risk_flag, bool):
            raise MLModelResponseError(f"Risk flag must be boolean, got {type(risk_flag)}")
    
    def _mock_predict(self, model_input: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Mock prediction for testing and development.
        
        Args:
            model_input: Model input dictionary
            
        Returns:
            Tuple of (risk_score, risk_flag)
        """
        # Simple mock logic based on vital signs
        heart_rate = model_input["heart_rate"]
        systolic_bp = model_input["systolic_bp"]
        oxygen_saturation = model_input["oxygen_saturation"]
        temperature = model_input["temperature"]
        acuity_level = model_input["acuity_level"]
        arrival_mode = model_input["arrival_mode"]
        
        # Calculate mock risk score based on abnormal values
        risk_factors = 0
        
        # High heart rate
        if heart_rate > 100:
            risk_factors += 1
        elif heart_rate > 120:
            risk_factors += 2
        
        # High blood pressure
        if systolic_bp > 140:
            risk_factors += 1
        elif systolic_bp > 180:
            risk_factors += 2
        
        # Low oxygen saturation
        if oxygen_saturation < 95:
            risk_factors += 1
        elif oxygen_saturation < 90:
            risk_factors += 2
        
        # Abnormal temperature
        if temperature > 38.0 or temperature < 36.0:
            risk_factors += 1
        elif temperature > 39.0 or temperature < 35.0:
            risk_factors += 2
        
        # High acuity level
        if acuity_level >= 4:
            risk_factors += 1
        elif acuity_level == 5:
            risk_factors += 2
        
        # Ambulance arrival (potentially more serious)
        if arrival_mode == "Ambulance":
            risk_factors += 1
        
        # Convert risk factors to score (0.0-1.0)
        max_risk_factors = 10  # Maximum possible risk factors
        risk_score = min(risk_factors / max_risk_factors, 1.0)
        
        # Risk flag if score > 0.5 or high acuity with multiple factors
        risk_flag = risk_score > 0.5 or (acuity_level >= 4 and risk_factors >= 3)
        
        # Add some randomness to make it more realistic
        import random
        risk_score += random.uniform(-0.1, 0.1)
        risk_score = max(0.0, min(1.0, risk_score))  # Clamp to valid range
        
        # Simulate processing delay
        time.sleep(0.01)  # 10ms delay
        
        logger.debug(f"Mock prediction: risk_factors={risk_factors}, score={risk_score}, flag={risk_flag}")
        
        return risk_score, risk_flag
    
    def _real_predict(self, model_input: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Real prediction using HTTP API call to ML model.
        
        Args:
            model_input: Model input dictionary
            
        Returns:
            Tuple of (risk_score, risk_flag)
            
        Raises:
            MLModelTimeoutError: If request times out
            MLModelResponseError: If response is invalid
            MLModelError: For other API errors
        """
        try:
            import requests
            
            # Prepare request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Make API call with timeout
            response = requests.post(
                self.model_endpoint,
                json=model_input,
                headers=headers,
                timeout=self.timeout_seconds
            )
            
            # Check response status
            if response.status_code != 200:
                raise MLModelError(f"ML model API returned status {response.status_code}: {response.text}")
            
            # Parse response
            try:
                result = response.json()
            except ValueError as e:
                raise MLModelResponseError(f"Invalid JSON response from ML model: {e}")
            
            # Extract risk score and flag
            if "risk_score" not in result:
                raise MLModelResponseError("Missing 'risk_score' in ML model response")
            
            if "risk_flag" not in result:
                raise MLModelResponseError("Missing 'risk_flag' in ML model response")
            
            risk_score = result["risk_score"]
            risk_flag = result["risk_flag"]
            
            return risk_score, risk_flag
            
        except requests.exceptions.Timeout:
            raise MLModelTimeoutError(f"ML model request timed out after {self.timeout_seconds} seconds")
        except requests.exceptions.RequestException as e:
            raise MLModelError(f"ML model request failed: {str(e)}")
        except ImportError:
            # Fallback to mock if requests is not available
            logger.warning("requests library not available, falling back to mock prediction")
            return self._mock_predict(model_input)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the ML model is healthy and responsive.
        
        Returns:
            Dictionary with health status information
        """
        if self.is_mock_mode:
            return {
                "status": "healthy",
                "mode": "mock",
                "model_version": self.model_version,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            with error_context(
                "ml_model_health_check",
                ErrorCategory.EXTERNAL_SERVICE,
                context={"model_version": self.model_version}
            ):
                # Try a simple prediction with normal values
                start_time = time.time()
                risk_score, risk_flag, _ = self.predict_risk(
                    heart_rate=72.0,
                    systolic_bp=120.0,
                    diastolic_bp=80.0,
                    respiratory_rate=16.0,
                    oxygen_saturation=98.0,
                    temperature=36.5,
                    arrival_mode="Walk-in",
                    acuity_level=2
                )
                response_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "status": "healthy",
                    "mode": "real",
                    "model_version": self.model_version,
                    "response_time_ms": response_time_ms,
                    "test_prediction": {
                        "risk_score": risk_score,
                        "risk_flag": risk_flag
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            # Handle health check errors gracefully
            global_error_handler.handle_error(
                exception=e,
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "health_check", "model_version": self.model_version},
                user_message="ML model health check failed"
            )
            
            return {
                "status": "unhealthy",
                "mode": "real",
                "model_version": self.model_version,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }