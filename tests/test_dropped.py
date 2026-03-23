"""Tests for the dropped argument detector."""

import pytest

from src.core.dropped import DroppedArgumentDetector, DroppedArgument
from src.core.extractor import Argument
from src.core.flow_sheet import FlowSheet


@pytest.fixture
def flow_with_dropped():
    """Flow sheet where argument a3 (negative) is never rebutted."""
    args = [
        Argument(
            id="a1", claim="Trade boosts GDP", warrant="Data", impact="Growth",
            speech_label="1AC", side="affirmative",
        ),
        Argument(
            id="a2", claim="Trade harms workers", warrant="Job loss stats",
            impact="Unemployment rises significantly across manufacturing sectors",
            speech_label="1NC", side="negative", parent_id="a1",
        ),
        Argument(
            id="a3", claim="Security risk from trade", warrant="Intel reports",
            impact="Espionage and IP theft threaten national security for decades",
            speech_label="1NC", side="negative",
        ),
        Argument(
            id="a4", claim="Workers retrained", warrant="Programs exist",
            impact="Mitigates job loss", speech_label="2AC", side="affirmative",
            parent_id="a2",
        ),
        # Note: a3 is NEVER rebutted by the affirmative side
    ]
    flow = FlowSheet()
    flow.build(args)
    return flow


@pytest.fixture
def flow_no_dropped():
    """Flow sheet where every root argument is rebutted."""
    args = [
        Argument(
            id="x1", claim="Claim A", warrant="W", impact="I",
            speech_label="1AC", side="affirmative",
        ),
        Argument(
            id="x2", claim="Rebut A", warrant="W", impact="I",
            speech_label="1NC", side="negative", parent_id="x1",
        ),
        Argument(
            id="x3", claim="Claim B", warrant="W", impact="I",
            speech_label="1NC", side="negative",
        ),
        Argument(
            id="x4", claim="Rebut B", warrant="W", impact="I",
            speech_label="2AC", side="affirmative", parent_id="x3",
        ),
    ]
    flow = FlowSheet()
    flow.build(args)
    return flow


class TestDroppedArgumentDetector:
    def test_detects_dropped_argument(self, flow_with_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_with_dropped)
        assert len(dropped) == 1
        assert dropped[0].argument.id == "a3"
        assert dropped[0].argument.side == "negative"

    def test_expected_responses(self, flow_with_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_with_dropped)
        da = dropped[0]
        # 2AC comes after 1NC and is on the affirmative side
        assert "2AC" in da.expected_responses_from

    def test_severity_assessment(self, flow_with_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_with_dropped)
        # a3 has a long impact statement, should be at least medium
        assert dropped[0].severity in ("medium", "high")

    def test_no_dropped_arguments(self, flow_no_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_no_dropped)
        assert len(dropped) == 0

    def test_summary_with_dropped(self, flow_with_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_with_dropped)
        text = detector.summary(dropped)
        assert "Dropped Arguments" in text
        assert "a3" in text

    def test_summary_no_dropped(self, flow_no_dropped):
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow_no_dropped)
        text = detector.summary(dropped)
        assert "No dropped arguments" in text

    def test_empty_flow_sheet(self):
        flow = FlowSheet()
        flow.build([])
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow)
        assert dropped == []

    def test_single_side_no_drops(self):
        """Only one side means no opponent to drop anything."""
        args = [
            Argument(id="s1", claim="C", warrant="W", impact="I",
                     speech_label="1AC", side="affirmative"),
        ]
        flow = FlowSheet()
        flow.build(args)
        detector = DroppedArgumentDetector()
        dropped = detector.detect(flow)
        assert dropped == []
