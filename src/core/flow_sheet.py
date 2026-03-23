"""Flow sheet generator -- organise arguments into columns by speech with response arrows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.core.extractor import Argument


@dataclass
class FlowArrow:
    """A directed link between two arguments (source rebuts target)."""

    source_id: str
    target_id: str
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
        }


@dataclass
class FlowColumn:
    """A single column on the flow sheet, representing one speech."""

    speech_label: str
    side: str
    order: int
    arguments: List[Argument] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speech_label": self.speech_label,
            "side": self.side,
            "order": self.order,
            "arguments": [a.to_dict() for a in self.arguments],
        }


class FlowSheet:
    """Build and query a debate flow sheet.

    The flow sheet arranges arguments into columns (one per speech) and
    tracks rebuttal arrows between them.
    """

    def __init__(self) -> None:
        self.columns: List[FlowColumn] = []
        self.arrows: List[FlowArrow] = []
        self._arg_index: Dict[str, Argument] = {}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def build(self, arguments: List[Argument], speech_order: Optional[List[str]] = None) -> None:
        """Populate the flow sheet from a list of arguments.

        Parameters
        ----------
        arguments : list of Argument
            All extracted arguments (already tagged with speech_label / side).
        speech_order : list of str, optional
            Explicit ordering of speech labels.  If ``None``, the order is
            inferred from the arguments' appearance.
        """
        self._arg_index = {a.id: a for a in arguments}

        # Group arguments by speech label, preserving order
        seen_labels: List[str] = []
        groups: Dict[str, List[Argument]] = {}
        for arg in arguments:
            if arg.speech_label not in groups:
                groups[arg.speech_label] = []
                seen_labels.append(arg.speech_label)
            groups[arg.speech_label].append(arg)

        label_order = speech_order if speech_order else seen_labels

        self.columns = []
        for idx, label in enumerate(label_order):
            args_in_col = groups.get(label, [])
            side = args_in_col[0].side if args_in_col else ""
            self.columns.append(
                FlowColumn(
                    speech_label=label,
                    side=side,
                    order=idx + 1,
                    arguments=args_in_col,
                )
            )

        # Build arrows from parent_id references
        self.arrows = []
        for arg in arguments:
            if arg.parent_id and arg.parent_id in self._arg_index:
                self.arrows.append(
                    FlowArrow(source_id=arg.id, target_id=arg.parent_id)
                )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_argument(self, arg_id: str) -> Optional[Argument]:
        return self._arg_index.get(arg_id)

    def get_column(self, speech_label: str) -> Optional[FlowColumn]:
        for col in self.columns:
            if col.speech_label == speech_label:
                return col
        return None

    def get_rebuttals_for(self, arg_id: str) -> List[Argument]:
        """Return all arguments that directly rebut *arg_id*."""
        return [
            self._arg_index[arrow.source_id]
            for arrow in self.arrows
            if arrow.target_id == arg_id and arrow.source_id in self._arg_index
        ]

    def get_arguments_by_side(self, side: str) -> List[Argument]:
        return [a for a in self._arg_index.values() if a.side == side]

    def get_all_arguments(self) -> List[Argument]:
        return list(self._arg_index.values())

    def get_root_arguments(self) -> List[Argument]:
        """Arguments that are not rebuttals (no parent_id)."""
        return [a for a in self._arg_index.values() if a.parent_id is None]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "arrows": [a.to_dict() for a in self.arrows],
        }

    def summary(self) -> str:
        """Human-readable summary of the flow sheet."""
        lines = ["=== Flow Sheet Summary ==="]
        for col in self.columns:
            lines.append(f"\n--- {col.speech_label} ({col.side}) ---")
            for arg in col.arguments:
                rebuttal_tag = f" [rebuts {arg.parent_id}]" if arg.parent_id else ""
                lines.append(f"  [{arg.id}] {arg.claim}{rebuttal_tag}")
        lines.append(f"\nTotal arguments: {len(self._arg_index)}")
        lines.append(f"Rebuttal arrows: {len(self.arrows)}")
        return "\n".join(lines)
