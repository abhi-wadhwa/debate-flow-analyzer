"""Tests for the speech parser."""

import pytest

from src.core.parser import SpeechParser, Speech
from src.core.formats import get_format


class TestSpeechParserPolicy:
    """Test parsing with Policy/CX format."""

    def setup_method(self):
        self.parser = SpeechParser("policy")

    def test_parse_two_speeches(self):
        transcript = (
            "1AC: We propose increasing federal infrastructure spending to "
            "stimulate economic growth. The evidence shows that every dollar "
            "invested in infrastructure returns $1.50 in GDP.\n\n"
            "1NC: The opposition contends that federal spending leads to "
            "unsustainable debt levels. The current national debt exceeds "
            "$30 trillion."
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 2
        assert speeches[0].speaker_label == "1AC"
        assert speeches[0].side == "affirmative"
        assert speeches[0].order == 1
        assert "infrastructure" in speeches[0].text
        assert speeches[1].speaker_label == "1NC"
        assert speeches[1].side == "negative"
        assert speeches[1].order == 2

    def test_parse_rebuttal_flag(self):
        transcript = (
            "1AC: Plan text.\n"
            "1NR: Rebuttal argument.\n"
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 2
        assert speeches[0].is_rebuttal is False
        assert speeches[1].is_rebuttal is True

    def test_parse_crossex_flag(self):
        transcript = (
            "1AC: Constructive speech.\n"
            "CX-1AC: Questions go here.\n"
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 2
        assert speeches[0].is_crossex is False
        assert speeches[1].is_crossex is True

    def test_bracket_label_format(self):
        transcript = (
            "[1AC] Opening statement.\n"
            "[1NC] Response.\n"
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 2
        assert speeches[0].speaker_label == "1AC"
        assert speeches[1].speaker_label == "1NC"

    def test_empty_transcript(self):
        assert self.parser.parse("") == []
        assert self.parser.parse("   ") == []

    def test_no_labels_found(self):
        speeches = self.parser.parse("Just some random text with no labels.")
        assert len(speeches) == 1
        assert speeches[0].speaker_label == "Unknown"

    def test_word_count(self):
        transcript = "1AC: one two three four five.\n"
        speeches = self.parser.parse(transcript)
        assert speeches[0].word_count == 5

    def test_full_policy_round(self):
        labels = ["1AC", "1NC", "2AC", "2NC", "1NR", "1AR", "2NR", "2AR"]
        lines = [f"{lbl}: Speech content for {lbl}." for lbl in labels]
        transcript = "\n".join(lines)
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 8
        for speech, expected_label in zip(speeches, labels):
            assert speech.speaker_label == expected_label


class TestSpeechParserLD:
    """Test parsing with Lincoln-Douglas format."""

    def setup_method(self):
        self.parser = SpeechParser("ld")

    def test_parse_ld_speeches(self):
        transcript = (
            "AC: The affirmative case is based on the value of justice.\n"
            "NC: The negative case rests on the value of security.\n"
            "1AR: Extending the affirmative case.\n"
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 3
        assert speeches[0].speaker_label == "AC"
        assert speeches[0].side == "affirmative"
        assert speeches[2].speaker_label == "1AR"
        assert speeches[2].is_rebuttal is True


class TestSpeechParserBP:
    """Test parsing with British Parliamentary format."""

    def setup_method(self):
        self.parser = SpeechParser("bp")

    def test_parse_bp_speeches(self):
        transcript = (
            "PM: The Prime Minister proposes the motion.\n"
            "LO: The Leader of the Opposition responds.\n"
            "DPM: The Deputy PM extends the case.\n"
            "DLO: The Deputy LO counters.\n"
        )
        speeches = self.parser.parse(transcript)
        assert len(speeches) == 4
        assert speeches[0].speaker_label == "PM"
        assert speeches[0].side == "government"
        assert speeches[1].speaker_label == "LO"
        assert speeches[1].side == "opposition"


class TestCustomLabels:
    """Test parsing with user-defined labels."""

    def test_custom_labels(self):
        parser = SpeechParser("policy")
        transcript = (
            "Alice: Opening remarks.\n"
            "Bob: Counter argument.\n"
            "Alice: Rebuttal.\n"
        )
        speeches = parser.parse_with_custom_labels(transcript, ["Alice", "Bob"])
        assert len(speeches) == 3
        assert speeches[0].speaker_label == "Alice"
        assert speeches[1].speaker_label == "Bob"
        assert speeches[2].speaker_label == "Alice"
