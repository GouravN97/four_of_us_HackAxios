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

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("patient_risk_classifier")


# Input sanitization patterns for security
DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # XSS script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"--",  # SQL comment
    r";.*(?:drop|delete|truncate|alter|create|insert|update)",  # SQL injection
    r"'\s*or\s*'",  # SQL injection OR
    r"'\s*and\s*'",  # SQL injection AND
    r"\$\{.*\}",  # Template injection
    r"\{\{.*\}\}",  # Template injection
]


def sanitize_string(value: str) -> str:
    """
    Sanitize a string value to prevent injection attacks.
    
    Args:
        value: The string to sanitize
        
    Returns:
        Sanitized string with dangerous patterns removed
    """
    if not isinstance(value, str):
        return value
    
    sanitized = value
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    
    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")
    
    return sanitized.strip()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: Dictionary to sanitize
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def create_secure_error_response(
    error_code: str,
    user_message: str,
    request_id: str = None,
    details: Dict[str, Any] = None
) -> ErrorResponse:
    """
    Create a secure error response that doesn't expose sensitive information.
    
    Args:
        error_code: Error type/code for categorization
        user_message: User-friendly error message
        request_id: Optional request ID for support reference
        details: Optional safe details to include
        
    Returns:
        ErrorResponse with sanitized content
    """
    safe_details = {}
    if request_id:
        safe_details["request_id"] = request_id
    if details:
        # Only include safe, non-sensitive details
        safe_keys = {"field", "fields", "validation_errors", "allowed_values", "request_id"}
        for key, value in details.items():
            if key in safe_keys:
                safe_details[key] = value
    
    return ErrorResponse(
        error=error_code,
        message=user_message,
        details=safe_details if safe_details else None
    )


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
            logger.error(
                f"[{request_id}] Error during request processing: {type(e).__name__}: {str(e)} "
                f"- Duration: {process_time:.3f}s"
            )
            raise


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for sanitizing input data to prevent injection attacks."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Sanitize query parameters
        # Note: Query params are read-only, so we log warnings for suspicious content
        for key, value in request.query_params.items():
            sanitized = sanitize_string(value)
            if sanitized != value:
                logger.warning(
                    f"[{request_id}] Potentially malicious content detected in query param '{key}'"
                )
        
        # Sanitize path parameters (check for suspicious patterns)
        path = request.url.path
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.warning(
                    f"[{request_id}] Potentially malicious content detected in path: {path}"
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "INVALID_REQUEST",
                        "message": "Invalid request path",
                        "details": None,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
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

# Add input sanitization middleware
app.add_middleware(InputSanitizationMiddleware)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error response format."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the HTTP exception
    logger.warning(
        f"[{request_id}] HTTP {exc.status_code}: {exc.detail} "
        f"- Path: {request.url.path}"
    )
    
    error_response = ErrorResponse(
        error=f"HTTP_{exc.status_code}",
        message=exc.detail,
        details=getattr(exc, "details", None),
    )
    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with secure error responses."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the full exception details for debugging (internal only)
    logger.error(
        f"[{request_id}] Unexpected error: {type(exc).__name__}: {str(exc)} "
        f"- Path: {request.url.path}",
        exc_info=True  # Include stack trace in logs
    )

    # Return generic error response without exposing internal details
    # This satisfies Requirement 6.5: user-friendly messages without sensitive info
    error_response = create_secure_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        user_message="An unexpected error occurred. Please try again later.",
        request_id=request_id
    )
    return JSONResponse(status_code=500, content=error_response.model_dump(mode='json'))


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with descriptive messages."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"[{request_id}] Validation error: {len(errors)} field(s) invalid "
        f"- Path: {request.url.path}"
    )
    
    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="Invalid input data. Please check the provided values.",
        details={"validation_errors": errors}
    )
    return JSONResponse(status_code=422, content=error_response.model_dump(mode='json'))


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for system monitoring.

    Returns system status and basic information.
    """
    return {
        "status": "healthy",
        "service": "Patient Risk Classifier Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",  # TODO: Add actual database health check in task 3.1
        "ml_model": "available",  # TODO: Add actual ML model health check in task 5.5
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
