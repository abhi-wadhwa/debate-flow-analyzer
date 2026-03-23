"""Demo script showing the full analysis pipeline with a mock LLM."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.dropped import DroppedArgumentDetector
from src.core.extractor import Argument, ArgumentExtractor
from src.core.flow_sheet import FlowSheet
from src.core.formats import get_format, list_formats
from src.core.impact import ImpactCalculus
from src.core.llm_client import MockLLMClient
from src.core.parser import SpeechParser
from src.core.win_prob import WinProbabilityEstimator


def build_demo_client() -> MockLLMClient:
    """Create a mock LLM client with realistic debate responses."""
    client = MockLLMClient()

    # Response for 1AC
    client.add_response(json.dumps({
        "arguments": [
            {
                "claim": "Renewable energy investment drives economic growth",
                "warrant": "Every dollar invested generates $1.80 in economic activity; 2M new jobs by 2035",
                "impact": "Massive job creation and GDP growth from clean energy sector",
                "tags": ["economy", "jobs", "energy"],
                "parent_id": None,
            },
            {
                "claim": "Climate change mitigation requires immediate action",
                "warrant": "IPCC requires 45% emission reduction by 2030; plan achieves 40% in energy sector",
                "impact": "Without action, climate damages cost $2 trillion annually by 2100",
                "tags": ["climate", "environment"],
                "parent_id": None,
            },
            {
                "claim": "Renewable energy ensures energy independence",
                "warrant": "US imports 6.4M barrels of oil daily; renewables eliminate foreign dependence",
                "impact": "National security strengthened, energy prices stabilized",
                "tags": ["security", "energy"],
                "parent_id": None,
            },
        ]
    }))

    # Response for 1NC
    client.add_response(json.dumps({
        "arguments": [
            {
                "claim": "Federal spending causes debt crisis and inflation",
                "warrant": "$34T national debt; $500B more crowds out private investment; CBO warns above 100% debt-to-GDP",
                "impact": "Long-term growth reduced by 0.5% per year; inflation harms all Americans",
                "tags": ["spending", "debt", "economy"],
                "parent_id": None,
            },
            {
                "claim": "Federal energy mandates violate federalism",
                "warrant": "Energy policy is traditionally state-level; federal mandates ignore regional differences",
                "impact": "State sovereignty undermined; one-size-fits-all fails diverse energy needs",
                "tags": ["federalism", "governance"],
                "parent_id": None,
            },
        ]
    }))

    # Response for 2AC
    client.add_response(json.dumps({
        "arguments": [
            {
                "claim": "Plan is revenue-neutral through subsidy reallocation",
                "warrant": "Fossil fuel subsidies total $52B annually; eliminating them funds the plan",
                "impact": "No deficit increase; climate inaction costs $2T/year by 2100",
                "tags": ["funding", "economy"],
                "parent_id": None,
            },
        ]
    }))

    # Response for 2NC
    client.add_response(json.dumps({
        "arguments": [
            {
                "claim": "Rapid renewable transition causes grid instability",
                "warrant": "Germany's Energiewende led to blackouts and 50% electricity price increase",
                "impact": "Grid failure risks energy security of 330 million Americans",
                "tags": ["grid", "reliability", "energy"],
                "parent_id": None,
            },
        ]
    }))

    # Responses for rebuttals (1NR, 1AR, 2NR, 2AR)
    for _ in range(4):
        client.add_response(json.dumps({"arguments": []}))

    # Impact assessment response
    client.add_response(json.dumps({
        "assessments": [
            {
                "argument_id": "placeholder",
                "magnitude": 8,
                "timeframe": 7,
                "probability": 7,
                "reversibility": 8,
                "explanation": "Climate change has existential-level magnitude with closing window.",
            },
            {
                "argument_id": "placeholder",
                "magnitude": 7,
                "timeframe": 6,
                "probability": 6,
                "reversibility": 5,
                "explanation": "Economic growth impact is significant but more recoverable.",
            },
            {
                "argument_id": "placeholder",
                "magnitude": 6,
                "timeframe": 5,
                "probability": 7,
                "reversibility": 6,
                "explanation": "Energy independence has moderate but sustained strategic impact.",
            },
            {
                "argument_id": "placeholder",
                "magnitude": 7,
                "timeframe": 8,
                "probability": 5,
                "reversibility": 4,
                "explanation": "Debt impact is high and near-term but potentially reversible.",
            },
            {
                "argument_id": "placeholder",
                "magnitude": 5,
                "timeframe": 4,
                "probability": 5,
                "reversibility": 7,
                "explanation": "Federalism concern is structural but lower magnitude.",
            },
        ]
    }))

    return client


def main() -> None:
    print("=" * 60)
    print("  AI Debate Flow Analyzer -- Demo")
    print("=" * 60)
    print()

    # Show available formats
    print(f"Supported formats: {', '.join(list_formats())}")
    print()

    # Load transcript
    transcript_path = Path(__file__).parent / "sample_transcript.txt"
    if not transcript_path.exists():
        print(f"Sample transcript not found at {transcript_path}")
        return
    transcript = transcript_path.read_text(encoding="utf-8")

    # Setup
    fmt = get_format("policy")
    llm = build_demo_client()

    # 1. Parse speeches
    parser = SpeechParser(fmt)
    speeches = parser.parse(transcript)
    print(f"Parsed {len(speeches)} speeches:")
    for s in speeches:
        print(f"  {s.speaker_label:>8} ({s.side:>12}) -- {s.word_count} words")
    print()

    # 2. Extract arguments
    extractor = ArgumentExtractor(llm)
    arguments = extractor.extract_all(speeches)
    print(f"Extracted {len(arguments)} arguments.")
    print()

    # 3. Build flow sheet
    flow = FlowSheet()
    flow.build(arguments)
    print(flow.summary())
    print()

    # 4. Detect dropped arguments
    detector = DroppedArgumentDetector()
    dropped = detector.detect(flow)
    print(detector.summary(dropped))
    print()

    # 5. Impact calculus
    impact_calc = ImpactCalculus(llm)
    root_args = flow.get_root_arguments()
    impacts = impact_calc.assess(root_args)
    print(impact_calc.summary(impacts))
    print()

    # 6. Win probability
    estimator = WinProbabilityEstimator()
    win_est = estimator.estimate(flow, dropped, impacts)
    print(estimator.summary(win_est))
    print()

    # JSON output
    print("=" * 60)
    print("  JSON Output (abbreviated)")
    print("=" * 60)
    result = {
        "speech_count": len(speeches),
        "argument_count": len(arguments),
        "dropped_count": len(dropped),
        "win_estimate": win_est.to_dict(),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
