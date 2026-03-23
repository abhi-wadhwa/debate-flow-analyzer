"""Win probability estimator -- weighted scoring of argument coverage, dropped args, impact."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.core.dropped import DroppedArgument
from src.core.extractor import Argument
from src.core.flow_sheet import FlowSheet
from src.core.impact import ImpactAssessment


@dataclass
class SideScore:
    """Scoring breakdown for one side of the debate."""

    side: str
    argument_count: int = 0
    rebuttal_count: int = 0
    dropped_by_opponent: int = 0  # opponent dropped this side's args
    dropped_own: int = 0  # this side dropped opponent's args
    avg_impact: float = 0.0
    coverage_score: float = 0.0
    impact_score: float = 0.0
    dropped_penalty: float = 0.0
    total_score: float = 0.0
    win_probability: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "side": self.side,
            "argument_count": self.argument_count,
            "rebuttal_count": self.rebuttal_count,
            "dropped_by_opponent": self.dropped_by_opponent,
            "dropped_own": self.dropped_own,
            "avg_impact": round(self.avg_impact, 2),
            "coverage_score": round(self.coverage_score, 2),
            "impact_score": round(self.impact_score, 2),
            "dropped_penalty": round(self.dropped_penalty, 2),
            "total_score": round(self.total_score, 2),
            "win_probability": round(self.win_probability, 3),
        }


@dataclass
class WinEstimate:
    """Complete win-probability estimate with per-side breakdowns."""

    sides: Dict[str, SideScore] = field(default_factory=dict)
    predicted_winner: str = ""
    confidence: float = 0.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sides": {k: v.to_dict() for k, v in self.sides.items()},
            "predicted_winner": self.predicted_winner,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
        }


class WinProbabilityEstimator:
    """Estimate win probability based on argument coverage, dropped arguments, and impact.

    Weights (configurable):
        - argument_coverage: 0.25
        - rebuttal_coverage: 0.20
        - dropped_argument_penalty: 0.25
        - impact_calculus: 0.30
    """

    def __init__(
        self,
        weight_coverage: float = 0.25,
        weight_rebuttal: float = 0.20,
        weight_dropped: float = 0.25,
        weight_impact: float = 0.30,
    ):
        self.w_cov = weight_coverage
        self.w_reb = weight_rebuttal
        self.w_drop = weight_dropped
        self.w_imp = weight_impact

    def estimate(
        self,
        flow: FlowSheet,
        dropped: List[DroppedArgument],
        impact_assessments: Optional[List[ImpactAssessment]] = None,
    ) -> WinEstimate:
        """Produce a win estimate from the flow sheet data."""
        sides = self._identify_sides(flow)
        if len(sides) < 2:
            return WinEstimate(rationale="Fewer than two sides detected.")

        side_a, side_b = sides[0], sides[1]

        score_a = self._score_side(side_a, side_b, flow, dropped, impact_assessments)
        score_b = self._score_side(side_b, side_a, flow, dropped, impact_assessments)

        # Normalise to probabilities using softmax-style
        total = score_a.total_score + score_b.total_score
        if total > 0:
            score_a.win_probability = score_a.total_score / total
            score_b.win_probability = score_b.total_score / total
        else:
            score_a.win_probability = 0.5
            score_b.win_probability = 0.5

        predicted = side_a if score_a.win_probability >= score_b.win_probability else side_b
        confidence = abs(score_a.win_probability - score_b.win_probability)

        rationale = self._build_rationale(score_a, score_b)

        return WinEstimate(
            sides={side_a: score_a, side_b: score_b},
            predicted_winner=predicted,
            confidence=confidence,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _score_side(
        self,
        side: str,
        opponent: str,
        flow: FlowSheet,
        dropped: List[DroppedArgument],
        impacts: Optional[List[ImpactAssessment]],
    ) -> SideScore:
        my_args = flow.get_arguments_by_side(side)
        opp_args = flow.get_arguments_by_side(opponent)

        arg_count = len([a for a in my_args if a.parent_id is None])
        rebuttal_count = len([a for a in my_args if a.parent_id is not None])

        # Dropped arguments where this side's args were dropped by opponent
        dropped_by_opp = [d for d in dropped if d.argument.side == side]
        # Arguments this side failed to rebut (opponent's args this side dropped)
        dropped_own = [d for d in dropped if d.argument.side == opponent]

        # Coverage score: arguments + rebuttals
        total_possible = max(arg_count + len(opp_args), 1)
        coverage = (arg_count + rebuttal_count) / total_possible
        coverage_score = min(coverage, 1.0) * 10

        # Rebuttal coverage
        opp_root_count = len([a for a in opp_args if a.parent_id is None])
        reb_coverage = rebuttal_count / max(opp_root_count, 1)
        rebuttal_score = min(reb_coverage, 1.0) * 10

        # Dropped penalty: penalty for args this side dropped (opponent's args)
        drop_penalty_raw = len(dropped_own) / max(opp_root_count, 1)
        dropped_penalty = min(drop_penalty_raw, 1.0) * 10  # higher = worse for this side

        # Impact score
        impact_score = 5.0
        avg_impact = 5.0
        if impacts:
            my_impacts = [i for i in impacts if self._impact_belongs_to(i, my_args)]
            if my_impacts:
                avg_impact = sum(i.composite_score for i in my_impacts) / len(my_impacts)
                impact_score = avg_impact

        # Combine (note: dropped_penalty is inverted -- higher penalty = lower score)
        total = (
            self.w_cov * coverage_score
            + self.w_reb * rebuttal_score
            + self.w_drop * (10 - dropped_penalty)
            + self.w_imp * impact_score
        )

        return SideScore(
            side=side,
            argument_count=arg_count,
            rebuttal_count=rebuttal_count,
            dropped_by_opponent=len(dropped_by_opp),
            dropped_own=len(dropped_own),
            avg_impact=avg_impact,
            coverage_score=coverage_score,
            impact_score=impact_score,
            dropped_penalty=dropped_penalty,
            total_score=total,
        )

    @staticmethod
    def _impact_belongs_to(
        impact: ImpactAssessment, side_args: List[Argument]
    ) -> bool:
        return any(a.id == impact.argument_id for a in side_args)

    @staticmethod
    def _identify_sides(flow: FlowSheet) -> List[str]:
        seen: List[str] = []
        for col in flow.columns:
            if col.side and col.side not in seen:
                seen.append(col.side)
        return seen

    @staticmethod
    def _build_rationale(a: SideScore, b: SideScore) -> str:
        parts: List[str] = []
        if a.dropped_by_opponent > 0:
            parts.append(
                f"{a.side} had {a.dropped_by_opponent} argument(s) dropped by the opponent."
            )
        if b.dropped_by_opponent > 0:
            parts.append(
                f"{b.side} had {b.dropped_by_opponent} argument(s) dropped by the opponent."
            )
        if abs(a.impact_score - b.impact_score) > 1:
            stronger = a.side if a.impact_score > b.impact_score else b.side
            parts.append(f"{stronger} had stronger impact calculus.")
        if abs(a.coverage_score - b.coverage_score) > 1:
            broader = a.side if a.coverage_score > b.coverage_score else b.side
            parts.append(f"{broader} had broader argument coverage.")
        if not parts:
            parts.append("Both sides performed comparably.")
        return " ".join(parts)

    def summary(self, estimate: WinEstimate) -> str:
        """Human-readable summary of the win estimate."""
        lines = ["=== Win Probability Estimate ==="]
        for side, score in estimate.sides.items():
            lines.append(
                f"\n{side}: {score.win_probability:.1%}"
                f"  (args={score.argument_count}, rebuttals={score.rebuttal_count}, "
                f"opp_dropped={score.dropped_by_opponent}, own_dropped={score.dropped_own})"
            )
        lines.append(f"\nPredicted winner: {estimate.predicted_winner}")
        lines.append(f"Confidence: {estimate.confidence:.1%}")
        lines.append(f"Rationale: {estimate.rationale}")
        return "\n".join(lines)
