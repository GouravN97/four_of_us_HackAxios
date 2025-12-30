"""
Security utilities for authentication and authorization.
Implements Requirements 6.4, 6.5 for security measures.
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.error_handling import (
    ErrorCategory,
    ErrorSeverity,
    global_error_handler,
)
from src.utils.validation import validate_api_key_format, sanitize_for_logging, create_safe_error_response

logger = logging.getLogger(__name__)


# API Key storage (in production, use a secure database or secrets manager)
# This is a simple in-memory implementation for demo purposes
class APIKeyManager:
    """
    Manages API keys for authentication.
    
    Implements Requirement 6.4: Security measures including authentication.
    """
    
    def __init__(self):
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._revoked_keys: Set[str] = set()
        self._key_usage: Dict[str, List[datetime]] = {}
        
        # Initialize with a demo API key (in production, load from secure storage)
        self._initialize_demo_keys()
    
    def _initialize_demo_keys(self) -> None:
        """Initialize demo API keys for development/testing."""
        # Demo API key for testing (in production, generate securely)
        demo_key = os.environ.get("DEMO_API_KEY", "demo-api-key-12345678")
        self._api_keys[demo_key] = {
            "name": "Demo API Key",
            "created_at": datetime.utcnow(),
            "permissions": ["read", "write"],
            "rate_limit": 1000,  # requests per hour
            "is_active": True,
        }
        
        # Admin API key for system operations
        admin_key = os.environ.get("ADMIN_API_KEY", "admin-api-key-87654321")
        self._api_keys[admin_key] = {
            "name": "Admin API Key",
            "created_at": datetime.utcnow(),
            "permissions": ["read", "write", "admin"],
            "rate_limit": 10000,  # requests per hour
            "is_active": True,
        }
    
    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return its metadata.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Key metadata if valid, None otherwise
        """
        if not api_key or not validate_api_key_format(api_key):
            return None
        
        if api_key in self._revoked_keys:
            logger.warning(f"Attempted use of revoked API key: {sanitize_for_logging(api_key[:8])}...")
            return None
        
        key_data = self._api_keys.get(api_key)
        if not key_data or not key_data.get("is_active", False):
            return None
        
        return key_data
    
    def check_rate_limit(self, api_key: str) -> bool:
        """
        Check if API key has exceeded its rate limit.
        
        Args:
            api_key: API key to check
            
        Returns:
            True if within rate limit, False if exceeded
        """
        key_data = self._api_keys.get(api_key)
        if not key_data:
            return False
        
        rate_limit = key_data.get("rate_limit", 100)
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        # Get usage in the last hour
        if api_key not in self._key_usage:
            self._key_usage[api_key] = []
        
        # Clean old entries
        self._key_usage[api_key] = [
            t for t in self._key_usage[api_key] if t > one_hour_ago
        ]
        
        # Check limit
        if len(self._key_usage[api_key]) >= rate_limit:
            return False
        
        # Record this request
        self._key_usage[api_key].append(current_time)
        return True
    
    def has_permission(self, api_key: str, permission: str) -> bool:
        """
        Check if API key has a specific permission.
        
        Args:
            api_key: API key to check
            permission: Permission to verify
            
        Returns:
            True if key has permission
        """
        key_data = self._api_keys.get(api_key)
        if not key_data:
            return False
        
        permissions = key_data.get("permissions", [])
        return permission in permissions
    
    def revoke_key(self, api_key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if key was revoked
        """
        if api_key in self._api_keys:
            self._revoked_keys.add(api_key)
            self._api_keys[api_key]["is_active"] = False
            logger.info(f"API key revoked: {sanitize_for_logging(api_key[:8])}...")
            return True
        return False


# Global API key manager instance
api_key_manager = APIKeyManager()


class EnhancedAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for API key authentication with additional security features.
    
    Implements Requirement 6.4: Security measures including authentication.
    """
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/demo/info",
    }
    
    # Paths that require authentication (prefix matching)
    PROTECTED_PREFIXES = [
        "/patients",
        "/system",
    ]
    
    def __init__(self, app, require_auth: bool = False, enable_session_tracking: bool = True):
        """
        Initialize enhanced authentication middleware.
        
        Args:
            app: FastAPI application
            require_auth: If True, require authentication for protected paths
            enable_session_tracking: If True, track API key sessions for security
        """
        super().__init__(app)
        self.require_auth = require_auth
        self.enable_session_tracking = enable_session_tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # API key -> session info
        self.failed_attempts: Dict[str, List[datetime]] = {}  # IP -> failed attempt times
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def _is_ip_locked_out(self, client_ip: str) -> bool:
        """Check if IP is locked out due to too many failed attempts."""
        if client_ip not in self.failed_attempts:
            return False
        
        current_time = datetime.utcnow()
        cutoff_time = current_time - self.lockout_duration
        
        # Clean old attempts
        self.failed_attempts[client_ip] = [
            attempt for attempt in self.failed_attempts[client_ip]
            if attempt > cutoff_time
        ]
        
        return len(self.failed_attempts[client_ip]) >= self.max_failed_attempts
    
    def _record_failed_attempt(self, client_ip: str) -> None:
        """Record a failed authentication attempt."""
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []
        
        self.failed_attempts[client_ip].append(datetime.utcnow())
    
    def _validate_session(self, api_key: str, client_ip: str, user_agent: str) -> bool:
        """Validate API key session for consistency."""
        if not self.enable_session_tracking:
            return True
        
        if api_key not in self.active_sessions:
            # Create new session
            self.active_sessions[api_key] = {
                "client_ip": client_ip,
                "user_agent": user_agent,
                "first_seen": datetime.utcnow(),
                "last_seen": datetime.utcnow(),
                "request_count": 1
            }
            return True
        
        session = self.active_sessions[api_key]
        
        # Check for session hijacking indicators
        if session["client_ip"] != client_ip:
            logger.warning(
                f"API key session IP mismatch: {session['client_ip']} -> {client_ip}"
            )
            # Allow IP changes but log them (mobile users, etc.)
        
        if session["user_agent"] != user_agent:
            logger.warning(
                f"API key session User-Agent mismatch for key: {api_key[:8]}..."
            )
            # Allow User-Agent changes but log them
        
        # Update session
        session["last_seen"] = datetime.utcnow()
        session["request_count"] += 1
        
        return True
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Skip authentication for public paths
        if path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Check if path requires authentication
        requires_auth = any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
        
        if not requires_auth or not self.require_auth:
            return await call_next(request)
        
        # Check if IP is locked out
        if self._is_ip_locked_out(client_ip):
            global_error_handler.handle_error(
                exception=Exception("IP locked out due to failed authentication attempts"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "path": path,
                    "lockout_reason": "too_many_failed_attempts"
                },
                user_message="IP temporarily locked due to security policy"
            )
            
            return JSONResponse(
                status_code=429,
                content=create_safe_error_response(
                    error_code="IP_LOCKED_OUT",
                    user_message="Too many failed authentication attempts. Please try again later.",
                    error_id=request_id,
                    details={"retry_after": int(self.lockout_duration.total_seconds())}
                )
            )
        
        # Extract API key from multiple possible locations
        api_key = None
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
        elif auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]  # Remove "ApiKey " prefix
        else:
            # Check X-API-Key header
            api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            self._record_failed_attempt(client_ip)
            
            global_error_handler.handle_error(
                exception=Exception("Missing API key"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                context={
                    "request_id": request_id,
                    "path": path,
                    "method": request.method,
                    "client_ip": client_ip,
                    "user_agent": sanitize_for_logging(user_agent)
                },
                user_message="Authentication required"
            )
            
            return JSONResponse(
                status_code=401,
                content=create_safe_error_response(
                    error_code="AUTHENTICATION_REQUIRED",
                    user_message="API key is required for this endpoint",
                    error_id=request_id
                ),
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate API key format first
        if not validate_api_key_format(api_key):
            self._record_failed_attempt(client_ip)
            
            global_error_handler.handle_error(
                exception=Exception("Invalid API key format"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "path": path,
                    "client_ip": client_ip,
                    "api_key_length": len(api_key) if api_key else 0
                },
                user_message="Invalid API key format"
            )
            
            return JSONResponse(
                status_code=401,
                content=create_safe_error_response(
                    error_code="INVALID_API_KEY_FORMAT",
                    user_message="The provided API key format is invalid",
                    error_id=request_id
                )
            )
        
        # Validate API key
        key_data = api_key_manager.validate_key(api_key)
        if not key_data:
            self._record_failed_attempt(client_ip)
            
            global_error_handler.handle_error(
                exception=Exception("Invalid API key"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "path": path,
                    "method": request.method,
                    "client_ip": client_ip,
                    "api_key_prefix": api_key[:8] if api_key else "none"
                },
                user_message="Invalid API key"
            )
            
            return JSONResponse(
                status_code=401,
                content=create_safe_error_response(
                    error_code="INVALID_API_KEY",
                    user_message="The provided API key is invalid or expired",
                    error_id=request_id
                )
            )
        
        # Validate session consistency
        if not self._validate_session(api_key, client_ip, user_agent):
            global_error_handler.handle_error(
                exception=Exception("Session validation failed"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "path": path,
                    "client_ip": client_ip,
                    "api_key_name": key_data.get("name")
                },
                user_message="Session validation failed"
            )
            
            return JSONResponse(
                status_code=401,
                content=create_safe_error_response(
                    error_code="SESSION_INVALID",
                    user_message="Session validation failed. Please re-authenticate.",
                    error_id=request_id
                )
            )
        
        # Check rate limit for this API key
        if not api_key_manager.check_rate_limit(api_key):
            global_error_handler.handle_error(
                exception=Exception("API key rate limit exceeded"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                context={
                    "request_id": request_id,
                    "path": path,
                    "api_key_name": key_data.get("name"),
                    "rate_limit": key_data.get("rate_limit")
                },
                user_message="API key rate limit exceeded"
            )
            
            return JSONResponse(
                status_code=429,
                content=create_safe_error_response(
                    error_code="API_KEY_RATE_LIMIT",
                    user_message="API key rate limit exceeded. Please try again later.",
                    error_id=request_id,
                    details={"retry_after": 3600}
                )
            )
        
        # Store API key info in request state for downstream use
        request.state.api_key_data = key_data
        request.state.authenticated_session = self.active_sessions.get(api_key)
        
        return await call_next(request)


class EnhancedRateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting middleware with per-endpoint and per-IP limits.
    
    Implements Requirement 6.4: Security measures including rate limiting.
    """
    
    # Default rate limits per endpoint pattern
    ENDPOINT_LIMITS = {
        "POST /patients": {"max_requests": 50, "window_seconds": 60},
        "PUT /patients/*/vitals": {"max_requests": 100, "window_seconds": 60},
        "GET /patients/*": {"max_requests": 200, "window_seconds": 60},
        "default": {"max_requests": 100, "window_seconds": 60},
    }
    
    def __init__(self, app, global_max_requests: int = 1000, global_window_seconds: int = 60):
        super().__init__(app)
        self.global_max_requests = global_max_requests
        self.global_window_seconds = global_window_seconds
        self.requests: Dict[str, List[float]] = {}  # IP -> timestamps
        self.endpoint_requests: Dict[str, Dict[str, List[float]]] = {}  # endpoint -> IP -> timestamps
    
    def _get_endpoint_pattern(self, method: str, path: str) -> str:
        """Get the endpoint pattern for rate limiting."""
        # Normalize path by replacing IDs with wildcards
        normalized_path = path
        parts = path.split("/")
        for i, part in enumerate(parts):
            if part and not part.startswith("{") and len(part) > 10:
                # Likely a patient ID or similar
                parts[i] = "*"
        normalized_path = "/".join(parts)
        
        return f"{method} {normalized_path}"
    
    def _get_limits(self, endpoint_pattern: str) -> Dict[str, int]:
        """Get rate limits for an endpoint pattern."""
        for pattern, limits in self.ENDPOINT_LIMITS.items():
            if pattern == "default":
                continue
            if self._pattern_matches(pattern, endpoint_pattern):
                return limits
        return self.ENDPOINT_LIMITS["default"]
    
    def _pattern_matches(self, pattern: str, endpoint: str) -> bool:
        """Check if endpoint matches a pattern."""
        pattern_parts = pattern.split()
        endpoint_parts = endpoint.split()
        
        if len(pattern_parts) != len(endpoint_parts):
            return False
        
        # Check method
        if pattern_parts[0] != endpoint_parts[0]:
            return False
        
        # Check path with wildcard support
        pattern_path = pattern_parts[1].split("/")
        endpoint_path = endpoint_parts[1].split("/")
        
        if len(pattern_path) != len(endpoint_path):
            return False
        
        for p, e in zip(pattern_path, endpoint_path):
            if p != "*" and p != e:
                return False
        
        return True
    
    def _clean_old_requests(self, requests_dict: Dict[str, List[float]], cutoff_time: float) -> None:
        """Remove old request timestamps."""
        keys_to_remove = []
        for key, timestamps in requests_dict.items():
            requests_dict[key] = [t for t in timestamps if t > cutoff_time]
            if not requests_dict[key]:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del requests_dict[key]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        request_id = getattr(request.state, "request_id", "unknown")
        current_time = time.time()
        
        # Get endpoint pattern and limits
        endpoint_pattern = self._get_endpoint_pattern(request.method, request.url.path)
        limits = self._get_limits(endpoint_pattern)
        
        # Clean old requests
        global_cutoff = current_time - self.global_window_seconds
        endpoint_cutoff = current_time - limits["window_seconds"]
        
        self._clean_old_requests(self.requests, global_cutoff)
        
        # Check global rate limit
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        if len(self.requests[client_ip]) >= self.global_max_requests:
            logger.warning(f"[{request_id}] Global rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content=create_safe_error_response(
                    error_code="RATE_LIMIT_EXCEEDED",
                    user_message="Too many requests. Please try again later.",
                    error_id=request_id,
                    details={"retry_after": self.global_window_seconds}
                )
            )
        
        # Check endpoint-specific rate limit
        if endpoint_pattern not in self.endpoint_requests:
            self.endpoint_requests[endpoint_pattern] = {}
        
        self._clean_old_requests(self.endpoint_requests[endpoint_pattern], endpoint_cutoff)
        
        if client_ip not in self.endpoint_requests[endpoint_pattern]:
            self.endpoint_requests[endpoint_pattern][client_ip] = []
        
        if len(self.endpoint_requests[endpoint_pattern][client_ip]) >= limits["max_requests"]:
            logger.warning(
                f"[{request_id}] Endpoint rate limit exceeded for IP: {client_ip} "
                f"on endpoint: {endpoint_pattern}"
            )
            return JSONResponse(
                status_code=429,
                content=create_safe_error_response(
                    error_code="ENDPOINT_RATE_LIMIT",
                    user_message=f"Too many requests to this endpoint. Please try again later.",
                    error_id=request_id,
                    details={"retry_after": limits["window_seconds"]}
                )
            )
        
        # Record this request
        self.requests[client_ip].append(current_time)
        self.endpoint_requests[endpoint_pattern][client_ip].append(current_time)
        
        return await call_next(request)


class ContentValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating request content.
    
    Implements Requirement 6.4: Comprehensive input sanitization.
    """
    
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB max request size
    MAX_JSON_DEPTH = 10  # Maximum JSON nesting depth
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.MAX_CONTENT_LENGTH:
                    global_error_handler.handle_error(
                        exception=Exception(f"Request too large: {length} bytes"),
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.MEDIUM,
                        context={
                            "request_id": request_id,
                            "content_length": length,
                            "max_allowed": self.MAX_CONTENT_LENGTH
                        },
                        user_message="Request body too large"
                    )
                    
                    logger.warning(
                        f"[{request_id}] Request too large: {length} bytes "
                        f"(max: {self.MAX_CONTENT_LENGTH})"
                    )
                    return JSONResponse(
                        status_code=413,
                        content=create_safe_error_response(
                            error_code="REQUEST_TOO_LARGE",
                            user_message="Request body is too large",
                            error_id=request_id,
                            details={"max_size": self.MAX_CONTENT_LENGTH}
                        )
                    )
            except ValueError:
                pass
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if content_type and not content_type.startswith("application/json"):
                # Allow form data for specific endpoints if needed
                base_type = content_type.split(";")[0].strip().lower()
                if base_type not in ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]:
                    global_error_handler.handle_error(
                        exception=Exception(f"Unsupported content type: {base_type}"),
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.MEDIUM,
                        context={
                            "request_id": request_id,
                            "content_type": base_type,
                            "allowed_types": ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]
                        },
                        user_message="Unsupported content type"
                    )
                    
                    logger.warning(
                        f"[{request_id}] Invalid content type: {base_type}"
                    )
                    return JSONResponse(
                        status_code=415,
                        content=create_safe_error_response(
                            error_code="UNSUPPORTED_MEDIA_TYPE",
                            user_message="Content type not supported. Use application/json.",
                            error_id=request_id
                        )
                    )
        
        return await call_next(request)


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Secure random API key
    """
    return secrets.token_urlsafe(32)


class ComprehensiveSecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware that combines all security validations.
    
    Implements Requirement 6.4: Comprehensive input sanitization to prevent 
    injection attacks and data corruption.
    """
    
    def __init__(self, app, enable_strict_validation: bool = True):
        """
        Initialize comprehensive security middleware.
        
        Args:
            app: FastAPI application
            enable_strict_validation: If True, enable strict security validation
        """
        super().__init__(app)
        self.enable_strict_validation = enable_strict_validation
        self.security_events: List[Dict[str, Any]] = []
        self.max_security_events = 1000  # Keep last 1000 events in memory
    
    def _log_security_event(self, event_type: str, request_id: str, details: Dict[str, Any]) -> None:
        """Log security event for monitoring."""
        from src.utils.security_config import log_security_event
        
        log_security_event(event_type, request_id, details, "high")
        
        # Store in memory for monitoring
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "request_id": request_id,
            "details": details
        }
        
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > self.max_security_events:
            self.security_events = self.security_events[-self.max_security_events:]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip security validation for health check and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Perform comprehensive request validation
        try:
            # Read request body if present
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode('utf-8', errors='ignore')
            
            # Validate entire request
            from src.utils.validation import comprehensive_request_validation
            
            validation_issues = comprehensive_request_validation(
                headers=dict(request.headers),
                query_params=dict(request.query_params),
                body=body,
                client_ip=client_ip
            )
            
            # Check for critical security issues
            critical_issues = []
            for category, issues in validation_issues.items():
                if issues:
                    critical_issues.extend([f"{category}: {issue}" for issue in issues])
            
            if critical_issues and self.enable_strict_validation:
                # Log security event
                self._log_security_event(
                    "COMPREHENSIVE_VALIDATION_FAILURE",
                    request_id,
                    {
                        "client_ip": client_ip,
                        "path": request.url.path,
                        "method": request.method,
                        "issues": critical_issues[:10],  # Limit to first 10 issues
                        "total_issues": len(critical_issues)
                    }
                )
                
                global_error_handler.handle_error(
                    exception=ValueError(f"Security validation failed: {len(critical_issues)} issues"),
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.HIGH,
                    context={
                        "request_id": request_id,
                        "client_ip": client_ip,
                        "validation_issues": critical_issues[:5],  # Log first 5 issues
                        "operation": "comprehensive_security_validation"
                    },
                    user_message="Request failed security validation"
                )
                
                return JSONResponse(
                    status_code=400,
                    content=create_safe_error_response(
                        error_code="SECURITY_VALIDATION_FAILED",
                        user_message="Request failed security validation. Please check your input.",
                        error_id=request_id,
                        details={"issue_count": len(critical_issues)}
                    )
                )
            
            # If body was read, recreate the request with the body
            if body:
                async def receive():
                    return {"type": "http.request", "body": body.encode('utf-8')}
                
                request._receive = receive
            
            # Store validation results in request state for downstream use
            request.state.security_validation = {
                "issues": validation_issues,
                "validated_at": datetime.utcnow().isoformat(),
                "strict_mode": self.enable_strict_validation
            }
            
        except Exception as e:
            # Handle validation errors gracefully
            global_error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "operation": "security_middleware_processing"
                },
                user_message="Error during security validation"
            )
            
            logger.error(f"[{request_id}] Security middleware error: {e}")
            
            # Continue processing but log the error
            if self.enable_strict_validation:
                return JSONResponse(
                    status_code=500,
                    content=create_safe_error_response(
                        error_code="SECURITY_VALIDATION_ERROR",
                        user_message="Security validation error. Please try again.",
                        error_id=request_id
                    )
                )
        
        return await call_next(request)
    
    def get_security_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events for monitoring."""
        return self.security_events[-limit:]


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.
    
    Args:
        api_key: API key to hash
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


# Create global instances for enhanced security
enhanced_auth_middleware = None
comprehensive_security_middleware = None


def get_enhanced_auth_middleware(require_auth: bool = False) -> EnhancedAuthenticationMiddleware:
    """Get or create enhanced authentication middleware instance."""
    global enhanced_auth_middleware
    if enhanced_auth_middleware is None:
        enhanced_auth_middleware = EnhancedAuthenticationMiddleware(None, require_auth=require_auth)
    return enhanced_auth_middleware


def get_comprehensive_security_middleware(strict_validation: bool = True) -> ComprehensiveSecurityMiddleware:
    """Get or create comprehensive security middleware instance."""
    global comprehensive_security_middleware
    if comprehensive_security_middleware is None:
        comprehensive_security_middleware = ComprehensiveSecurityMiddleware(None, enable_strict_validation=strict_validation)
    return comprehensive_security_middleware