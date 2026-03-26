"""Public SDK exceptions."""


class AgentOSError(Exception):
    """Base class for AgentOS client errors."""


class PolicyViolationError(AgentOSError):
    """Raised when the server reports a policy block or violation."""
