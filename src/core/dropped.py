"""Dropped argument detector -- find arguments that were never responded to."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from src.core.extractor import Argument
from src.core.flow_sheet import FlowSheet


@dataclass
class DroppedArgument:
    """An argument that was never rebutted by the opposing side."""

    argument: Argument
    expected_responses_from: List[str]  # speech labels that should have responded
    severity: str = "medium"  # low / medium / high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "argument": self.argument.to_dict(),
            "expected_responses_from": self.expected_responses_from,
            "severity": self.severity,
        }


class DroppedArgumentDetector:
    """Detect arguments that the opposing side never responded to.

    An argument is considered *dropped* when:
    1. It has no rebuttal arrows pointing to it from the other side.
    2. At least one subsequent speech from the other side exists
       (otherwise there was no opportunity to respond).
    """

    def detect(self, flow: FlowSheet) -> List[DroppedArgument]:
        """Return a list of dropped arguments from the flow sheet."""
        # Build set of argument IDs that have been rebutted
        rebutted_ids: Set[str] = set()
        for arrow in flow.arrows:
            rebutted_ids.add(arrow.target_id)

        # Determine which sides had speeches, ordered
        side_speech_order: Dict[str, List[str]] = {}
        for col in flow.columns:
            side_speech_order.setdefault(col.side, []).append(col.speech_label)

        # Identify the opposing side for each side
        all_sides = list(side_speech_order.keys())
        opposite: Dict[str, str] = {}
        if len(all_sides) == 2:
            opposite[all_sides[0]] = all_sides[1]
            opposite[all_sides[1]] = all_sides[0]
        else:
            # Fallback: no clear opposite
            for s in all_sides:
                opposite[s] = s

        dropped: List[DroppedArgument] = []

        for arg in flow.get_all_arguments():
            if arg.id in rebutted_ids:
                continue  # already rebutted
            if arg.parent_id is not None:
                # This is itself a rebuttal; being unrebutted is less critical
                continue

            # Check whether the opposing side had any subsequent speeches
            opp_side = opposite.get(arg.side, "")
            if not opp_side or opp_side not in side_speech_order:
                continue  # no opposing speeches exist

            # Find the column order of this argument's speech
            arg_col = flow.get_column(arg.speech_label)
            if arg_col is None:
                continue
            arg_order = arg_col.order

            # Speeches from the opposing side that came after
            expected = [
                col.speech_label
                for col in flow.columns
                if col.side == opp_side and col.order > arg_order
            ]
            if not expected:
                continue  # no opportunity to respond

            severity = self._assess_severity(arg, expected)
            dropped.append(
                DroppedArgument(
                    argument=arg,
                    expected_responses_from=expected,
                    severity=severity,
                )
            )

        return dropped

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assess_severity(arg: Argument, expected_speeches: List[str]) -> str:
        """Heuristic severity based on number of missed opportunities and impact text."""
        missed_count = len(expected_speeches)
        has_strong_impact = bool(arg.impact and len(arg.impact) > 20)

        if missed_count >= 3 and has_strong_impact:
            return "high"
        if missed_count >= 2 or has_strong_impact:
            return "medium"
        return "low"

    def summary(self, dropped: List[DroppedArgument]) -> str:
        """Human-readable summary of dropped arguments."""
        if not dropped:
            return "No dropped arguments detected."

        lines = [f"=== Dropped Arguments ({len(dropped)}) ==="]
        for da in dropped:
            lines.append(
                f"\n[{da.severity.upper()}] [{da.argument.id}] "
                f"({da.argument.speech_label}, {da.argument.side})"
            )
            lines.append(f"  Claim: {da.argument.claim}")
            lines.append(f"  Impact: {da.argument.impact}")
            lines.append(
                f"  Should have been addressed in: {', '.join(da.expected_responses_from)}"
            )
        return "\n".join(lines)
