"""Text/JSON inference via direct Azure OpenAI or restricted Copilot transport."""

from .azure import AzureOpenAIProvider
from .copilot import CopilotProvider
from .contracts import (
    InferenceError,
    InferenceProvider,
    InferenceRequest,
    InferenceResponse,
)

__all__ = [
    "AzureOpenAIProvider",
    "CopilotProvider",
    "InferenceError",
    "InferenceProvider",
    "InferenceRequest",
    "InferenceResponse",
]
