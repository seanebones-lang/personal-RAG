"""Parser plugin interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ExtractedDocument:
    """One logical document extracted from a file (may be one of many per file)."""

    text: str
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser:
    extensions: frozenset[str] = frozenset()

    def extract(self, file_path: Path) -> List[ExtractedDocument]:
        raise NotImplementedError
