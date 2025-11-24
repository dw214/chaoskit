"""Custom exception hierarchy for Chaos Mesh SDK."""


class ChaosMeshSDKError(Exception):
    """Base exception for all Chaos Mesh SDK errors."""
    pass


class ChaosMeshConnectionError(ChaosMeshSDKError):
    """Raised when unable to connect to Kubernetes API server."""
    pass


class ExperimentAlreadyExistsError(ChaosMeshSDKError):
    """Raised when attempting to create an experiment that already exists (HTTP 409)."""
    pass


class ChaosResourceNotFoundError(ChaosMeshSDKError):
    """Raised when attempting to access a non-existent chaos experiment (HTTP 404)."""
    pass


class AmbiguousSelectorError(ChaosMeshSDKError):
    """Raised when selector configuration is ambiguous or conflicting."""
    pass


class ExperimentTimeoutError(ChaosMeshSDKError):
    """Raised when waiting for experiment status exceeds timeout."""
    pass


class ValidationError(ChaosMeshSDKError):
    """Raised when input validation fails."""
    pass