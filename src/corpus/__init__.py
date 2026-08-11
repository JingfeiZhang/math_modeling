"""Evidence-grounded corpus tooling for the modeling workbench.

Exports are resolved lazily so ``python -m src.corpus.miner`` does not import the
CLI module twice and emit a runpy warning.
"""

from importlib import import_module

__all__ = [
    "PAPER_CARD_SCHEMA_VERSION",
    "build_paper_card",
    "classify_authenticity",
    "deduplicate_records",
    "scan_matlab_text",
    "scan_matlab_tree",
    "sync_git_tree",
    "validate_paper_card",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(name)
    return getattr(import_module(".miner", __name__), name)
