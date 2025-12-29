"""
FastAPI main application for Patient Risk Classifier Backend.
Configures the API with middleware, error handlers, and routing.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src.models.api_models import ErrorResponse
from src.utils.database import close_database, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print("🏥 Patient Risk Classifier Backend starting up...")
    print("📊 Initializing database connections...")
    init_database()

    yield

    # Shutdown
    print("🏥 Patient Risk Classifier Backend shutting down...")
    print("📊 Closing database connections...")
    close_database()


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


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error response format."""
    error_response = ErrorResponse(
        error=f"HTTP_{exc.status_code}",
        message=exc.detail,
        details=getattr(exc, "details", None),
    )
    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with secure error responses."""
    # Log the full exception details (in production, use proper logging)
    print(f"Unexpected error: {type(exc).__name__}: {str(exc)}")

    # Return generic error response without exposing internal details
    error_response = ErrorResponse(
        error="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
    )
    return JSONResponse(status_code=500, content=error_response.model_dump())


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

# TODO: Add route includes for controllers in later tasks
# from .controllers import patients, vital_signs
# app.include_router(patients.router, prefix="/patients", tags=["Patients"])
# app.include_router(vital_signs.router, prefix="/patients", tags=["Vital Signs"])
