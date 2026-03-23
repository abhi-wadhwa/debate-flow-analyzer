"""Debate format definitions for British Parliamentary, Policy/CX, and Lincoln-Douglas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class Side(Enum):
    """Which side of the debate a speaker is on."""

    PROPOSITION = "proposition"
    OPPOSITION = "opposition"
    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"
    # British Parliamentary has government/opposition
    GOVERNMENT = "government"


@dataclass(frozen=True)
class SpeechRole:
    """A single speech slot in a debate format."""

    label: str
    side: Side
    order: int
    duration_minutes: float
    is_rebuttal: bool = False
    is_crossex: bool = False


@dataclass(frozen=True)
class DebateFormat:
    """Complete definition of a debate format."""

    name: str
    description: str
    speeches: List[SpeechRole] = field(default_factory=list)
    sides: List[Side] = field(default_factory=list)
    speaker_labels: List[str] = field(default_factory=list)

    @property
    def speech_count(self) -> int:
        return len(self.speeches)

    @property
    def side_count(self) -> int:
        return len(self.sides)

    def get_speeches_for_side(self, side: Side) -> List[SpeechRole]:
        return [s for s in self.speeches if s.side == side]

    def get_speech_by_label(self, label: str) -> SpeechRole | None:
        for s in self.speeches:
            if s.label.lower() == label.lower():
                return s
        return None


# ---------------------------------------------------------------------------
# Pre-built format definitions
# ---------------------------------------------------------------------------

POLICY_CX = DebateFormat(
    name="Policy/CX",
    description=(
        "Cross-Examination (Policy) debate with 2 teams of 2 speakers each. "
        "Eight constructive/rebuttal speeches plus four cross-examination periods."
    ),
    sides=[Side.AFFIRMATIVE, Side.NEGATIVE],
    speaker_labels=[
        "1AC", "CX-1AC", "1NC", "CX-1NC",
        "2AC", "CX-2AC", "2NC", "CX-2NC",
        "1NR", "1AR", "2NR", "2AR",
    ],
    speeches=[
        SpeechRole(label="1AC", side=Side.AFFIRMATIVE, order=1, duration_minutes=8),
        SpeechRole(label="CX-1AC", side=Side.NEGATIVE, order=2, duration_minutes=3, is_crossex=True),
        SpeechRole(label="1NC", side=Side.NEGATIVE, order=3, duration_minutes=8),
        SpeechRole(label="CX-1NC", side=Side.AFFIRMATIVE, order=4, duration_minutes=3, is_crossex=True),
        SpeechRole(label="2AC", side=Side.AFFIRMATIVE, order=5, duration_minutes=8),
        SpeechRole(label="CX-2AC", side=Side.NEGATIVE, order=6, duration_minutes=3, is_crossex=True),
        SpeechRole(label="2NC", side=Side.NEGATIVE, order=7, duration_minutes=8),
        SpeechRole(label="CX-2NC", side=Side.AFFIRMATIVE, order=8, duration_minutes=3, is_crossex=True),
        SpeechRole(label="1NR", side=Side.NEGATIVE, order=9, duration_minutes=5, is_rebuttal=True),
        SpeechRole(label="1AR", side=Side.AFFIRMATIVE, order=10, duration_minutes=5, is_rebuttal=True),
        SpeechRole(label="2NR", side=Side.NEGATIVE, order=11, duration_minutes=5, is_rebuttal=True),
        SpeechRole(label="2AR", side=Side.AFFIRMATIVE, order=12, duration_minutes=5, is_rebuttal=True),
    ],
)

LINCOLN_DOUGLAS = DebateFormat(
    name="Lincoln-Douglas",
    description=(
        "One-on-one value debate format with constructive, "
        "cross-examination, and rebuttal speeches."
    ),
    sides=[Side.AFFIRMATIVE, Side.NEGATIVE],
    speaker_labels=["AC", "CX-AC", "NC", "CX-NC", "1AR", "NR", "2AR"],
    speeches=[
        SpeechRole(label="AC", side=Side.AFFIRMATIVE, order=1, duration_minutes=6),
        SpeechRole(label="CX-AC", side=Side.NEGATIVE, order=2, duration_minutes=3, is_crossex=True),
        SpeechRole(label="NC", side=Side.NEGATIVE, order=3, duration_minutes=7),
        SpeechRole(label="CX-NC", side=Side.AFFIRMATIVE, order=4, duration_minutes=3, is_crossex=True),
        SpeechRole(label="1AR", side=Side.AFFIRMATIVE, order=5, duration_minutes=4, is_rebuttal=True),
        SpeechRole(label="NR", side=Side.NEGATIVE, order=6, duration_minutes=6, is_rebuttal=True),
        SpeechRole(label="2AR", side=Side.AFFIRMATIVE, order=7, duration_minutes=3, is_rebuttal=True),
    ],
)

BRITISH_PARLIAMENTARY = DebateFormat(
    name="British Parliamentary",
    description=(
        "Four teams of two: Opening Government, Opening Opposition, "
        "Closing Government, Closing Opposition. Eight speeches total."
    ),
    sides=[Side.GOVERNMENT, Side.OPPOSITION],
    speaker_labels=[
        "PM", "LO", "DPM", "DLO",
        "MG", "MO", "GW", "OW",
    ],
    speeches=[
        SpeechRole(label="PM", side=Side.GOVERNMENT, order=1, duration_minutes=7),
        SpeechRole(label="LO", side=Side.OPPOSITION, order=2, duration_minutes=7),
        SpeechRole(label="DPM", side=Side.GOVERNMENT, order=3, duration_minutes=7),
        SpeechRole(label="DLO", side=Side.OPPOSITION, order=4, duration_minutes=7),
        SpeechRole(label="MG", side=Side.GOVERNMENT, order=5, duration_minutes=7),
        SpeechRole(label="MO", side=Side.OPPOSITION, order=6, duration_minutes=7),
        SpeechRole(label="GW", side=Side.GOVERNMENT, order=7, duration_minutes=7, is_rebuttal=True),
        SpeechRole(label="OW", side=Side.OPPOSITION, order=8, duration_minutes=7, is_rebuttal=True),
    ],
)

FORMAT_REGISTRY: Dict[str, DebateFormat] = {
    "policy": POLICY_CX,
    "cx": POLICY_CX,
    "lincoln-douglas": LINCOLN_DOUGLAS,
    "ld": LINCOLN_DOUGLAS,
    "british-parliamentary": BRITISH_PARLIAMENTARY,
    "bp": BRITISH_PARLIAMENTARY,
}


def get_format(name: str) -> DebateFormat:
    """Look up a debate format by name (case-insensitive).

    Raises ``KeyError`` if the format is not found.
    """
    key = name.lower().strip()
    if key not in FORMAT_REGISTRY:
        available = sorted({f.name for f in FORMAT_REGISTRY.values()})
        raise KeyError(
            f"Unknown debate format '{name}'. Available: {', '.join(available)}"
        )
    return FORMAT_REGISTRY[key]


def list_formats() -> List[str]:
    """Return the canonical names of all supported debate formats."""
    return sorted({f.name for f in FORMAT_REGISTRY.values()})
