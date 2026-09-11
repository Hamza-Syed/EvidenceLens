"""Public-safe service failures; provider details never become API error messages."""


class ServiceError(RuntimeError):
    pass


class ClaimExtractionError(ServiceError):
    pass


class EmbeddingError(ServiceError):
    pass


class EvidenceScopeError(ServiceError):
    pass


class VerifierOutputError(ServiceError):
    pass


class VerifierUnavailableError(ServiceError):
    pass
