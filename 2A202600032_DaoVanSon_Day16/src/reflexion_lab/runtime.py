from __future__ import annotations

import os
from importlib import import_module


_MODULE_BY_RUNTIME = {
    "gemini": "src.reflexion_lab.gemini_runtime",
    "mock": "src.reflexion_lab.mock_runtime",
    "ollama": "src.reflexion_lab.ollama_runtime",
}


def get_runtime_name() -> str:
    runtime_name = os.getenv("REFLEXION_RUNTIME", "ollama").strip().lower()
    if runtime_name not in _MODULE_BY_RUNTIME:
        raise ValueError(f"Unsupported runtime: {runtime_name}")
    return runtime_name


def _runtime_module():
    return import_module(_MODULE_BY_RUNTIME[get_runtime_name()])


def actor_answer(*args, **kwargs):
    return _runtime_module().actor_answer(*args, **kwargs)


def evaluator(*args, **kwargs):
    return _runtime_module().evaluator(*args, **kwargs)


def reflector(*args, **kwargs):
    return _runtime_module().reflector(*args, **kwargs)
