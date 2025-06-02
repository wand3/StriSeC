class AppBaseException(Exception):
    """Base class for all application-specific exceptions."""
    def __init__(self, message, *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"


class ConfigError(AppBaseException):
    """Raised when configuration is invalid or missing."""
    def __init__(self, section=None, key=None, value=None, message=None):
        if not message:
            if section and key:
                message = f"Invalid config value for [{section}]->{key}"
                if value:
                    message += f" = '{value}'"
            else:
                message = "Configuration error"
        super().__init__(message)


class ServerError(AppBaseException):
    """Raised for generic server operational errors."""
    def __init__(self, operation, reason, details=None):
        message = f"Server error during {operation}: {reason}"
        if details:
            message += f" | Details: {details}"
        super().__init__(message)
        self.operation = operation
        self.reason = reason
        self.details = details


class ClientError(AppBaseException):
    """Base class for client-related errors."""
    def __init__(self, client_info, reason):
        ip, port = client_info
        message = f"Client error ({ip}:{port}): {reason}"
        super().__init__(message)
        self.client_ip = ip
        self.client_port = port
        self.reason = reason


class ClientConfigError(ClientError):
    """Raised for client configuration issues."""
    def __init__(self, client_info, key=None, value=None):
        reason = f"Invalid config"
        if key:
            reason += f" [{key}='{value}']" if value else f" [{key}]"
        super().__init__(client_info, reason)


class ClientProtocolError(ClientError):
    """Raised for protocol violations by client."""
    def __init__(self, client_info, violation):
        reason = f"Protocol violation: {violation}"
        super().__init__(client_info, reason)


class SecurityError(AppBaseException):
    """Base class for security-related exceptions."""
    def __init__(self, mechanism, reason):
        message = f"{mechanism} security failure: {reason}"
        super().__init__(message)


class SSLError(SecurityError):
    """Raised for SSL/TLS-related errors."""
    def __init__(self, operation, reason):
        super().__init__("SSL", f"{operation} failed - {reason}")


class FileSystemError(AppBaseException):
    """Raised for filesystem-related errors."""
    def __init__(self, operation, path, reason):
        message = f"File error during {operation} '{path}': {reason}"
        super().__init__(message)
        self.path = path
        self.operation = operation