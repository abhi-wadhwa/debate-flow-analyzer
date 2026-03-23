"""Argument extractor -- uses an LLM to identify arguments with claim/warrant/impact structure."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.llm_client import LLMClient
from src.core.parser import Speech


@dataclass
class Argument:
    """A single argument extracted from a speech."""

    id: str
    claim: str
    warrant: str
    impact: str
    speech_label: str
    side: str
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None  # If this is a rebuttal, reference the argument it responds to
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "claim": self.claim,
            "warrant": self.warrant,
            "impact": self.impact,
            "speech_label": self.speech_label,
            "side": self.side,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Argument":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            claim=d.get("claim", ""),
            warrant=d.get("warrant", ""),
            impact=d.get("impact", ""),
            speech_label=d.get("speech_label", ""),
            side=d.get("side", ""),
            tags=d.get("tags", []),
            parent_id=d.get("parent_id"),
            confidence=d.get("confidence", 1.0),
        )


EXTRACTION_SYSTEM_PROMPT = """You are a competitive debate analyst. Your task is to extract
structured arguments from debate speeches. Each argument should be decomposed into:

- claim: The central assertion being made
- warrant: The reasoning/evidence supporting the claim
- impact: The consequence or significance of the claim
- tags: Short keyword labels for the argument (e.g., "economy", "rights", "security")

If an argument is a rebuttal to a previously identified argument, include the parent_id
of the argument it responds to. If it is a new, independent contention, leave parent_id null.

Return ONLY valid JSON with the following structure:
{
  "arguments": [
    {
      "claim": "...",
      "warrant": "...",
      "impact": "...",
      "tags": ["..."],
      "parent_id": null or "id-of-parent-argument"
    }
  ]
}
"""


class ArgumentExtractor:
    """Extract structured arguments from debate speeches using an LLM."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_from_speech(
        self,
        speech: Speech,
        prior_arguments: Optional[List[Argument]] = None,
    ) -> List[Argument]:
        """Extract arguments from a single speech.

        Parameters
        ----------
        speech : Speech
            The speech to analyse.
        prior_arguments : list of Argument, optional
            Previously extracted arguments (for rebuttal linking).
        """
        prior_context = ""
        if prior_arguments:
            prior_listing = "\n".join(
                f"  - [{a.id}] ({a.speech_label}, {a.side}) Claim: {a.claim}"
                for a in prior_arguments
            )
            prior_context = (
                f"\n\nPreviously identified arguments (use their IDs for parent_id if rebutting):\n"
                f"{prior_listing}"
            )

        prompt = (
            f"Speech label: {speech.speaker_label}\n"
            f"Side: {speech.side}\n"
            f"Is rebuttal speech: {speech.is_rebuttal}\n\n"
            f"Speech text:\n{speech.text}"
            f"{prior_context}\n\n"
            f"Extract all arguments from this speech."
        )

        raw = self.llm.complete_json(prompt, system=EXTRACTION_SYSTEM_PROMPT)
        return self._parse_response(raw, speech)

    def extract_all(self, speeches: List[Speech]) -> List[Argument]:
        """Extract arguments from all speeches, threading rebuttal references."""
        all_arguments: List[Argument] = []
        for speech in speeches:
            if speech.is_crossex:
                continue  # Skip cross-examination periods
            new_args = self.extract_from_speech(speech, prior_arguments=all_arguments)
            all_arguments.extend(new_args)
        return all_arguments

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, data: Any, speech: Speech) -> List[Argument]:
        """Convert the LLM JSON output into ``Argument`` objects."""
        arguments: List[Argument] = []
        raw_args = data.get("arguments", []) if isinstance(data, dict) else []

        for item in raw_args:
            arg = Argument(
                id=str(uuid.uuid4())[:8],
                claim=item.get("claim", ""),
                warrant=item.get("warrant", ""),
                impact=item.get("impact", ""),
                speech_label=speech.speaker_label,
                side=speech.side,
                tags=item.get("tags", []),
                parent_id=item.get("parent_id"),
                confidence=item.get("confidence", 1.0),
            )
            arguments.append(arg)

        return arguments
