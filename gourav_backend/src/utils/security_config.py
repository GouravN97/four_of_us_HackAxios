"""
Security configuration and utilities for the Patient Risk Classifier Backend.
Implements Requirements 6.4 and 6.5 for comprehensive security measures.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """
    Security configuration settings.
    
    Implements Requirement 6.4: Security measures including authentication and rate limiting.
    """
    
    # Authentication settings
    require_authentication: bool = False
    api_key_min_length: int = 16
    api_key_max_length: int = 128
    
    # Rate limiting settings
    global_rate_limit: int = 1000  # requests per hour
    endpoint_rate_limits: Dict[str, Dict[str, int]] = None
    
    # Input validation settings
    max_request_size: int = 1024 * 1024  # 1MB
    max_json_depth: int = 10
    max_json_keys: int = 1000
    max_header_count: int = 100
    max_header_length: int = 8192
    
    # Security headers
    security_headers: Dict[str, str] = None
    
    # Logging settings
    log_security_events: bool = True
    log_failed_auth_attempts: bool = True
    max_log_message_length: int = 500
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.endpoint_rate_limits is None:
            self.endpoint_rate_limits = {
                "POST /patients": {"max_requests": 50, "window_seconds": 60},
                "PUT /patients/*/vitals": {"max_requests": 100, "window_seconds": 60},
                "GET /patients/*": {"max_requests": 200, "window_seconds": 60},
                "default": {"max_requests": 100, "window_seconds": 60},
            }
        
        if self.security_headers is None:
            self.security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            }


def get_security_config() -> SecurityConfig:
    """
    Get security configuration from environment variables or defaults.
    
    Returns:
        SecurityConfig instance with environment-specific settings
    """
    return SecurityConfig(
        require_authentication=os.getenv("REQUIRE_AUTH", "false").lower() == "true",
        api_key_min_length=int(os.getenv("API_KEY_MIN_LENGTH", "16")),
        api_key_max_length=int(os.getenv("API_KEY_MAX_LENGTH", "128")),
        global_rate_limit=int(os.getenv("GLOBAL_RATE_LIMIT", "1000")),
        max_request_size=int(os.getenv("MAX_REQUEST_SIZE", str(1024 * 1024))),
        max_json_depth=int(os.getenv("MAX_JSON_DEPTH", "10")),
        max_json_keys=int(os.getenv("MAX_JSON_KEYS", "1000")),
        log_security_events=os.getenv("LOG_SECURITY_EVENTS", "true").lower() == "true",
        log_failed_auth_attempts=os.getenv("LOG_FAILED_AUTH", "true").lower() == "true",
    )


# Dangerous patterns for input validation (Requirement 6.4)
EXTENDED_DANGEROUS_PATTERNS = [
    # XSS patterns
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"vbscript:",
    r"data:text/html",
    
    # SQL injection patterns
    r"--",
    r";.*(?:drop|delete|truncate|alter|create|insert|update)",
    r"'\s*or\s*'",
    r"'\s*and\s*'",
    r"union\s+select",
    r"'\s*;\s*drop",
    r"'\s*;\s*delete",
    r"'\s*;\s*insert",
    r"'\s*;\s*update",
    
    # Template injection patterns
    r"\$\{.*\}",
    r"\{\{.*\}\}",
    r"<%.*%>",
    r"<\?php",
    
    # Command injection patterns
    r"exec\s*\(",
    r"eval\s*\(",
    r"system\s*\(",
    r"shell_exec\s*\(",
    r"passthru\s*\(",
    r"cmd\.exe",
    r"powershell",
    r"/bin/sh",
    r"/bin/bash",
    
    # Path traversal patterns
    r"\.\.\/",
    r"\.\.\\",
    r"\/etc\/passwd",
    r"\/proc\/",
    r"\\windows\\system32",
    
    # LDAP injection patterns
    r"\(\s*\|\s*\(",
    r"\(\s*&\s*\(",
    r"\*\)\s*\(",
    
    # NoSQL injection patterns
    r"\$where",
    r"\$ne",
    r"\$gt",
    r"\$lt",
    r"\$regex",
]


# Enhanced suspicious User-Agent patterns for comprehensive detection
SUSPICIOUS_USER_AGENTS = [
    # Security scanners and penetration testing tools
    r"sqlmap",  # SQL injection tool
    r"nikto",  # Web vulnerability scanner
    r"nmap",  # Network mapper
    r"masscan",  # Port scanner
    r"burp",  # Burp Suite
    r"zap",  # OWASP ZAP
    r"w3af",  # Web application attack framework
    r"acunetix",  # Web vulnerability scanner
    r"nessus",  # Vulnerability scanner
    r"openvas",  # Vulnerability scanner
    r"metasploit",  # Penetration testing framework
    r"havij",  # SQL injection tool
    r"pangolin",  # SQL injection tool
    r"dirbuster",  # Directory brute forcer
    r"dirb",  # Directory brute forcer
    r"gobuster",  # Directory brute forcer
    r"wfuzz",  # Web fuzzer
    r"ffuf",  # Fast web fuzzer
    r"hydra",  # Password cracker
    r"john",  # John the Ripper
    r"hashcat",  # Password recovery tool
    
    # Automated attack tools
    r"wget",  # Command line downloader
    r"curl",  # Command line tool (when used maliciously)
    r"python-requests",  # Python requests library (automated)
    r"libwww-perl",  # Perl library (automated)
    r"lwp-trivial",  # Perl library
    r"urllib",  # Python urllib (automated)
    r"httpclient",  # Generic HTTP client
    r"apache-httpclient",  # Apache HTTP client
    r"okhttp",  # OkHttp client
    
    # Malicious patterns in User-Agent
    r"<script",  # XSS attempt
    r"javascript:",  # JavaScript injection
    r"\.\.\/",  # Path traversal
    r"union\s+select",  # SQL injection
    r"<\?php",  # PHP injection
    r"<%.*%>",  # ASP injection
    r"\$\{.*\}",  # Template injection
    r"exec\s*\(",  # Code execution
    r"eval\s*\(",  # Code execution
    
    # Bot patterns (suspicious automation)
    r"bot\/0\.0",  # Fake bot version
    r"crawler\/0\.0",  # Fake crawler version
    r"spider\/0\.0",  # Fake spider version
    r"^bot$",  # Generic bot
    r"^crawler$",  # Generic crawler
    r"^spider$",  # Generic spider
    r"test",  # Test user agents
    r"scanner",  # Generic scanner
    r"exploit",  # Exploit tools
    r"attack",  # Attack tools
    r"hack",  # Hacking tools
    
    # Empty or minimal User-Agents (suspicious)
    r"^-$",  # Just a dash
    r"^\.$",  # Just a dot
    r"^x$",  # Single character
    r"^test$",  # Just "test"
    r"^mozilla$",  # Just "mozilla" (incomplete)
    
    # Encoded or obfuscated User-Agents
    r"%[0-9a-fA-F]{2}",  # URL encoded
    r"\\x[0-9a-fA-F]{2}",  # Hex encoded
    r"&#[0-9]+;",  # HTML entities
    r"&#x[0-9a-fA-F]+;",  # HTML hex entities
]


# Medical data validation ranges (Requirement 6.1)
MEDICAL_VALIDATION_RANGES = {
    "heart_rate": {
        "min": 30,
        "max": 200,
        "unit": "bpm",
        "critical_low": 40,
        "critical_high": 180,
    },
    "systolic_bp": {
        "min": 50,
        "max": 300,
        "unit": "mmHg",
        "critical_low": 70,
        "critical_high": 250,
    },
    "diastolic_bp": {
        "min": 20,
        "max": 200,
        "unit": "mmHg",
        "critical_low": 40,
        "critical_high": 150,
    },
    "respiratory_rate": {
        "min": 5,
        "max": 60,
        "unit": "breaths/min",
        "critical_low": 8,
        "critical_high": 40,
    },
    "oxygen_saturation": {
        "min": 50,
        "max": 100,
        "unit": "%",
        "critical_low": 70,
        "critical_high": 100,
    },
    "temperature": {
        "min": 30,
        "max": 45,
        "unit": "°C",
        "critical_low": 32,
        "critical_high": 42,
    },
}


def get_allowed_origins() -> List[str]:
    """
    Get allowed CORS origins from environment or defaults.
    
    Returns:
        List of allowed origins for CORS
    """
    origins_env = os.getenv("ALLOWED_ORIGINS", "*")
    if origins_env == "*":
        return ["*"]  # Allow all origins (development only)
    
    return [origin.strip() for origin in origins_env.split(",")]


def is_production_environment() -> bool:
    """
    Check if running in production environment.
    
    Returns:
        True if in production environment
    """
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def get_api_keys_from_env() -> Dict[str, Dict[str, any]]:
    """
    Load API keys from environment variables.
    
    Returns:
        Dictionary of API keys and their metadata
    """
    api_keys = {}
    
    # Demo API key
    demo_key = os.getenv("DEMO_API_KEY", "demo-api-key-12345678")
    if demo_key:
        api_keys[demo_key] = {
            "name": "Demo API Key",
            "permissions": ["read", "write"],
            "rate_limit": 1000,
            "is_active": True,
        }
    
    # Admin API key
    admin_key = os.getenv("ADMIN_API_KEY", "admin-api-key-87654321")
    if admin_key:
        api_keys[admin_key] = {
            "name": "Admin API Key",
            "permissions": ["read", "write", "admin"],
            "rate_limit": 10000,
            "is_active": True,
        }
    
    # Production API keys (comma-separated)
    prod_keys = os.getenv("PRODUCTION_API_KEYS", "")
    if prod_keys:
        for key in prod_keys.split(","):
            key = key.strip()
            if key:
                api_keys[key] = {
                    "name": "Production API Key",
                    "permissions": ["read", "write"],
                    "rate_limit": 5000,
                    "is_active": True,
                }
    
    return api_keys


# Security event types for logging
class SecurityEventType:
    """Security event types for comprehensive logging."""
    
    AUTHENTICATION_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_INPUT = "suspicious_input"
    INJECTION_ATTEMPT = "injection_attempt"
    PATH_TRAVERSAL = "path_traversal"
    INVALID_CONTENT_TYPE = "invalid_content_type"
    REQUEST_TOO_LARGE = "request_too_large"
    MALFORMED_JSON = "malformed_json"
    SUSPICIOUS_USER_AGENT = "suspicious_user_agent"
    INVALID_IP_ADDRESS = "invalid_ip_address"
    HEADER_VALIDATION_FAILURE = "header_validation_failure"


def log_security_event(
    event_type: str,
    request_id: str,
    details: Dict[str, any],
    severity: str = "medium"
) -> None:
    """
    Log security events with standardized format.
    
    Implements Requirement 6.5: Log detailed error information for security monitoring.
    
    Args:
        event_type: Type of security event
        request_id: Request identifier for tracing
        details: Event details (will be sanitized)
        severity: Event severity (low, medium, high, critical)
    """
    import logging
    from src.utils.validation import sanitize_log_message
    
    logger = logging.getLogger("security")
    
    # Sanitize details for safe logging
    safe_details = {}
    for key, value in details.items():
        if isinstance(value, str):
            safe_details[key] = sanitize_log_message(value)
        else:
            safe_details[key] = str(value)[:100]  # Limit non-string values
    
    log_message = (
        f"SECURITY_EVENT: {event_type} | "
        f"RequestID: {request_id} | "
        f"Severity: {severity} | "
        f"Details: {safe_details}"
    )
    
    # Log at appropriate level based on severity
    if severity == "critical":
        logger.critical(log_message)
    elif severity == "high":
        logger.error(log_message)
    elif severity == "medium":
        logger.warning(log_message)
    else:
        logger.info(log_message)