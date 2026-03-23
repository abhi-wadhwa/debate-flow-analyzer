"""Speech parser -- segment a debate transcript into individual speeches by speaker/role."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.core.formats import DebateFormat, get_format


@dataclass
class Speech:
    """A single speech extracted from a transcript."""

    speaker_label: str
    text: str
    order: int
    side: str = ""
    is_rebuttal: bool = False
    is_crossex: bool = False

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class SpeechParser:
    """Parse a raw debate transcript into a list of ``Speech`` objects.

    The parser looks for speaker labels at the start of lines and splits
    the transcript at each label boundary.  Labels are matched against the
    debate format's ``speaker_labels`` list so only recognised roles produce
    new speech segments.

    Accepted label patterns (case-insensitive)::

        SPEAKER_LABEL:
        [SPEAKER_LABEL]
        SPEAKER_LABEL -
        **SPEAKER_LABEL**

    Example::

        1AC: Ladies and gentlemen ...
        [1NC] Thank you, the opposition ...
    """

    def __init__(self, debate_format: DebateFormat | str = "policy"):
        if isinstance(debate_format, str):
            debate_format = get_format(debate_format)
        self.format = debate_format
        # Build a compiled regex that matches any known speaker label
        escaped = [re.escape(lbl) for lbl in self.format.speaker_labels]
        label_group = "|".join(escaped)
        # Match label at start-of-line with optional decoration.
        # The separator (: > -) is required for bare labels but optional
        # when brackets or asterisks wrap the label.
        self._pattern = re.compile(
            rf"^\s*(?:"
            rf"\[({label_group})\]\s*[:>\-]?\s*"  # [LABEL] with optional separator
            rf"|"
            rf"\*\*({label_group})\*\*\s*[:>\-]?\s*"  # **LABEL** with optional separator
            rf"|"
            rf"({label_group})\s*[:>\-]\s*"  # LABEL with required separator
            rf")",
            re.IGNORECASE | re.MULTILINE,
        )

    def parse(self, transcript: str) -> List[Speech]:
        """Parse *transcript* and return an ordered list of ``Speech`` objects."""
        if not transcript or not transcript.strip():
            return []

        matches = list(self._pattern.finditer(transcript))
        if not matches:
            # No recognised labels -- return the whole text as one speech
            return [Speech(speaker_label="Unknown", text=transcript.strip(), order=1)]

        speeches: List[Speech] = []
        for i, match in enumerate(matches):
            label = (match.group(1) or match.group(2) or match.group(3)).upper()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(transcript)
            text = transcript[start:end].strip()

            # Enrich with format metadata
            role = self.format.get_speech_by_label(label)
            side = role.side.value if role else ""
            is_rebuttal = role.is_rebuttal if role else False
            is_crossex = role.is_crossex if role else False

            speeches.append(
                Speech(
                    speaker_label=label,
                    text=text,
                    order=i + 1,
                    side=side,
                    is_rebuttal=is_rebuttal,
                    is_crossex=is_crossex,
                )
            )

        return speeches

    def parse_with_custom_labels(
        self, transcript: str, labels: List[str]
    ) -> List[Speech]:
        """Parse using a custom set of speaker labels (ignoring the format)."""
        escaped = [re.escape(lbl) for lbl in labels]
        label_group = "|".join(escaped)
        pattern = re.compile(
            rf"^\s*(?:"
            rf"\[({label_group})\]\s*[:>\-]?\s*"
            rf"|"
            rf"\*\*({label_group})\*\*\s*[:>\-]?\s*"
            rf"|"
            rf"({label_group})\s*[:>\-]\s*"
            rf")",
            re.IGNORECASE | re.MULTILINE,
        )
        matches = list(pattern.finditer(transcript))
        if not matches:
            return [Speech(speaker_label="Unknown", text=transcript.strip(), order=1)]

        speeches: List[Speech] = []
        for i, match in enumerate(matches):
            label = match.group(1) or match.group(2) or match.group(3)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(transcript)
            speeches.append(
                Speech(
                    speaker_label=label,
                    text=transcript[start:end].strip(),
                    order=i + 1,
                )
            )
        return speeches
