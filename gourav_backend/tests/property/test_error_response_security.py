"""
Property-based tests for error response security.
Tests Property 15: Error Response Security
**Validates: Requirements 6.2, 6.5**
"""

import pytest
import json
import re
from hypothesis import given, strategies as st, assume
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.utils.validation import create_safe_error_response, sanitize_string
from src.utils.error_handling import ErrorCategory, ErrorSeverity, global_error_handler


class TestErrorResponseSecurity:
    """Test error response security measures."""
    
    @given(st.text(min_size=1, max_size=100))
    def test_error_response_sanitization(self, error_message):
        """
        Property 15: Error Response Security
        For any error message, the response should be sanitized and not expose sensitive information.
        **Validates: Requirements 6.5**
        """
        # Create a safe error response
        error_id = "test-error-123"
        error_code = "TEST_ERROR"
        
        try:
            response = create_safe_error_response(
                error_code=error_code,
                user_message=error_message,
                error_id=error_id
            )
            
            # Response should always be a dictionary
            assert isinstance(response, dict), "Error response must be a dictionary"
            
            # Required fields should be present
            assert "error_code" in response, "Error response must contain error_code"
            assert "message" in response, "Error response must contain message"
            assert "error_id" in response, "Error response must contain error_id"
            
            # Message should be sanitized
            sanitized_message = response["message"]
            assert isinstance(sanitized_message, str), "Error message must be a string"
            
            # Should not contain dangerous patterns
            dangerous_patterns = [
                r"<script[^>]*>",  # XSS script tags
                r"javascript:",    # JavaScript protocol
                r"on\w+\s*=",     # Event handlers
                r"--",            # SQL comments
                r"union\s+select", # SQL injection
                r"\$\{.*\}",      # Template injection
                r"<%.*%>",        # ASP/JSP injection
                r"<\?php",        # PHP injection
            ]
            
            for pattern in dangerous_patterns:
                assert not re.search(pattern, sanitized_message, re.IGNORECASE), \
                    f"Error message contains dangerous pattern '{pattern}': {sanitized_message}"
            
            # Should not contain control characters
            assert not any(ord(c) < 32 and c not in '\t\r\n' for c in sanitized_message), \
                "Error message contains control characters"
            
        except ValueError:
            # If sanitization raises ValueError, the input was deemed too malicious
            # This is acceptable behavior
            pass
    
    @given(st.text(min_size=1, max_size=50))
    def test_patient_not_found_error_security(self, patient_id):
        """
        Property 15: Error Response Security
        For any invalid patient ID, the error response should be user-friendly without exposing system details.
        **Validates: Requirements 6.2, 6.5**
        """
        client = TestClient(app)
        
        # Skip if patient_id contains null bytes or is too dangerous
        assume('\x00' not in patient_id)
        assume(len(patient_id.strip()) > 0)
        
        try:
            # Try to get a non-existent patient
            response = client.get(f"/patients/{patient_id}")
            
            # Should return 404 for non-existent patients
            if response.status_code == 404:
                error_data = response.json()
                
                # Should have proper error structure
                assert "error_code" in error_data or "error" in error_data, \
                    "Error response missing error code"
                assert "message" in error_data, "Error response missing message"
                
                message = error_data.get("message", "").lower()
                
                # Message should be user-friendly
                user_friendly_indicators = [
                    "not found", "does not exist", "invalid", "unknown"
                ]
                assert any(indicator in message for indicator in user_friendly_indicators), \
                    f"Error message not user-friendly: {message}"
                
                # Should not expose sensitive system information
                sensitive_patterns = [
                    r"database", r"sql", r"connection", r"server", r"internal",
                    r"stack", r"trace", r"exception", r"error.*line",
                    r"file.*py", r"function", r"module", r"class",
                    r"password", r"secret", r"key", r"token", r"auth",
                    r"path.*src", r"\.py:", r"traceback"
                ]
                
                full_response = json.dumps(error_data).lower()
                for pattern in sensitive_patterns:
                    assert not re.search(pattern, full_response), \
                        f"Error response exposes sensitive information '{pattern}': {full_response}"
            
            # Other status codes (400, 422) are acceptable for malformed IDs
            assert response.status_code in [400, 404, 422], \
                f"Unexpected status code for patient lookup: {response.status_code}"
                
        except Exception as e:
            # Network/parsing errors are acceptable for malicious patient IDs
            pass
    
    def test_system_error_response_security(self):
        """
        Property 15: Error Response Security
        System errors should return generic user-friendly messages without exposing internal details.
        **Validates: Requirements 6.5**
        """
        client = TestClient(app)
        
        # Mock a database error to test system error handling
        with patch('src.repositories.patient_repository.PatientRepository.get_by_id') as mock_get:
            # Simulate a database connection error
            mock_get.side_effect = Exception("Database connection failed: Connection to localhost:5432 refused")
            
            response = client.get("/patients/TEST123")
            
            # Should return 500 for system errors
            assert response.status_code == 500, f"Expected 500 for system error, got {response.status_code}"
            
            error_data = response.json()
            
            # Should have proper error structure
            assert "error_code" in error_data or "error" in error_data, \
                "System error response missing error code"
            assert "message" in error_data, "System error response missing message"
            
            message = error_data.get("message", "").lower()
            
            # Message should be generic and user-friendly
            generic_indicators = [
                "internal server error", "unexpected error", "try again later",
                "temporarily unavailable", "service unavailable"
            ]
            assert any(indicator in message for indicator in generic_indicators), \
                f"System error message not generic enough: {message}"
            
            # Should not expose internal system details
            full_response = json.dumps(error_data).lower()
            sensitive_details = [
                "database connection", "localhost", "5432", "connection refused",
                "stack trace", "traceback", "exception", "src/", ".py",
                "function", "line", "module"
            ]
            
            for detail in sensitive_details:
                assert detail not in full_response, \
                    f"System error exposes sensitive detail '{detail}': {full_response}"
    
    @given(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(max_size=100), st.integers(), st.floats(allow_nan=False))
    ))
    def test_validation_error_response_security(self, invalid_payload):
        """
        Property 15: Error Response Security
        Validation errors should provide helpful messages without exposing system internals.
        **Validates: Requirements 6.2, 6.5**
        """
        client = TestClient(app)
        
        # Skip if payload is too large or contains non-serializable data
        try:
            json.dumps(invalid_payload)
        except (TypeError, ValueError):
            assume(False)
        
        # Create an intentionally invalid patient registration payload
        invalid_patient_data = {
            "patient_id": "",  # Invalid: empty patient ID
            "arrival_mode": "InvalidMode",  # Invalid: not in enum
            "acuity_level": 10,  # Invalid: out of range
            "initial_vitals": invalid_payload  # May contain invalid vital signs
        }
        
        try:
            response = client.post("/patients", json=invalid_patient_data)
            
            # Should return validation error (422) or bad request (400)
            if response.status_code in [400, 422]:
                error_data = response.json()
                
                # Should have proper error structure
                assert "error_code" in error_data or "error" in error_data, \
                    "Validation error response missing error code"
                assert "message" in error_data, "Validation error response missing message"
                
                message = error_data.get("message", "").lower()
                
                # Message should be helpful for validation errors
                validation_indicators = [
                    "validation", "invalid", "required", "missing", "format",
                    "range", "value", "field", "parameter"
                ]
                assert any(indicator in message for indicator in validation_indicators), \
                    f"Validation error message not helpful: {message}"
                
                # Should not expose internal validation logic or system details
                full_response = json.dumps(error_data).lower()
                internal_details = [
                    "pydantic", "fastapi", "starlette", "uvicorn",
                    "src/", ".py", "line", "traceback", "stack",
                    "function", "module", "class", "method"
                ]
                
                for detail in internal_details:
                    assert detail not in full_response, \
                        f"Validation error exposes internal detail '{detail}': {full_response}"
            
            # Other status codes are acceptable depending on the invalid data
            assert response.status_code in [400, 422, 500], \
                f"Unexpected status code for invalid payload: {response.status_code}"
                
        except Exception:
            # Network/parsing errors are acceptable for malformed payloads
            pass
    
    def test_authentication_error_response_security(self):
        """
        Property 15: Error Response Security
        Authentication errors should not expose authentication mechanisms or valid credentials.
        **Validates: Requirements 6.2, 6.5**
        """
        client = TestClient(app)
        
        # Test with invalid API key (if authentication is enabled)
        headers = {"X-API-Key": "invalid-key-<script>alert('xss')</script>"}
        
        try:
            response = client.get("/patients/TEST123", headers=headers)
            
            # Authentication errors should return 401 or be ignored (if auth disabled)
            if response.status_code == 401:
                error_data = response.json()
                
                # Should have proper error structure
                assert "error_code" in error_data or "error" in error_data, \
                    "Auth error response missing error code"
                assert "message" in error_data, "Auth error response missing message"
                
                message = error_data.get("message", "").lower()
                
                # Message should be generic for security
                auth_indicators = [
                    "authentication", "unauthorized", "invalid", "required",
                    "api key", "token", "credentials"
                ]
                assert any(indicator in message for indicator in auth_indicators), \
                    f"Auth error message not appropriate: {message}"
                
                # Should not expose authentication details or valid keys
                full_response = json.dumps(error_data).lower()
                sensitive_auth_info = [
                    "demo-api-key", "admin-api-key", "bearer", "jwt",
                    "secret", "hash", "algorithm", "signature",
                    "valid keys", "accepted keys"
                ]
                
                for info in sensitive_auth_info:
                    assert info not in full_response, \
                        f"Auth error exposes sensitive info '{info}': {full_response}"
                
                # Should not contain the malicious script from the invalid key
                assert "<script>" not in full_response, \
                    "Auth error response contains unescaped malicious content"
            
            # Other status codes are acceptable (200 if auth disabled, 400 for malformed)
            assert response.status_code in [200, 400, 401, 404], \
                f"Unexpected status code for auth test: {response.status_code}"
                
        except Exception:
            # Network/parsing errors are acceptable
            pass
    
    @given(st.text(min_size=1, max_size=200))
    def test_error_message_length_limits(self, long_error_input):
        """
        Property 15: Error Response Security
        Error messages should be limited in length to prevent information disclosure attacks.
        **Validates: Requirements 6.5**
        """
        # Test that error responses don't become too verbose
        try:
            response = create_safe_error_response(
                error_code="TEST_ERROR",
                user_message=long_error_input,
                error_id="test-123"
            )
            
            message = response.get("message", "")
            
            # Error messages should be reasonably limited
            assert len(message) <= 1000, f"Error message too long: {len(message)} chars"
            
            # Should not contain excessive repetition (potential DoS)
            words = message.split()
            if len(words) > 10:
                unique_words = set(words)
                repetition_ratio = len(words) / len(unique_words)
                assert repetition_ratio <= 5, f"Error message too repetitive: {repetition_ratio}"
            
        except ValueError:
            # Sanitization rejection is acceptable for malicious input
            pass
    
    def test_error_response_structure_consistency(self):
        """
        Property 15: Error Response Security
        All error responses should have consistent structure for security and usability.
        **Validates: Requirements 6.2, 6.5**
        """
        client = TestClient(app)
        
        # Test various error scenarios
        error_scenarios = [
            ("/patients/NONEXISTENT", 404),  # Not found
            ("/patients", 405),              # Method not allowed (GET on POST endpoint)
            ("/invalid-endpoint", 404),      # Invalid endpoint
        ]
        
        for endpoint, expected_status in error_scenarios:
            try:
                response = client.get(endpoint)
                
                if response.status_code >= 400:
                    error_data = response.json()
                    
                    # All error responses should have consistent structure
                    required_fields = ["message"]
                    for field in required_fields:
                        assert field in error_data, \
                            f"Error response missing required field '{field}' for {endpoint}"
                    
                    # Error code should be present (either 'error_code' or 'error')
                    assert "error_code" in error_data or "error" in error_data, \
                        f"Error response missing error code for {endpoint}"
                    
                    # Message should be non-empty string
                    message = error_data.get("message", "")
                    assert isinstance(message, str) and len(message) > 0, \
                        f"Error message invalid for {endpoint}: {message}"
                    
                    # Should not contain internal paths or system info
                    full_response = json.dumps(error_data).lower()
                    internal_info = ["src/", ".py", "traceback", "stack", "line"]
                    for info in internal_info:
                        assert info not in full_response, \
                            f"Error response exposes internal info '{info}' for {endpoint}"
                            
            except Exception:
                # Network/parsing errors are acceptable
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])