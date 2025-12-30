"""
FastAPI main application for Patient Risk Classifier Backend.
Configures the API with middleware, error handlers, and routing.
"""

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from src.models.api_models import ErrorResponse
from src.utils.database import close_database, init_database
from src.utils.validation import (
    sanitize_string, 
    validate_patient_id, 
    sanitize_dict, 
    DANGEROUS_PATTERNS,
    create_safe_error_details,
    validate_request_headers,
    validate_user_agent,
    validate_ip_address,
    sanitize_for_logging,
    validate_json_depth,
    validate_json_size,
    sanitize_log_message
)
from src.utils.error_handling import (
    global_error_handler,
    ErrorCategory,
    ErrorSeverity,
    setup_error_monitoring
)
from src.utils.security import (
    EnhancedAuthenticationMiddleware,
    EnhancedRateLimitingMiddleware,
    ContentValidationMiddleware,
    ComprehensiveSecurityMiddleware,
    api_key_manager,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("patient_risk_classifier")

# Initialize error monitoring system
setup_error_monitoring()


def create_safe_error_response(
    error_code: str,
    user_message: str,
    error_id: str = None,
    details: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a secure error response that doesn't expose sensitive information.
    
    Args:
        error_code: Error type/code for categorization
        user_message: User-friendly error message
        error_id: Optional error ID for tracking
        details: Optional safe details to include in response
        
    Returns:
        Error response dictionary
    """
    response = {
        "error": error_code,
        "message": user_message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if error_id:
        response["error_id"] = error_id
    
    if details:
        response["details"] = details
    
    return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses with timing information."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        
        # Store request ID in state for access in handlers
        request.state.request_id = request_id
        
        # Log incoming request
        start_time = time.time()
        logger.info(
            f"[{request_id}] Request: {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"[{request_id}] Response: {response.status_code} "
                f"- Duration: {process_time:.3f}s"
            )
            
            # Add request ID to response headers for client-side tracing
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Handle the error with comprehensive tracking
            global_error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "duration": process_time
                },
                user_message="Error during request processing"
            )
            
            logger.error(
                f"[{request_id}] Error during request processing: {type(e).__name__}: {str(e)} "
                f"- Duration: {process_time:.3f}s"
            )
            raise


class EnhancedInputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for comprehensive input sanitization and validation.
    
    Implements Requirement 6.4: Comprehensive input sanitization to prevent 
    injection attacks and data corruption.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Validate request headers
        header_errors = validate_request_headers(dict(request.headers))
        if header_errors:
            global_error_handler.handle_error(
                exception=ValueError(f"Invalid headers: {', '.join(header_errors)}"),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "header_errors": header_errors,
                    "operation": "header_validation"
                },
                user_message="Invalid request headers detected"
            )
            
            logger.warning(f"[{request_id}] Invalid headers: {header_errors}")
            return JSONResponse(
                status_code=400,
                content=create_safe_error_response(
                    error_code="INVALID_HEADERS",
                    user_message="Invalid request headers detected",
                    error_id=request_id
                )
            )
        
        # Validate User-Agent
        user_agent = request.headers.get("user-agent")
        if user_agent and not validate_user_agent(user_agent):
            global_error_handler.handle_error(
                exception=ValueError("Suspicious User-Agent detected"),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "user_agent": sanitize_for_logging(user_agent),
                    "operation": "user_agent_validation"
                },
                user_message="Suspicious User-Agent detected"
            )
            
            logger.warning(f"[{request_id}] Suspicious User-Agent: {sanitize_for_logging(user_agent)}")
            return JSONResponse(
                status_code=400,
                content=create_safe_error_response(
                    error_code="SUSPICIOUS_USER_AGENT",
                    user_message="Invalid User-Agent header",
                    error_id=request_id
                )
            )
        
        # Validate client IP
        client_ip = request.client.host if request.client else "unknown"
        if client_ip != "unknown" and not validate_ip_address(client_ip):
            global_error_handler.handle_error(
                exception=ValueError("Invalid client IP address"),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                context={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "operation": "ip_validation"
                },
                user_message="Invalid client IP address"
            )
            
            logger.warning(f"[{request_id}] Invalid client IP: {client_ip}")
        
        # Sanitize query parameters
        suspicious_params = []
        for key, value in request.query_params.items():
            try:
                sanitized = sanitize_string(value)
                if sanitized != value:
                    suspicious_params.append(key)
            except ValueError as e:
                global_error_handler.handle_error(
                    exception=e,
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.HIGH,
                    context={
                        "request_id": request_id,
                        "parameter": key,
                        "operation": "query_param_sanitization"
                    },
                    user_message="Malicious content detected in request parameters"
                )
                
                logger.warning(f"[{request_id}] Malicious content in query param '{key}': {e}")
                return JSONResponse(
                    status_code=400,
                    content=create_safe_error_response(
                        error_code="INVALID_INPUT",
                        user_message="Invalid characters detected in request parameters",
                        error_id=request_id
                    )
                )
        
        if suspicious_params:
            logger.warning(f"[{request_id}] Suspicious query params: {suspicious_params}")
        
        # Validate path for injection attempts
        path = request.url.path
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                global_error_handler.handle_error(
                    exception=ValueError(f"Suspicious pattern in path: {pattern}"),
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.HIGH,
                    context={
                        "request_id": request_id,
                        "path": path,
                        "pattern": pattern,
                        "operation": "path_sanitization"
                    },
                    user_message="Potentially malicious content detected in path"
                )
                
                logger.warning(f"[{request_id}] Malicious content in path: {path}")
                return JSONResponse(
                    status_code=400,
                    content=create_safe_error_response(
                        error_code="INVALID_REQUEST",
                        user_message="Invalid request path detected",
                        error_id=request_id
                    )
                )
        
        # Check for path traversal attempts
        if "../" in path or "..\\" in path:
            global_error_handler.handle_error(
                exception=ValueError("Path traversal attempt detected"),
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                context={
                    "request_id": request_id,
                    "path": path,
                    "operation": "path_traversal_check"
                },
                user_message="Path traversal attempt detected"
            )
            
            logger.warning(f"[{request_id}] Path traversal attempt: {path}")
            return JSONResponse(
                status_code=400,
                content=create_safe_error_response(
                    error_code="INVALID_REQUEST",
                    user_message="Invalid request path",
                    error_id=request_id
                )
            )
        
        return await call_next(request)


class JSONValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating and sanitizing JSON request bodies.
    
    Implements Requirement 6.4: Comprehensive input sanitization to prevent 
    injection attacks and data corruption.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Only process JSON requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                try:
                    # Read and parse JSON body
                    body = await request.body()
                    if body:
                        try:
                            import json
                            json_data = json.loads(body)
                            
                            # Validate JSON structure
                            validate_json_depth(json_data, max_depth=10)
                            validate_json_size(json_data, max_keys=1000)
                            
                            # Sanitize JSON data
                            sanitized_data = sanitize_dict(json_data)
                            
                            # Replace request body with sanitized version
                            sanitized_body = json.dumps(sanitized_data).encode()
                            
                            # Create new request with sanitized body
                            async def receive():
                                return {"type": "http.request", "body": sanitized_body}
                            
                            # Update request scope
                            request._receive = receive
                            
                        except json.JSONDecodeError as e:
                            global_error_handler.handle_error(
                                exception=e,
                                category=ErrorCategory.VALIDATION,
                                severity=ErrorSeverity.MEDIUM,
                                context={
                                    "request_id": request_id,
                                    "operation": "json_parsing",
                                    "error": str(e)
                                },
                                user_message="Invalid JSON format"
                            )
                            
                            logger.warning(f"[{request_id}] Invalid JSON: {e}")
                            return JSONResponse(
                                status_code=400,
                                content=create_safe_error_response(
                                    error_code="INVALID_JSON",
                                    user_message="Invalid JSON format in request body",
                                    error_id=request_id
                                )
                            )
                        
                        except ValueError as e:
                            # Handle JSON validation errors (depth, size, etc.)
                            global_error_handler.handle_error(
                                exception=e,
                                category=ErrorCategory.VALIDATION,
                                severity=ErrorSeverity.HIGH,
                                context={
                                    "request_id": request_id,
                                    "operation": "json_validation",
                                    "error": str(e)
                                },
                                user_message="Invalid JSON structure"
                            )
                            
                            logger.warning(f"[{request_id}] JSON validation error: {e}")
                            return JSONResponse(
                                status_code=400,
                                content=create_safe_error_response(
                                    error_code="INVALID_JSON_STRUCTURE",
                                    user_message="JSON structure validation failed",
                                    error_id=request_id
                                )
                            )
                
                except Exception as e:
                    # Handle unexpected errors during JSON processing
                    global_error_handler.handle_error(
                        exception=e,
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        context={
                            "request_id": request_id,
                            "operation": "json_middleware_processing"
                        },
                        user_message="Error processing request body"
                    )
                    
                    logger.error(f"[{request_id}] JSON middleware error: {e}")
                    return JSONResponse(
                        status_code=500,
                        content=create_safe_error_response(
                            error_code="REQUEST_PROCESSING_ERROR",
                            user_message="Error processing request body",
                            error_id=request_id
                        )
                    )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers (Requirement 6.4: Security measures)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware for basic protection."""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis or similar
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        request_id = getattr(request.state, "request_id", "unknown")
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - self.window_seconds
        self.requests = {
            ip: timestamps for ip, timestamps in self.requests.items()
            if any(t > cutoff_time for t in timestamps)
        }
        
        # Update current IP's requests
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old timestamps for this IP
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > cutoff_time
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            # Handle rate limit exceeded
            global_error_handler.handle_error(
                exception=Exception("Rate limit exceeded"),
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM,
                context={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "request_count": len(self.requests[client_ip]),
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds
                },
                user_message="Rate limit exceeded"
            )
            
            logger.warning(f"[{request_id}] Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content=create_safe_error_response(
                    error_code="RATE_LIMIT_EXCEEDED",
                    user_message="Too many requests. Please try again later.",
                    error_id=request_id,
                    details={"retry_after": self.window_seconds}
                )
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("🏥 Patient Risk Classifier Backend starting up...")
    logger.info("📊 Initializing database connections...")
    init_database()
    logger.info("✅ Application startup complete")

    yield

    # Shutdown
    logger.info("🏥 Patient Risk Classifier Backend shutting down...")
    logger.info("📊 Closing database connections...")
    close_database()
    logger.info("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Patient Risk Classifier Backend",
    description="""
    A RESTful API system for patient risk classification that continuously monitors 
    patient vital signs and uses a pre-trained machine learning model to assess 
    deterioration risk.
    
    ## Features
    
    * **Patient Registration** - Register patients with initial vital signs and clinical information
    * **Vital Signs Monitoring** - Update and track patient vital signs over time
    * **Risk Assessment** - Automated risk scoring using machine learning models
    * **Historical Data** - Access to complete patient history and trends
    * **High-Risk Alerts** - Query and identify high-risk patients
    
    ## Medical Validation
    
    All vital signs are validated against medically acceptable ranges:
    - Heart Rate: 30-200 bpm
    - Systolic BP: 50-300 mmHg  
    - Diastolic BP: 20-200 mmHg
    - Respiratory Rate: 5-60 breaths/min
    - Oxygen Saturation: 50-100%
    - Temperature: 30-45°C
    """,
    version="1.0.0",
    contact={
        "name": "Patient Risk Classifier Team",
        "email": "support@patientrisk.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add JSON validation middleware (validates and sanitizes JSON request bodies)
app.add_middleware(JSONValidationMiddleware)

# Add enhanced input sanitization middleware
app.add_middleware(EnhancedInputSanitizationMiddleware)

# Add content validation middleware (validates content type and size)
app.add_middleware(ContentValidationMiddleware)

# Add enhanced rate limiting middleware (per-endpoint limits)
app.add_middleware(EnhancedRateLimitingMiddleware, global_max_requests=1000, global_window_seconds=60)

# Add basic rate limiting middleware (IP-based protection)
app.add_middleware(RateLimitingMiddleware, max_requests=100, window_seconds=60)

# Add enhanced authentication middleware (disabled by default for demo, enable with require_auth=True)
# In production, set require_auth=True to enforce API key authentication
app.add_middleware(EnhancedAuthenticationMiddleware, require_auth=False, enable_session_tracking=True)

# Add comprehensive security middleware for enhanced input validation
app.add_middleware(ComprehensiveSecurityMiddleware, enable_strict_validation=False)  # Set to True for production


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error response format."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Handle the HTTP exception with comprehensive tracking
    severity = ErrorSeverity.HIGH if exc.status_code >= 500 else ErrorSeverity.MEDIUM
    global_error_handler.handle_error(
        exception=exc,
        category=ErrorCategory.SYSTEM,
        severity=severity,
        context={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        },
        user_message=f"HTTP {exc.status_code} error"
    )
    
    # Log the HTTP exception with appropriate level
    if exc.status_code >= 500:
        logger.error(
            f"[{request_id}] HTTP {exc.status_code}: {exc.detail} "
            f"- Path: {request.url.path}"
        )
    else:
        logger.warning(
            f"[{request_id}] HTTP {exc.status_code}: {exc.detail} "
            f"- Path: {request.url.path}"
        )
    
    # Create secure error response based on status code
    if exc.status_code == 404:
        error_response = create_safe_error_response(
            error_code="RESOURCE_NOT_FOUND",
            user_message="The requested resource was not found",
            error_id=request_id
        )
    elif exc.status_code == 400:
        error_response = create_safe_error_response(
            error_code="BAD_REQUEST",
            user_message="Invalid request data provided",
            error_id=request_id,
            details=getattr(exc, "details", None)
        )
    elif exc.status_code == 422:
        error_response = create_safe_error_response(
            error_code="VALIDATION_ERROR",
            user_message="Request data validation failed",
            error_id=request_id,
            details=getattr(exc, "details", None)
        )
    elif exc.status_code == 429:
        error_response = create_safe_error_response(
            error_code="RATE_LIMIT_EXCEEDED",
            user_message="Too many requests. Please try again later.",
            error_id=request_id,
            details={"retry_after": 60}
        )
    elif exc.status_code >= 500:
        error_response = create_safe_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            user_message="An internal server error occurred. Please try again later.",
            error_id=request_id
        )
    else:
        # Generic error response for other status codes
        error_response = create_safe_error_response(
            error_code=f"HTTP_{exc.status_code}",
            user_message="An error occurred while processing your request",
            error_id=request_id
        )
    
    return JSONResponse(
        status_code=exc.status_code, 
        content=error_response
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with secure error responses.
    
    Implements Requirement 6.5: Log detailed error information while returning 
    user-friendly error messages.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Handle the unexpected exception with comprehensive tracking
    system_error = global_error_handler.handle_error(
        exception=exc,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.CRITICAL,
        context={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": sanitize_for_logging(request.headers.get("user-agent", "unknown")),
            "content_type": request.headers.get("content-type", "unknown"),
            "content_length": request.headers.get("content-length", "unknown")
        },
        user_message="Unexpected system error occurred"
    )
    
    # Log the full exception details for debugging (internal only)
    # This satisfies Requirement 6.5: detailed error logging
    logger.error(
        f"[{request_id}] Unexpected error: {type(exc).__name__}: {sanitize_log_message(str(exc))} "
        f"- Path: {request.url.path} - Method: {request.method} "
        f"- Client: {request.client.host if request.client else 'unknown'}",
        exc_info=True  # Include stack trace in logs
    )

    # Return generic error response without exposing internal details
    # This satisfies Requirement 6.5: user-friendly messages without sensitive info
    error_response = create_safe_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        user_message="An unexpected error occurred. Please try again later.",
        error_id=system_error.error_id
    )
    return JSONResponse(status_code=500, content=error_response)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with descriptive messages."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Handle the validation error with comprehensive tracking
    global_error_handler.handle_error(
        exception=exc,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        context={
            "request_id": request_id,
            "path": request.url.path,
            "error_count": len(exc.errors())
        },
        user_message="Request validation failed"
    )
    
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        # Sanitize error messages to prevent information leakage
        safe_message = sanitize_string(error["msg"])
        errors.append({
            "field": field,
            "message": safe_message,
            "type": error["type"]
        })
    
    logger.warning(
        f"[{request_id}] Validation error: {len(errors)} field(s) invalid "
        f"- Path: {request.url.path}"
    )
    
    error_response = create_safe_error_response(
        error_code="VALIDATION_ERROR",
        user_message="Invalid input data. Please check the provided values.",
        error_id=request_id,
        details={"validation_errors": errors}
    )
    return JSONResponse(status_code=422, content=error_response)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for system monitoring.

    Returns system status and basic information.
    """
    # Get error statistics for monitoring
    error_stats = global_error_handler.get_error_statistics()
    
    return {
        "status": "healthy",
        "service": "Patient Risk Classifier Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "ml_model": "available",
        "error_monitoring": {
            "total_errors": sum(error_stats["error_counts"].values()),
            "circuit_breakers": len(error_stats["circuit_breakers"])
        }
    }


# System monitoring endpoint
@app.get("/system/errors", tags=["System"])
async def get_error_statistics() -> Dict[str, Any]:
    """
    Get system error statistics for monitoring.
    
    Returns comprehensive error tracking information.
    """
    return global_error_handler.get_error_statistics()


# Security monitoring endpoint
@app.get("/system/security", tags=["System"])
async def get_security_events(limit: int = 100) -> Dict[str, Any]:
    """
    Get recent security events for monitoring.
    
    Returns security event information for system monitoring.
    """
    from src.utils.security import get_comprehensive_security_middleware
    
    security_middleware = get_comprehensive_security_middleware()
    events = security_middleware.get_security_events(limit)
    
    return {
        "security_events": events,
        "total_events": len(events),
        "monitoring_enabled": True,
        "last_updated": datetime.utcnow().isoformat()
    }


# Demo endpoints for development
@app.get("/demo/info", tags=["Demo"])
async def demo_info() -> Dict[str, Any]:
    """
    Demo information endpoint.

    Provides information about the demo system and sample data.
    """
    return {
        "message": "Patient Risk Classifier Backend Demo",
        "description": "Real-time patient deterioration risk assessment system",
        "endpoints": {"health": "/health", "docs": "/docs", "openapi": "/openapi.json"},
        "sample_data": {
            "patients": "Sample patients will be available after database setup",
            "vital_signs": "Sample vital signs data for testing",
            "risk_assessments": "Sample risk assessment results",
        },
        "next_steps": [
            "Complete database setup (Task 3.1)",
            "Implement patient registration (Task 6.2)",
            "Add vital signs endpoints (Task 6.4)",
            "Integrate ML risk model (Task 5.5)",
        ],
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema with additional metadata."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom schema extensions
    openapi_schema["info"]["x-logo"] = {"url": "https://example.com/logo.png"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Include routers for API endpoints
from src.api.patients import router as patients_router
from src.api.vitals import router as vitals_router

app.include_router(patients_router)
app.include_router(vitals_router)