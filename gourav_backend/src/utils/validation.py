"""
Input validation utilities for security and data integrity.
Implements Requirements 6.2, 6.4, and 6.5 for secure input handling.
"""

import logging
import re
import html
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Enhanced security patterns for comprehensive input sanitization (Requirement 6.4)
DANGEROUS_PATTERNS = [
    # XSS patterns (enhanced)
    r"<script[^>]*>.*?</script>",  # XSS script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"<iframe",  # XSS iframe
    r"<object",  # XSS object
    r"<embed",  # XSS embed
    r"<applet",  # Java applet
    r"<form",  # Form injection
    r"<input",  # Input injection
    r"<img[^>]*src\s*=\s*[\"']?javascript:",  # Image XSS
    r"<svg[^>]*onload",  # SVG XSS
    r"<link[^>]*href\s*=\s*[\"']?javascript:",  # Link XSS
    r"vbscript:",  # VBScript protocol
    r"data:text/html",  # Data URI XSS
    r"data:application/javascript",  # JavaScript data URI
    r"expression\s*\(",  # CSS expression
    r"@import",  # CSS import
    r"behavior\s*:",  # IE behavior
    
    # SQL injection patterns (enhanced)
    r"--",  # SQL comment
    r";.*(?:drop|delete|truncate|alter|create|insert|update)",  # SQL injection
    r"'\s*or\s*'",  # SQL injection OR
    r"'\s*and\s*'",  # SQL injection AND
    r"union\s+select",  # SQL injection UNION
    r"'\s*;\s*drop",  # Drop table injection
    r"'\s*;\s*delete",  # Delete injection
    r"'\s*;\s*insert",  # Insert injection
    r"'\s*;\s*update",  # Update injection
    r"0x[0-9a-fA-F]+",  # Hex encoded SQL
    r"char\s*\(",  # SQL char function
    r"ascii\s*\(",  # SQL ascii function
    r"substring\s*\(",  # SQL substring function
    r"waitfor\s+delay",  # SQL Server time delay
    r"pg_sleep\s*\(",  # PostgreSQL sleep
    r"sleep\s*\(",  # MySQL sleep
    r"benchmark\s*\(",  # MySQL benchmark
    
    # Template injection patterns (enhanced)
    r"\$\{.*\}",  # Template injection
    r"\{\{.*\}\}",  # Template injection
    r"\{%.*%\}",  # Jinja2 template injection
    r"\{\*.*\*\}",  # Smarty template injection
    r"<%.*%>",  # ASP/JSP code injection
    r"<\?php",  # PHP code injection
    r"<\?=",  # PHP short tag
    r"#\{.*\}",  # Ruby template injection
    r"\$\(.*\)",  # Shell command substitution
    r"`.*`",  # Backtick command execution
    
    # Command injection patterns (enhanced)
    r"exec\s*\(",  # Code execution
    r"eval\s*\(",  # Code execution
    r"system\s*\(",  # System command
    r"shell_exec\s*\(",  # Shell execution
    r"passthru\s*\(",  # Passthru execution
    r"popen\s*\(",  # Process open
    r"proc_open\s*\(",  # Process open
    r"cmd\.exe",  # Command execution
    r"powershell",  # PowerShell execution
    r"\/bin\/sh",  # Shell execution
    r"\/bin\/bash",  # Bash execution
    r"\/bin\/csh",  # C shell
    r"\/bin\/ksh",  # Korn shell
    r"\/bin\/zsh",  # Z shell
    r"cmd\s*\/c",  # Windows command
    r"start\s+",  # Windows start command
    
    # Path traversal patterns (enhanced)
    r"\.\.\/",  # Path traversal
    r"\.\.\\",  # Path traversal (Windows)
    r"\/etc\/passwd",  # File inclusion
    r"\/etc\/shadow",  # Shadow file
    r"\/proc\/",  # System file access
    r"\/sys\/",  # System file access
    r"\/dev\/",  # Device file access
    r"\\windows\\system32",  # Windows system files
    r"\\windows\\temp",  # Windows temp files
    r"c:\\windows",  # Windows drive access
    r"file:\/\/",  # File protocol
    r"ftp:\/\/",  # FTP protocol
    
    # LDAP injection patterns
    r"\(\s*\|\s*\(",  # LDAP OR
    r"\(\s*&\s*\(",  # LDAP AND
    r"\*\)\s*\(",  # LDAP wildcard
    r"\)\s*\(",  # LDAP parentheses
    
    # NoSQL injection patterns
    r"\$where",  # MongoDB where
    r"\$ne",  # MongoDB not equal
    r"\$gt",  # MongoDB greater than
    r"\$lt",  # MongoDB less than
    r"\$gte",  # MongoDB greater than or equal
    r"\$lte",  # MongoDB less than or equal
    r"\$regex",  # MongoDB regex
    r"\$in",  # MongoDB in
    r"\$nin",  # MongoDB not in
    r"\$exists",  # MongoDB exists
    r"\$type",  # MongoDB type
    
    # XML/XXE injection patterns
    r"<!ENTITY",  # XML entity
    r"<!DOCTYPE",  # XML doctype
    r"SYSTEM\s+[\"']",  # XML system entity
    r"PUBLIC\s+[\"']",  # XML public entity
    r"<\?xml",  # XML declaration
    
    # Server-side includes
    r"<!--#",  # SSI directive
    r"#exec",  # SSI exec
    r"#include",  # SSI include
    
    # Additional dangerous patterns
    r"\\x[0-9a-fA-F]{2}",  # Hex encoded characters
    r"%[0-9a-fA-F]{2}",  # URL encoded characters
    r"&#x[0-9a-fA-F]+;",  # HTML hex entities
    r"&#[0-9]+;",  # HTML decimal entities
    r"\\u[0-9a-fA-F]{4}",  # Unicode escape sequences
    r"\\[rnt]",  # Escape sequences
]

# Additional security patterns for patient ID validation
PATIENT_ID_DANGEROUS_PATTERNS = [
    r"[<>\"'&]",  # HTML/XML special characters
    r"[\x00-\x1f\x7f-\x9f]",  # Control characters
    r"\\x[0-9a-fA-F]{2}",  # Hex encoded characters
    r"%[0-9a-fA-F]{2}",  # URL encoded characters
]

# Content-Type validation patterns
ALLOWED_CONTENT_TYPES = [
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
]

# Maximum field lengths for validation
MAX_FIELD_LENGTHS = {
    "patient_id": 50,
    "recorded_by": 100,
    "model_version": 50,
    "general_string": 500,
}

# Allowed characters for different field types
SAFE_PATIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
SAFE_ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s_\-\.]+$')


def sanitize_string(value: str) -> str:
    """
    Sanitize a string value to prevent injection attacks.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        value: The string to sanitize
        
    Returns:
        Sanitized string with dangerous patterns removed
        
    Raises:
        ValueError: If the input contains too many dangerous patterns (potential attack)
    """
    if not isinstance(value, str):
        return value
    
    # Use enhanced sanitization
    return advanced_input_sanitization(value, "general")


def validate_patient_id(patient_id: str) -> str:
    """
    Validate and sanitize patient ID according to security requirements.
    
    Implements Requirement 6.2: Clear error messages for invalid patient IDs.
    Implements Requirement 6.4: Input sanitization for patient identifiers.
    
    Args:
        patient_id: Patient identifier to validate
        
    Returns:
        Sanitized patient ID
        
    Raises:
        ValueError: If patient ID is invalid or contains dangerous patterns
    """
    if not patient_id or not isinstance(patient_id, str):
        raise ValueError("Patient ID must be a non-empty string")
    
    # Check for dangerous patterns specific to patient IDs
    for pattern in PATIENT_ID_DANGEROUS_PATTERNS:
        if re.search(pattern, patient_id):
            raise ValueError("Patient ID contains invalid characters")
    
    # Basic format validation
    if len(patient_id.strip()) == 0:
        raise ValueError("Patient ID cannot be empty or whitespace only")
    
    if len(patient_id) > 50:
        raise ValueError("Patient ID cannot exceed 50 characters")
    
    # Check for suspicious patterns that might indicate injection attempts
    if any(keyword in patient_id.lower() for keyword in ['select', 'drop', 'delete', 'insert', 'update', 'union']):
        raise ValueError("Patient ID contains invalid content")
    
    sanitized_id = sanitize_string(patient_id)
    
    # Ensure sanitization didn't remove too much content
    if len(sanitized_id) < len(patient_id) * 0.9:
        raise ValueError("Patient ID contains too many invalid characters")
    
    return sanitized_id


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


def validate_medical_ranges(vital_signs: Dict[str, float]) -> List[str]:
    """
    Validate vital signs are within medically acceptable ranges.
    
    Implements Requirement 6.1: Validate measurements against medical ranges.
    
    Args:
        vital_signs: Dictionary of vital sign measurements
        
    Returns:
        List of validation error messages (empty if all valid)
    """
    errors = []
    
    # Define medical ranges (extended for critical cases)
    ranges = {
        "heart_rate": (30, 200, "bpm"),
        "systolic_bp": (50, 300, "mmHg"),
        "diastolic_bp": (20, 200, "mmHg"),
        "respiratory_rate": (5, 60, "breaths/min"),
        "oxygen_saturation": (50, 100, "%"),
        "temperature": (30, 45, "°C"),
    }
    
    for field, (min_val, max_val, unit) in ranges.items():
        if field in vital_signs:
            value = vital_signs[field]
            if not isinstance(value, (int, float)):
                errors.append(f"{field} must be a number")
            elif value < min_val or value > max_val:
                errors.append(f"{field} must be between {min_val} and {max_val} {unit}")
    
    # Additional validation: Blood pressure relationship
    if "systolic_bp" in vital_signs and "diastolic_bp" in vital_signs:
        if vital_signs["diastolic_bp"] >= vital_signs["systolic_bp"]:
            errors.append("Diastolic blood pressure must be less than systolic blood pressure")
    
    return errors


def validate_time_range(start_time, end_time) -> List[str]:
    """
    Validate time range parameters.
    
    Args:
        start_time: Start datetime
        end_time: End datetime
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if start_time and end_time:
        if start_time >= end_time:
            errors.append("Start time must be before end time")
    
    return errors


def is_suspicious_input(text: str) -> bool:
    """
    Check if input text contains suspicious patterns that might indicate an attack.
    
    Args:
        text: Text to check
        
    Returns:
        True if suspicious patterns detected
    """
    if not isinstance(text, str):
        return False
    
    suspicious_count = 0
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            suspicious_count += 1
    
    return suspicious_count > 0


def create_safe_error_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create safe error details that don't expose sensitive information.
    
    Implements Requirement 6.5: User-friendly error messages without exposing 
    sensitive system information.
    
    Args:
        details: Original error details
        
    Returns:
        Sanitized error details safe for client response
    """
    if not details:
        return {}
    
    # Only include safe, non-sensitive details
    safe_keys = {
        "field", "fields", "validation_errors", "allowed_values", 
        "request_id", "error_count", "retry_after", "supported_formats",
        "min_value", "max_value", "expected_format"
    }
    
    safe_details = {}
    for key, value in details.items():
        if key in safe_keys:
            # Sanitize the detail values as well
            if isinstance(value, str):
                safe_details[key] = sanitize_string(value)
            elif isinstance(value, list):
                safe_details[key] = [
                    sanitize_string(item) if isinstance(item, str) else item 
                    for item in value
                ]
            else:
                safe_details[key] = value
    
    return safe_details


def html_escape(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS attacks.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        text: Text to escape
        
    Returns:
        HTML-escaped text
    """
    if not isinstance(text, str):
        return text
    return html.escape(text, quote=True)


def validate_content_type(content_type: Optional[str]) -> bool:
    """
    Validate that the content type is allowed.
    
    Implements Requirement 6.4: Input sanitization and security measures.
    
    Args:
        content_type: Content-Type header value
        
    Returns:
        True if content type is allowed
    """
    if not content_type:
        return False
    
    # Extract base content type (without charset or boundary)
    base_type = content_type.split(";")[0].strip().lower()
    return base_type in ALLOWED_CONTENT_TYPES


def validate_field_length(value: str, field_name: str, max_length: Optional[int] = None) -> str:
    """
    Validate that a field value doesn't exceed maximum length.
    
    Implements Requirement 6.4: Input sanitization and security measures.
    
    Args:
        value: Field value to validate
        field_name: Name of the field for error messages
        max_length: Optional custom max length (uses default if not provided)
        
    Returns:
        Validated value
        
    Raises:
        ValueError: If value exceeds maximum length
    """
    if not isinstance(value, str):
        return value
    
    limit = max_length or MAX_FIELD_LENGTHS.get(field_name, MAX_FIELD_LENGTHS["general_string"])
    
    if len(value) > limit:
        raise ValueError(f"{field_name} cannot exceed {limit} characters")
    
    return value


def sanitize_for_logging(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for safe logging without exposing sensitive data.
    
    Implements Requirement 6.5: Log detailed error information while returning 
    user-friendly error messages.
    
    Args:
        text: Text to sanitize for logging
        max_length: Maximum length of logged text
        
    Returns:
        Sanitized text safe for logging
    """
    if not isinstance(text, str):
        return str(text)[:max_length]
    
    # Remove control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


def validate_json_depth(data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
    """
    Validate that JSON data doesn't exceed maximum nesting depth.
    
    Prevents deeply nested JSON attacks that could cause stack overflow.
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        data: JSON data to validate
        max_depth: Maximum allowed nesting depth
        current_depth: Current depth (used for recursion)
        
    Returns:
        True if depth is within limits
        
    Raises:
        ValueError: If depth exceeds maximum
    """
    if current_depth > max_depth:
        raise ValueError(f"JSON nesting depth exceeds maximum of {max_depth}")
    
    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, max_depth, current_depth + 1)
    
    return True


def validate_json_size(data: Any, max_keys: int = 1000, current_keys: int = 0) -> bool:
    """
    Validate that JSON data doesn't contain too many keys (DoS protection).
    
    Prevents JSON bomb attacks with excessive key counts.
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        data: JSON data to validate
        max_keys: Maximum allowed total keys
        current_keys: Current key count (used for recursion)
        
    Returns:
        True if key count is within limits
        
    Raises:
        ValueError: If key count exceeds maximum
    """
    if current_keys > max_keys:
        raise ValueError(f"JSON key count exceeds maximum of {max_keys}")
    
    if isinstance(data, dict):
        current_keys += len(data)
        if current_keys > max_keys:
            raise ValueError(f"JSON key count exceeds maximum of {max_keys}")
        
        for value in data.values():
            current_keys = validate_json_size(value, max_keys, current_keys)
    elif isinstance(data, list):
        for item in data:
            current_keys = validate_json_size(item, max_keys, current_keys)
    
    return current_keys


def sanitize_numeric_input(value: Union[int, float, str], field_name: str) -> float:
    """
    Sanitize and validate numeric input.
    
    Implements Requirement 6.4: Input sanitization and security measures.
    
    Args:
        value: Numeric value to sanitize
        field_name: Name of the field for error messages
        
    Returns:
        Sanitized float value
        
    Raises:
        ValueError: If value is not a valid number
    """
    if isinstance(value, (int, float)):
        if not (-1e10 < value < 1e10):  # Reasonable bounds
            raise ValueError(f"{field_name} value is out of acceptable range")
        return float(value)
    
    if isinstance(value, str):
        # Remove whitespace and validate
        cleaned = value.strip()
        try:
            result = float(cleaned)
            if not (-1e10 < result < 1e10):
                raise ValueError(f"{field_name} value is out of acceptable range")
            return result
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be a valid number")
    
    raise ValueError(f"{field_name} must be a valid number")


def validate_api_key_format(api_key: Optional[str]) -> bool:
    """
    Validate API key format for authentication.
    
    Implements Requirement 6.4: Security measures including authentication.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if API key format is valid
    """
    if not api_key:
        return False
    
    # API key should be alphanumeric with optional dashes/underscores
    # Minimum 16 characters for security
    if len(api_key) < 16 or len(api_key) > 128:
        return False
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9_\-]+$', api_key):
        return False
    
    return True


def create_safe_error_response(
    error_code: str,
    user_message: str,
    error_id: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a safe error response that doesn't expose sensitive information.
    
    Implements Requirement 6.5: User-friendly error messages without exposing 
    sensitive system information.
    
    Args:
        error_code: Error code for categorization
        user_message: User-friendly error message
        error_id: Unique error identifier for tracking
        details: Optional additional details (will be sanitized)
        
    Returns:
        Safe error response dictionary
    """
    response = {
        "error_code": sanitize_string(error_code),
        "message": sanitize_string(user_message),
        "error_id": error_id,
    }
    
    if details:
        response["details"] = create_safe_error_details(details)
    
    return response


def validate_request_headers(headers: Dict[str, str]) -> List[str]:
    """
    Validate request headers for security issues.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        headers: Request headers to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check for suspicious header values
    for name, value in headers.items():
        if not isinstance(value, str):
            continue
            
        # Check for injection patterns in headers
        if is_suspicious_input(value):
            errors.append(f"Header '{name}' contains potentially malicious content")
        
        # Check header length (prevent header bomb attacks)
        if len(value) > 8192:  # 8KB max per header
            errors.append(f"Header '{name}' exceeds maximum length")
        
        # Check for null bytes and control characters
        if '\x00' in value or any(ord(c) < 32 and c not in '\t\r\n' for c in value):
            errors.append(f"Header '{name}' contains invalid characters")
    
    # Check total header count (prevent header bomb attacks)
    if len(headers) > 100:
        errors.append("Too many request headers")
    
    return errors


def validate_user_agent(user_agent: Optional[str]) -> bool:
    """
    Validate User-Agent header for suspicious patterns.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        user_agent: User-Agent header value
        
    Returns:
        True if User-Agent appears legitimate
    """
    if not user_agent:
        return True  # Allow empty user agent
    
    # Check for suspicious patterns in User-Agent
    suspicious_patterns = [
        r"<script",  # XSS attempts
        r"javascript:",  # JavaScript injection
        r"sqlmap",  # SQL injection tool
        r"nikto",  # Security scanner
        r"nmap",  # Network scanner
        r"masscan",  # Port scanner
        r"\.\.\/",  # Path traversal
        r"union\s+select",  # SQL injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return False
    
    return True


def sanitize_log_message(message: str, max_length: int = 500) -> str:
    """
    Sanitize log messages to prevent log injection attacks.
    
    Implements Requirement 6.5: Log detailed error information while returning 
    user-friendly error messages.
    
    Args:
        message: Log message to sanitize
        max_length: Maximum length of sanitized message
        
    Returns:
        Sanitized log message
    """
    if not isinstance(message, str):
        message = str(message)
    
    # Remove control characters that could break log format
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", message)
    
    # Remove ANSI escape sequences
    sanitized = re.sub(r"\x1b\[[0-9;]*m", "", sanitized)
    
    # Replace newlines and tabs to prevent log injection
    sanitized = sanitized.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate IP address format and check for suspicious patterns.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        ip_address: IP address to validate
        
    Returns:
        True if IP address is valid and not suspicious
    """
    if not ip_address:
        return False
    
    # Basic IPv4 validation
    ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    
    # Basic IPv6 validation (simplified)
    ipv6_pattern = r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::1$|^::$"
    
    if not (re.match(ipv4_pattern, ip_address) or re.match(ipv6_pattern, ip_address)):
        return False
    
    # Check for private/internal IP ranges that might indicate spoofing
    # This is informational - we don't reject private IPs but log them
    private_ranges = [
        r"^10\.",  # 10.0.0.0/8
        r"^172\.(1[6-9]|2[0-9]|3[01])\.",  # 172.16.0.0/12
        r"^192\.168\.",  # 192.168.0.0/16
        r"^127\.",  # 127.0.0.0/8 (loopback)
        r"^169\.254\.",  # 169.254.0.0/16 (link-local)
    ]
    
    return True  # All valid IPs are accepted


def advanced_input_sanitization(value: str, field_type: str = "general") -> str:
    """
    Advanced input sanitization with field-specific rules.
    
    Implements Requirement 6.4: Comprehensive input sanitization to prevent 
    injection attacks and data corruption.
    
    Args:
        value: The string to sanitize
        field_type: Type of field (patient_id, medical_data, general, etc.)
        
    Returns:
        Sanitized string with dangerous patterns removed
        
    Raises:
        ValueError: If the input contains too many dangerous patterns (potential attack)
    """
    if not isinstance(value, str):
        return value
    
    original_value = value
    sanitized = value
    dangerous_count = 0
    
    # Enhanced pattern detection with field-specific rules
    patterns_to_check = DANGEROUS_PATTERNS.copy()
    
    # Add field-specific patterns
    if field_type == "patient_id":
        patterns_to_check.extend(PATIENT_ID_DANGEROUS_PATTERNS)
    elif field_type == "medical_data":
        # Medical data should not contain any code-like patterns
        patterns_to_check.extend([
            r"function\s*\(",  # Function definitions
            r"class\s+\w+",  # Class definitions
            r"import\s+\w+",  # Import statements
            r"require\s*\(",  # Require statements
            r"include\s*\(",  # Include statements
        ])
    
    # Count and remove dangerous patterns with enhanced detection
    for pattern in patterns_to_check:
        matches = re.findall(pattern, sanitized, flags=re.IGNORECASE | re.MULTILINE)
        if matches:
            dangerous_count += len(matches)
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.MULTILINE)
    
    # Enhanced threat detection - lower threshold for medical data
    threat_threshold = 2 if field_type == "medical_data" else 3
    if dangerous_count > threat_threshold:
        logger.warning(f"Potential attack detected: {dangerous_count} dangerous patterns in {field_type} field")
        raise ValueError(f"Input contains potentially malicious content for {field_type} field")
    
    # Enhanced character filtering
    # Remove null bytes and control characters
    sanitized = sanitized.replace("\x00", "")
    sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)
    
    # Remove Unicode control characters
    sanitized = re.sub(r"[\u0000-\u001f\u007f-\u009f]", "", sanitized)
    
    # Remove zero-width characters that could be used for obfuscation
    zero_width_chars = [
        "\u200b",  # Zero width space
        "\u200c",  # Zero width non-joiner
        "\u200d",  # Zero width joiner
        "\u2060",  # Word joiner
        "\ufeff",  # Zero width no-break space
    ]
    for char in zero_width_chars:
        sanitized = sanitized.replace(char, "")
    
    # Normalize Unicode to prevent bypass attempts
    import unicodedata
    sanitized = unicodedata.normalize('NFKC', sanitized)
    
    # Log if significant sanitization occurred
    if len(sanitized) < len(original_value) * 0.7:
        logger.warning(
            f"Significant content removed during sanitization: "
            f"{len(original_value)} -> {len(sanitized)} chars in {field_type} field"
        )
    
    return sanitized.strip()


def validate_file_upload_security(filename: str, content_type: str, file_size: int) -> List[str]:
    """
    Validate file upload security to prevent malicious file uploads.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        filename: Name of the uploaded file
        content_type: MIME type of the file
        file_size: Size of the file in bytes
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not filename:
        errors.append("Filename is required")
        return errors
    
    # Sanitize filename
    try:
        safe_filename = advanced_input_sanitization(filename, "filename")
    except ValueError as e:
        errors.append(f"Filename contains malicious content: {e}")
        return errors
    
    # Check for dangerous file extensions
    dangerous_extensions = [
        ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".js", ".jar",
        ".php", ".asp", ".aspx", ".jsp", ".py", ".rb", ".pl", ".sh", ".ps1",
        ".dll", ".so", ".dylib", ".app", ".deb", ".rpm", ".msi", ".dmg"
    ]
    
    filename_lower = safe_filename.lower()
    for ext in dangerous_extensions:
        if filename_lower.endswith(ext):
            errors.append(f"File type '{ext}' is not allowed")
    
    # Check for double extensions (e.g., file.txt.exe)
    if filename_lower.count('.') > 1:
        parts = filename_lower.split('.')
        if len(parts) > 2 and any(ext.lstrip('.') in parts for ext in dangerous_extensions):
            errors.append("Files with multiple extensions are not allowed")
    
    # Validate content type
    allowed_content_types = [
        "text/plain", "text/csv", "application/json", "application/xml",
        "image/jpeg", "image/png", "image/gif", "application/pdf"
    ]
    
    if content_type not in allowed_content_types:
        errors.append(f"Content type '{content_type}' is not allowed")
    
    # Check file size (max 10MB for security)
    max_file_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_file_size:
        errors.append(f"File size ({file_size} bytes) exceeds maximum allowed ({max_file_size} bytes)")
    
    # Check for path traversal in filename
    if "../" in safe_filename or "..\\" in safe_filename:
        errors.append("Filename contains path traversal sequences")
    
    # Check for null bytes in filename
    if "\x00" in filename:
        errors.append("Filename contains null bytes")
    
    return errors


def detect_encoding_attacks(value: str) -> List[str]:
    """
    Detect various encoding-based attack attempts.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        value: String value to check for encoding attacks
        
    Returns:
        List of detected attack patterns
    """
    attacks = []
    
    if not isinstance(value, str):
        return attacks
    
    # URL encoding attacks
    if re.search(r"%[0-9a-fA-F]{2}", value):
        # Check for encoded dangerous characters
        dangerous_encoded = [
            "%3C",  # <
            "%3E",  # >
            "%22",  # "
            "%27",  # '
            "%3B",  # ;
            "%2D%2D",  # --
            "%2F",  # /
            "%5C",  # \
        ]
        for encoded in dangerous_encoded:
            if encoded.lower() in value.lower():
                attacks.append(f"URL encoded attack pattern: {encoded}")
    
    # HTML entity encoding attacks
    if re.search(r"&#[0-9]+;", value) or re.search(r"&#x[0-9a-fA-F]+;", value):
        attacks.append("HTML entity encoding detected")
    
    # Unicode escape attacks
    if re.search(r"\\u[0-9a-fA-F]{4}", value):
        attacks.append("Unicode escape sequence detected")
    
    # Hex encoding attacks
    if re.search(r"\\x[0-9a-fA-F]{2}", value):
        attacks.append("Hex encoding detected")
    
    # Base64 encoding (suspicious in certain contexts)
    import base64
    try:
        if len(value) > 20 and len(value) % 4 == 0:
            decoded = base64.b64decode(value, validate=True)
            decoded_str = decoded.decode('utf-8', errors='ignore')
            if any(pattern in decoded_str.lower() for pattern in ['script', 'javascript', 'eval', 'exec']):
                attacks.append("Suspicious Base64 encoded content")
    except Exception:
        pass  # Not valid Base64, which is fine
    
    return attacks


def validate_json_structure_security(data: Any, max_depth: int = 10, max_keys: int = 1000) -> List[str]:
    """
    Enhanced JSON structure validation for security.
    
    Implements Requirement 6.4: Input sanitization to prevent injection attacks.
    
    Args:
        data: JSON data to validate
        max_depth: Maximum allowed nesting depth
        max_keys: Maximum allowed total keys
        
    Returns:
        List of security issues found
    """
    issues = []
    
    try:
        validate_json_depth(data, max_depth)
    except ValueError as e:
        issues.append(str(e))
    
    try:
        validate_json_size(data, max_keys)
    except ValueError as e:
        issues.append(str(e))
    
    # Check for suspicious key names
    def check_keys(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check for dangerous key names
                if any(pattern in key.lower() for pattern in ['script', 'eval', 'exec', 'function', '__']):
                    issues.append(f"Suspicious key name at {path}.{key}")
                
                # Check for encoded keys
                encoding_attacks = detect_encoding_attacks(key)
                if encoding_attacks:
                    issues.append(f"Encoded key detected at {path}.{key}: {', '.join(encoding_attacks)}")
                
                # Recursively check nested objects
                check_keys(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_keys(item, f"{path}[{i}]" if path else f"[{i}]")
    
    check_keys(data)
    
    return issues


def comprehensive_request_validation(
    headers: Dict[str, str],
    query_params: Dict[str, str],
    body: Optional[str] = None,
    client_ip: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Comprehensive validation of entire HTTP request for security issues.
    
    Implements Requirement 6.4: Comprehensive input sanitization to prevent 
    injection attacks and data corruption.
    
    Args:
        headers: Request headers
        query_params: Query parameters
        body: Request body (if any)
        client_ip: Client IP address
        
    Returns:
        Dictionary of validation issues by category
    """
    issues = {
        "headers": [],
        "query_params": [],
        "body": [],
        "client_ip": [],
        "encoding_attacks": [],
        "suspicious_patterns": []
    }
    
    # Validate headers
    issues["headers"] = validate_request_headers(headers)
    
    # Validate User-Agent specifically
    user_agent = headers.get("user-agent")
    if user_agent and not validate_user_agent(user_agent):
        issues["headers"].append("Suspicious User-Agent detected")
    
    # Validate query parameters
    for key, value in query_params.items():
        try:
            sanitized = advanced_input_sanitization(value, "query_param")
            if sanitized != value:
                issues["query_params"].append(f"Suspicious content in parameter '{key}'")
        except ValueError as e:
            issues["query_params"].append(f"Malicious content in parameter '{key}': {e}")
        
        # Check for encoding attacks in parameters
        encoding_attacks = detect_encoding_attacks(value)
        if encoding_attacks:
            issues["encoding_attacks"].extend([f"Query param '{key}': {attack}" for attack in encoding_attacks])
    
    # Validate request body
    if body:
        try:
            # Check for encoding attacks in body
            encoding_attacks = detect_encoding_attacks(body)
            if encoding_attacks:
                issues["encoding_attacks"].extend([f"Request body: {attack}" for attack in encoding_attacks])
            
            # If it's JSON, validate structure
            if body.strip().startswith('{') or body.strip().startswith('['):
                try:
                    import json
                    json_data = json.loads(body)
                    json_issues = validate_json_structure_security(json_data)
                    issues["body"].extend(json_issues)
                except json.JSONDecodeError:
                    pass  # Not JSON, skip JSON-specific validation
        except Exception as e:
            issues["body"].append(f"Error validating request body: {e}")
    
    # Validate client IP
    if client_ip and not validate_ip_address(client_ip):
        issues["client_ip"].append("Invalid client IP address format")
    
    return issues