"""
System-wide error handling utilities for comprehensive error management.
Implements Requirements 3.4, 4.5, 5.3, 5.5, 6.3 for robust error handling.
"""

import logging
import traceback
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from contextlib import contextmanager
import time
import sys

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorizing system errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    NETWORK = "network"
    TIMEOUT = "timeout"


class SystemError:
    """
    Structured error information for comprehensive error tracking.
    
    Implements Requirements 3.4, 4.5, 5.3, 5.5 for error logging and monitoring.
    """
    
    def __init__(
        self,
        error_id: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.error_id = error_id
        self.category = category
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.exception = exception
        self.context = context or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.stack_trace = None
        
        if exception:
            self.stack_trace = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and storage."""
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "exception_type": type(self.exception).__name__ if self.exception else None,
            "stack_trace": self.stack_trace
        }
    
    def log(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """Log the error with appropriate severity level."""
        log = logger_instance or logger
        log_message = f"[{self.error_id}] {self.category.value.upper()}: {self.message}"
        
        if self.severity == ErrorSeverity.CRITICAL:
            log.critical(log_message)
        elif self.severity == ErrorSeverity.HIGH:
            log.error(log_message)
        elif self.severity == ErrorSeverity.MEDIUM:
            log.warning(log_message)
        else:
            log.info(log_message)


class ErrorHandler:
    """
    Centralized error handling and monitoring system.
    
    Provides comprehensive error tracking, logging, and graceful degradation
    for external service failures. Implements Requirements 3.4, 4.5, 5.3, 5.5, 6.3.
    """
    
    def __init__(self, service_name: str = "patient_risk_classifier"):
        self.service_name = service_name
        self.error_count = {}
        self.circuit_breakers = {}
        self.logger = logging.getLogger(f"{service_name}.error_handler")
    
    def handle_error(
        self,
        exception: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ) -> SystemError:
        """Handle and log an error with comprehensive tracking."""
        error_id = str(uuid.uuid4())[:8]
        
        system_error = SystemError(
            error_id=error_id,
            category=category,
            severity=severity,
            message=user_message or str(exception),
            exception=exception,
            context=context or {},
            details={
                "exception_type": type(exception).__name__,
                "service": self.service_name
            }
        )
        
        system_error.log(self.logger)
        
        error_key = f"{category.value}_{type(exception).__name__}"
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
        self._check_circuit_breaker(category, error_key)
        
        return system_error
    
    def _check_circuit_breaker(self, category: ErrorCategory, error_key: str) -> None:
        """Check if circuit breaker should be triggered for external services."""
        if category == ErrorCategory.EXTERNAL_SERVICE:
            error_count = self.error_count.get(error_key, 0)
            if error_count >= 5:
                if error_key not in self.circuit_breakers:
                    self.circuit_breakers[error_key] = {
                        "opened_at": datetime.utcnow(),
                        "error_count": error_count
                    }
                    self.logger.warning(
                        f"Circuit breaker OPENED for {error_key} after {error_count} errors"
                    )
    
    def is_circuit_open(self, service_key: str) -> bool:
        """Check if circuit breaker is open for a service."""
        if service_key not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[service_key]
        opened_at = breaker["opened_at"]
        
        if (datetime.utcnow() - opened_at).total_seconds() > 300:
            del self.circuit_breakers[service_key]
            self.logger.info(f"Circuit breaker RESET for {service_key}")
            return False
        
        return True
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "service": self.service_name,
            "error_counts": self.error_count.copy(),
            "circuit_breakers": {
                key: {
                    "opened_at": breaker["opened_at"].isoformat(),
                    "error_count": breaker["error_count"]
                }
                for key, breaker in self.circuit_breakers.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_service_error(
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for handling service-level errors with comprehensive logging.
    
    Implements Requirements 3.4, 4.5, 5.3, 5.5 for error handling and monitoring.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                global_error_handler.handle_error(
                    exception=e,
                    category=category,
                    severity=severity,
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        **(context or {})
                    },
                    user_message=user_message
                )
                raise e
        return wrapper
    return decorator


@contextmanager
def error_context(
    operation: str,
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None
):
    """Context manager for error handling with operation tracking."""
    start_time = time.time()
    operation_context = {
        "operation": operation,
        "start_time": datetime.utcnow().isoformat(),
        **(context or {})
    }
    
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        operation_context["duration_seconds"] = duration
        
        global_error_handler.handle_error(
            exception=e,
            category=category,
            severity=severity,
            context=operation_context,
            user_message=f"Error during {operation}"
        )
        raise


def log_performance_warning(
    operation: str,
    duration_seconds: float,
    threshold_seconds: float = 5.0,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log performance warnings for slow operations."""
    if duration_seconds > threshold_seconds:
        logger.warning(
            f"Performance warning: {operation} took {duration_seconds:.3f}s "
            f"(threshold: {threshold_seconds}s)"
        )


def monitor_external_service(
    service_name: str,
    timeout_seconds: float = 5.0,
    retry_attempts: int = 3,
    backoff_factor: float = 1.5
):
    """Decorator for monitoring external service calls with retry logic."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit_key = f"external_service_{service_name}"
            if global_error_handler.is_circuit_open(circuit_key):
                raise Exception(f"Circuit breaker open for {service_name}")
            
            last_exception = None
            
            for attempt in range(retry_attempts):
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    log_performance_warning(
                        f"{service_name}_call",
                        duration,
                        timeout_seconds,
                        {"attempt": attempt + 1}
                    )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    global_error_handler.handle_error(
                        exception=e,
                        category=ErrorCategory.EXTERNAL_SERVICE,
                        severity=ErrorSeverity.HIGH if attempt == retry_attempts - 1 else ErrorSeverity.MEDIUM,
                        context={
                            "service": service_name,
                            "attempt": attempt + 1,
                            "max_attempts": retry_attempts
                        }
                    )
                    
                    if attempt == retry_attempts - 1:
                        break
                    
                    wait_time = backoff_factor ** attempt
                    time.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator


def setup_error_monitoring() -> None:
    """Setup comprehensive error monitoring and logging."""
    root_logger = logging.getLogger()
    
    error_handler_name = "error_monitoring"
    if not any(getattr(h, 'name', None) == error_handler_name for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.name = error_handler_name
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    
    logger.info("Error monitoring system initialized")