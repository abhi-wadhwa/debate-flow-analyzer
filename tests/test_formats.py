"""Tests for debate format definitions."""

import pytest

from src.core.formats import (
    DebateFormat,
    Side,
    SpeechRole,
    get_format,
    list_formats,
    POLICY_CX,
    LINCOLN_DOUGLAS,
    BRITISH_PARLIAMENTARY,
)


class TestPolicyCX:
    def test_name(self):
        assert POLICY_CX.name == "Policy/CX"

    def test_speech_count(self):
        assert POLICY_CX.speech_count == 12

    def test_sides(self):
        assert Side.AFFIRMATIVE in POLICY_CX.sides
        assert Side.NEGATIVE in POLICY_CX.sides

    def test_first_speech_is_1ac(self):
        assert POLICY_CX.speeches[0].label == "1AC"
        assert POLICY_CX.speeches[0].side == Side.AFFIRMATIVE

    def test_rebuttal_speeches(self):
        rebuttals = [s for s in POLICY_CX.speeches if s.is_rebuttal]
        assert len(rebuttals) == 4  # 1NR, 1AR, 2NR, 2AR

    def test_crossex_speeches(self):
        cx = [s for s in POLICY_CX.speeches if s.is_crossex]
        assert len(cx) == 4

    def test_get_speech_by_label(self):
        s = POLICY_CX.get_speech_by_label("2NR")
        assert s is not None
        assert s.side == Side.NEGATIVE
        assert s.is_rebuttal is True

    def test_get_speech_by_label_case_insensitive(self):
        s = POLICY_CX.get_speech_by_label("1ac")
        assert s is not None
        assert s.label == "1AC"

    def test_get_speeches_for_side(self):
        aff = POLICY_CX.get_speeches_for_side(Side.AFFIRMATIVE)
        neg = POLICY_CX.get_speeches_for_side(Side.NEGATIVE)
        assert len(aff) == 6  # 1AC, CX-1NC, 2AC, CX-2NC, 1AR, 2AR
        assert len(neg) == 6

    def test_speaker_labels(self):
        assert "1AC" in POLICY_CX.speaker_labels
        assert "2AR" in POLICY_CX.speaker_labels


class TestLincolnDouglas:
    def test_name(self):
        assert LINCOLN_DOUGLAS.name == "Lincoln-Douglas"

    def test_speech_count(self):
        assert LINCOLN_DOUGLAS.speech_count == 7

    def test_sides(self):
        assert Side.AFFIRMATIVE in LINCOLN_DOUGLAS.sides
        assert Side.NEGATIVE in LINCOLN_DOUGLAS.sides

    def test_first_speech_is_ac(self):
        assert LINCOLN_DOUGLAS.speeches[0].label == "AC"

    def test_rebuttal_speeches(self):
        rebuttals = [s for s in LINCOLN_DOUGLAS.speeches if s.is_rebuttal]
        assert len(rebuttals) == 3  # 1AR, NR, 2AR


class TestBritishParliamentary:
    def test_name(self):
        assert BRITISH_PARLIAMENTARY.name == "British Parliamentary"

    def test_speech_count(self):
        assert BRITISH_PARLIAMENTARY.speech_count == 8

    def test_sides(self):
        assert Side.GOVERNMENT in BRITISH_PARLIAMENTARY.sides
        assert Side.OPPOSITION in BRITISH_PARLIAMENTARY.sides

    def test_pm_opens(self):
        assert BRITISH_PARLIAMENTARY.speeches[0].label == "PM"
        assert BRITISH_PARLIAMENTARY.speeches[0].side == Side.GOVERNMENT

    def test_whip_speeches_are_rebuttals(self):
        gw = BRITISH_PARLIAMENTARY.get_speech_by_label("GW")
        ow = BRITISH_PARLIAMENTARY.get_speech_by_label("OW")
        assert gw is not None and gw.is_rebuttal
        assert ow is not None and ow.is_rebuttal


class TestFormatRegistry:
    def test_get_format_policy(self):
        fmt = get_format("policy")
        assert fmt.name == "Policy/CX"

    def test_get_format_cx(self):
        fmt = get_format("cx")
        assert fmt.name == "Policy/CX"

    def test_get_format_ld(self):
        fmt = get_format("ld")
        assert fmt.name == "Lincoln-Douglas"

    def test_get_format_bp(self):
        fmt = get_format("bp")
        assert fmt.name == "British Parliamentary"

    def test_get_format_case_insensitive(self):
        fmt = get_format("POLICY")
        assert fmt.name == "Policy/CX"

    def test_get_format_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown debate format"):
            get_format("nonexistent-format")

    def test_list_formats(self):
        fmts = list_formats()
        assert "Policy/CX" in fmts
        assert "Lincoln-Douglas" in fmts
        assert "British Parliamentary" in fmts
        assert len(fmts) == 3
