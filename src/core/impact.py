"""Impact calculus -- assess magnitude, timeframe, probability, and reversibility."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.extractor import Argument
from src.core.llm_client import LLMClient


@dataclass
class ImpactAssessment:
    """Structured impact calculus for a single argument."""

    argument_id: str
    claim: str
    magnitude: float  # 0-10 scale
    timeframe: float  # 0-10 (10 = most imminent)
    probability: float  # 0-10
    reversibility: float  # 0-10 (10 = most irreversible, i.e. worse)
    explanation: str = ""

    @property
    def composite_score(self) -> float:
        """Weighted composite impact score (0-10)."""
        return (
            self.magnitude * 0.35
            + self.timeframe * 0.15
            + self.probability * 0.30
            + self.reversibility * 0.20
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "argument_id": self.argument_id,
            "claim": self.claim,
            "magnitude": self.magnitude,
            "timeframe": self.timeframe,
            "probability": self.probability,
            "reversibility": self.reversibility,
            "composite_score": round(self.composite_score, 2),
            "explanation": self.explanation,
        }


IMPACT_SYSTEM_PROMPT = """You are a debate judge evaluating the impact calculus of arguments.
For each argument, assess four dimensions on a 0-10 scale:

1. magnitude (0-10): How large is the impact? (10 = existential / massive)
2. timeframe (0-10): How soon does it occur? (10 = immediate, 0 = far future)
3. probability (0-10): How likely is the impact? (10 = certain)
4. reversibility (0-10): How irreversible is it? (10 = completely irreversible)

Provide a brief explanation for your assessment.

Return ONLY valid JSON:
{
  "assessments": [
    {
      "argument_id": "...",
      "magnitude": 7,
      "timeframe": 5,
      "probability": 6,
      "reversibility": 8,
      "explanation": "..."
    }
  ]
}
"""


class ImpactCalculus:
    """Evaluate the impact calculus of debate arguments."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def assess(self, arguments: List[Argument]) -> List[ImpactAssessment]:
        """Assess impact calculus for a batch of arguments."""
        if not arguments:
            return []

        arg_descriptions = "\n".join(
            f"- [{a.id}] Claim: {a.claim} | Impact stated: {a.impact}"
            for a in arguments
        )

        prompt = (
            f"Evaluate the impact calculus for the following debate arguments:\n\n"
            f"{arg_descriptions}\n\n"
            f"Assess each argument on all four dimensions."
        )

        raw = self.llm.complete_json(prompt, system=IMPACT_SYSTEM_PROMPT)
        return self._parse(raw, arguments)

    def assess_single(self, argument: Argument) -> ImpactAssessment:
        """Assess a single argument's impact calculus."""
        results = self.assess([argument])
        if results:
            return results[0]
        # Fallback: neutral assessment
        return ImpactAssessment(
            argument_id=argument.id,
            claim=argument.claim,
            magnitude=5.0,
            timeframe=5.0,
            probability=5.0,
            reversibility=5.0,
            explanation="Unable to assess.",
        )

    def compare(
        self,
        side_a: List[ImpactAssessment],
        side_b: List[ImpactAssessment],
    ) -> Dict[str, Any]:
        """Compare aggregate impact between two sides."""
        avg_a = self._average_score(side_a)
        avg_b = self._average_score(side_b)

        return {
            "side_a_avg_score": round(avg_a, 2),
            "side_b_avg_score": round(avg_b, 2),
            "side_a_count": len(side_a),
            "side_b_count": len(side_b),
            "advantage": "side_a" if avg_a > avg_b else ("side_b" if avg_b > avg_a else "tie"),
            "margin": round(abs(avg_a - avg_b), 2),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _average_score(assessments: List[ImpactAssessment]) -> float:
        if not assessments:
            return 0.0
        return sum(a.composite_score for a in assessments) / len(assessments)

    def _parse(
        self, data: Any, arguments: List[Argument]
    ) -> List[ImpactAssessment]:
        raw_list = data.get("assessments", []) if isinstance(data, dict) else []
        arg_map = {a.id: a for a in arguments}
        results: List[ImpactAssessment] = []

        for item in raw_list:
            arg_id = item.get("argument_id", "")
            claim = arg_map[arg_id].claim if arg_id in arg_map else ""
            results.append(
                ImpactAssessment(
                    argument_id=arg_id,
                    claim=claim,
                    magnitude=float(item.get("magnitude", 5)),
                    timeframe=float(item.get("timeframe", 5)),
                    probability=float(item.get("probability", 5)),
                    reversibility=float(item.get("reversibility", 5)),
                    explanation=item.get("explanation", ""),
                )
            )

        return results

    def summary(self, assessments: List[ImpactAssessment]) -> str:
        """Human-readable summary of impact assessments."""
        if not assessments:
            return "No impact assessments available."

        lines = ["=== Impact Calculus Summary ==="]
        sorted_a = sorted(assessments, key=lambda a: a.composite_score, reverse=True)
        for a in sorted_a:
            lines.append(
                f"\n[{a.argument_id}] {a.claim}"
                f"\n  Magnitude: {a.magnitude}/10  Timeframe: {a.timeframe}/10  "
                f"Probability: {a.probability}/10  Reversibility: {a.reversibility}/10"
                f"\n  Composite: {a.composite_score:.1f}/10"
                f"\n  {a.explanation}"
            )
        return "\n".join(lines)
