"""Command-line interface for the AI Debate Flow Analyzer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.dropped import DroppedArgumentDetector
from src.core.extractor import ArgumentExtractor
from src.core.flow_sheet import FlowSheet
from src.core.formats import list_formats, get_format
from src.core.impact import ImpactCalculus
from src.core.llm_client import create_client, MockLLMClient
from src.core.parser import SpeechParser
from src.core.win_prob import WinProbabilityEstimator


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="debate-flow-analyzer",
        description="Analyse a debate transcript: extract arguments, build flow sheets, detect dropped arguments.",
    )
    p.add_argument(
        "transcript",
        help="Path to a transcript text file, or '-' to read from stdin.",
    )
    p.add_argument(
        "--format",
        "-f",
        default="policy",
        help=f"Debate format. Choices: {', '.join(list_formats())} (default: policy)",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var).",
    )
    p.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model name (default: gpt-4o-mini).",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM for demo/testing (no API key required).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of human-readable text.",
    )
    return p


def _make_mock_client() -> MockLLMClient:
    """Build a mock client with sample responses for CLI demo."""
    client = MockLLMClient()
    sample_args = json.dumps({
        "arguments": [
            {
                "claim": "Renewable energy reduces long-term costs",
                "warrant": "Solar and wind have reached grid parity in most markets",
                "impact": "Continued fossil fuel dependence costs trillions in externalities",
                "tags": ["energy", "economics"],
                "parent_id": None,
            },
            {
                "claim": "Energy transition creates jobs",
                "warrant": "Clean energy sector employs more workers per MW than fossil fuels",
                "impact": "Millions of new jobs across manufacturing and installation",
                "tags": ["jobs", "energy"],
                "parent_id": None,
            },
        ]
    })
    sample_impact = json.dumps({
        "assessments": [
            {
                "argument_id": "placeholder",
                "magnitude": 8,
                "timeframe": 6,
                "probability": 7,
                "reversibility": 6,
                "explanation": "Significant economic and environmental impact.",
            },
        ]
    })
    # Add enough responses for multiple speeches
    for _ in range(12):
        client.add_response(sample_args)
    client.add_response(sample_impact)
    return client


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Read transcript
    if args.transcript == "-":
        transcript = sys.stdin.read()
    else:
        path = Path(args.transcript)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            return 1
        transcript = path.read_text(encoding="utf-8")

    if not transcript.strip():
        print("Error: transcript is empty.", file=sys.stderr)
        return 1

    # Set up components
    fmt = get_format(args.format)
    if args.mock:
        llm = _make_mock_client()
    else:
        llm = create_client("openai", api_key=args.api_key, model=args.model)

    parser = SpeechParser(fmt)
    speeches = parser.parse(transcript)
    if not speeches:
        print("Error: no speeches parsed from transcript.", file=sys.stderr)
        return 1

    extractor = ArgumentExtractor(llm)
    arguments = extractor.extract_all(speeches)

    flow = FlowSheet()
    flow.build(arguments)

    detector = DroppedArgumentDetector()
    dropped = detector.detect(flow)

    impact_calc = ImpactCalculus(llm)
    root_args = flow.get_root_arguments()
    impacts = impact_calc.assess(root_args) if root_args else []

    estimator = WinProbabilityEstimator()
    win_est = estimator.estimate(flow, dropped, impacts)

    # Output
    if args.json_output:
        result = {
            "speeches": [
                {"label": s.speaker_label, "side": s.side, "words": s.word_count}
                for s in speeches
            ],
            "flow_sheet": flow.to_dict(),
            "dropped_arguments": [d.to_dict() for d in dropped],
            "impact_assessments": [i.to_dict() for i in impacts],
            "win_estimate": win_est.to_dict(),
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"Parsed {len(speeches)} speeches, extracted {len(arguments)} arguments.\n")
        print(flow.summary())
        print()
        print(detector.summary(dropped))
        print()
        print(impact_calc.summary(impacts))
        print()
        print(estimator.summary(win_est))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
