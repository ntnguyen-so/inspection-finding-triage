"""Public source-first knowledge API."""
from importlib import import_module

_EXPORTS = {
    "SourceDocument": ("source", "SourceDocument"),
    "extract_code": ("source", "extract_code"),
    "validate_proposal": ("source", "validate_proposal"),
    "extraction_request": ("source", "extraction_request"),
    "SourceKnowledgeStore": ("source_store", "SourceKnowledgeStore"),
    "get_triage_knowledge": ("retrieval", "get_triage_knowledge"),
    "binding_from_tables": ("retrieval", "binding_from_tables"),
    "strategy_binding": ("retrieval", "strategy_binding"),
    "SourceContext": ("source_context", "SourceContext"),
    "build_source_context": ("source_context", "build_source_context"),
    "validate_source_context": ("source_context", "validate_source_context"),
}
for _name in (
    "KnowledgeError", "TableSource",
):
    _EXPORTS[_name] = ("contracts", _name)

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, symbol = _EXPORTS[name]
    value = getattr(import_module("." + module, __name__), symbol)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_EXPORTS))
