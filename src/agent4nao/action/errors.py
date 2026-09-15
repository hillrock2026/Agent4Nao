"""Action contract domain errors.

These errors are raised at the schema/validation boundary (construction and
``from_dict``) and are carried as typed categories by the Fake Execution Agent
rather than raised across its public ``submit`` boundary.
"""

from __future__ import annotations


class ActionError(Exception):
    """Base class for action-contract errors."""


class SchemaValidationError(ActionError):
    """A request/result failed schema validation."""


class SchemaVersionError(SchemaValidationError):
    """The request schema version is not supported."""


class UnknownFieldError(SchemaValidationError):
    """An unknown field was present where strict parsing is required."""


class InvalidParametersError(SchemaValidationError):
    """Capability parameters failed type, range, or shape validation."""


class InvalidIdentifierError(SchemaValidationError):
    """An identifier failed strict format validation (e.g. UUID)."""
