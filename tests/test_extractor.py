"""Tests for the argument extractor using the mock LLM client."""

import json

import pytest

from src.core.extractor import Argument, ArgumentExtractor
from src.core.llm_client import MockLLMClient
from src.core.parser import Speech


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def sample_speech():
    return Speech(
        speaker_label="1AC",
        text="We propose increasing the minimum wage to $15/hour. "
        "Studies show this lifts 1.3 million people out of poverty.",
        order=1,
        side="affirmative",
    )


class TestArgumentExtractor:
    def test_extract_single_speech(self, mock_llm, sample_speech):
        mock_llm.add_response(json.dumps({
            "arguments": [
                {
                    "claim": "Minimum wage should be raised to $15/hour",
                    "warrant": "Studies show 1.3 million people lifted from poverty",
                    "impact": "Reduces poverty and inequality nationwide",
                    "tags": ["economics", "poverty"],
                    "parent_id": None,
                }
            ]
        }))

        extractor = ArgumentExtractor(mock_llm)
        args = extractor.extract_from_speech(sample_speech)

        assert len(args) == 1
        assert args[0].claim == "Minimum wage should be raised to $15/hour"
        assert args[0].speech_label == "1AC"
        assert args[0].side == "affirmative"
        assert args[0].parent_id is None
        assert "economics" in args[0].tags

    def test_extract_multiple_arguments(self, mock_llm, sample_speech):
        mock_llm.add_response(json.dumps({
            "arguments": [
                {
                    "claim": "Claim A",
                    "warrant": "Warrant A",
                    "impact": "Impact A",
                    "tags": ["tag1"],
                    "parent_id": None,
                },
                {
                    "claim": "Claim B",
                    "warrant": "Warrant B",
                    "impact": "Impact B",
                    "tags": ["tag2"],
                    "parent_id": None,
                },
            ]
        }))

        extractor = ArgumentExtractor(mock_llm)
        args = extractor.extract_from_speech(sample_speech)
        assert len(args) == 2

    def test_extract_with_rebuttal(self, mock_llm):
        prior = Argument(
            id="arg-001",
            claim="Original claim",
            warrant="Original warrant",
            impact="Original impact",
            speech_label="1AC",
            side="affirmative",
        )

        mock_llm.add_response(json.dumps({
            "arguments": [
                {
                    "claim": "Rebuttal to original",
                    "warrant": "Counter evidence",
                    "impact": "Negates the original impact",
                    "tags": ["rebuttal"],
                    "parent_id": "arg-001",
                }
            ]
        }))

        neg_speech = Speech(
            speaker_label="1NC",
            text="We rebut the affirmative case.",
            order=2,
            side="negative",
        )

        extractor = ArgumentExtractor(mock_llm)
        args = extractor.extract_from_speech(neg_speech, prior_arguments=[prior])

        assert len(args) == 1
        assert args[0].parent_id == "arg-001"

    def test_extract_all_skips_crossex(self, mock_llm):
        speeches = [
            Speech(speaker_label="1AC", text="Constructive.", order=1, side="affirmative"),
            Speech(speaker_label="CX-1AC", text="Questions.", order=2, side="negative", is_crossex=True),
            Speech(speaker_label="1NC", text="Response.", order=3, side="negative"),
        ]

        # Two non-CX speeches, so two extraction calls
        for _ in range(2):
            mock_llm.add_response(json.dumps({
                "arguments": [
                    {"claim": "C", "warrant": "W", "impact": "I", "tags": [], "parent_id": None}
                ]
            }))

        extractor = ArgumentExtractor(mock_llm)
        args = extractor.extract_all(speeches)

        # Should have 2 arguments (one per non-CX speech)
        assert len(args) == 2
        # Only 2 prompts sent (CX was skipped)
        assert len(mock_llm.prompts_received) == 2

    def test_extract_empty_response(self, mock_llm, sample_speech):
        mock_llm.add_response(json.dumps({"arguments": []}))
        extractor = ArgumentExtractor(mock_llm)
        args = extractor.extract_from_speech(sample_speech)
        assert args == []

    def test_argument_to_dict_roundtrip(self):
        arg = Argument(
            id="x1",
            claim="Test claim",
            warrant="Test warrant",
            impact="Test impact",
            speech_label="1AC",
            side="affirmative",
            tags=["test"],
            parent_id=None,
            confidence=0.9,
        )
        d = arg.to_dict()
        restored = Argument.from_dict(d)
        assert restored.claim == arg.claim
        assert restored.id == arg.id
        assert restored.tags == arg.tags
