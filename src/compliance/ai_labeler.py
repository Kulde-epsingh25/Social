"""AI content labeling per IT Rules 2026 / SGI requirements."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.config.settings import settings

logger = logging.getLogger(__name__)


class AILabeler:
    """Adds mandatory AI-Generated labels to content before publication."""

    def __init__(self) -> None:
        self._prefix = settings.ai_label_prefix

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_label(self, content: str) -> str:
        """Prepend the configured AI-Generated label to *content*."""
        if content.startswith(self._prefix):
            return content  # idempotent
        return f"{self._prefix} {content}"

    def add_metadata(self, content: str) -> dict[str, Any]:
        """Return a metadata envelope conforming to SGI labeling requirements."""
        return {
            "content": content,
            "ai_generated": True,
            "label": self._prefix,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "system": "AutonomousPoliticalAccountabilitySystem",
            "version": "1.0.0",
            "compliance": {
                "it_rules_2026": True,
                "sgi_labeled": True,
            },
        }

    def format_for_x(self, content: str, analysis: dict[str, Any]) -> str:
        """Format *content* for X, embedding label and key metadata as a footer.

        The metadata is compact so as not to consume the 280-char budget on
        each tweet; only the first part of a thread receives the full label.
        """
        labeled = self.add_label(content)
        frameworks = analysis.get("frameworks", [])
        framework_str = (
            f" [{', '.join(frameworks[:2])}]" if frameworks else ""
        )
        # Append a compact attribution note if there is room.
        footer = f"\n{self._prefix}{framework_str}"
        # Only append footer if content doesn't already contain label.
        if self._prefix not in content:
            return labeled
        return content + footer
