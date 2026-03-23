"""Tests for the flow sheet generator."""

import pytest

from src.core.extractor import Argument
from src.core.flow_sheet import FlowSheet, FlowColumn, FlowArrow


@pytest.fixture
def sample_arguments():
    """Create a small set of arguments with rebuttals."""
    a1 = Argument(
        id="a1", claim="Economy grows with trade", warrant="Historical evidence",
        impact="GDP increase", speech_label="1AC", side="affirmative",
    )
    a2 = Argument(
        id="a2", claim="Trade causes inequality", warrant="Gini coefficient data",
        impact="Social instability", speech_label="1NC", side="negative",
        parent_id="a1",
    )
    a3 = Argument(
        id="a3", claim="Security risks of open borders", warrant="Defense reports",
        impact="National security threat", speech_label="1NC", side="negative",
    )
    a4 = Argument(
        id="a4", claim="Inequality is mitigated by policy", warrant="Welfare programs",
        impact="Stabilises society", speech_label="2AC", side="affirmative",
        parent_id="a2",
    )
    return [a1, a2, a3, a4]


class TestFlowSheet:
    def test_build_columns(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        assert len(flow.columns) == 3  # 1AC, 1NC, 2AC
        assert flow.columns[0].speech_label == "1AC"
        assert flow.columns[1].speech_label == "1NC"
        assert flow.columns[2].speech_label == "2AC"

    def test_build_arrows(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        assert len(flow.arrows) == 2
        targets = {a.target_id for a in flow.arrows}
        assert "a1" in targets  # a2 rebuts a1
        assert "a2" in targets  # a4 rebuts a2

    def test_get_argument(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        assert flow.get_argument("a1") is not None
        assert flow.get_argument("a1").claim == "Economy grows with trade"
        assert flow.get_argument("nonexistent") is None

    def test_get_column(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        col = flow.get_column("1NC")
        assert col is not None
        assert len(col.arguments) == 2
        assert flow.get_column("MISSING") is None

    def test_get_rebuttals_for(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        rebuttals = flow.get_rebuttals_for("a1")
        assert len(rebuttals) == 1
        assert rebuttals[0].id == "a2"

    def test_get_arguments_by_side(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        aff = flow.get_arguments_by_side("affirmative")
        neg = flow.get_arguments_by_side("negative")
        assert len(aff) == 2
        assert len(neg) == 2

    def test_get_root_arguments(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        roots = flow.get_root_arguments()
        assert len(roots) == 2  # a1 and a3 have no parent_id
        root_ids = {r.id for r in roots}
        assert "a1" in root_ids
        assert "a3" in root_ids

    def test_to_dict(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        d = flow.to_dict()
        assert "columns" in d
        assert "arrows" in d
        assert len(d["columns"]) == 3
        assert len(d["arrows"]) == 2

    def test_summary(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments)
        text = flow.summary()
        assert "Flow Sheet Summary" in text
        assert "1AC" in text
        assert "1NC" in text
        assert "Total arguments: 4" in text

    def test_explicit_speech_order(self, sample_arguments):
        flow = FlowSheet()
        flow.build(sample_arguments, speech_order=["2AC", "1NC", "1AC"])
        assert flow.columns[0].speech_label == "2AC"
        assert flow.columns[1].speech_label == "1NC"
        assert flow.columns[2].speech_label == "1AC"

    def test_empty_flow_sheet(self):
        flow = FlowSheet()
        flow.build([])
        assert flow.columns == []
        assert flow.arrows == []
        assert flow.get_all_arguments() == []
