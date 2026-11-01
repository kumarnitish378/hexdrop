"""Turns avrdude's stderr into :class:`ProgressEvent`s.

Calibrated against ``avrdude 8.0-arduino.1``. A successful flash prints:

    Processing -U flash:w:firmware.hex:i
    Reading 19278 bytes for flash from input file firmware.hex
    Writing 19278 bytes to flash
    Writing | ################################################## | 100% 7.60 s
    Reading | ################################################## | 100% 6.81 s
    19278 bytes of flash verified

    Avrdude done.  Thank you.

Two traps this handles:

* The progress bars redraw with ``\\r``, not ``\\n``. Splitting on newlines alone
  makes the whole bar arrive as one blob when the process exits.
* Write and verify both draw a bar, and the *verify* bar is labelled "Reading".
  Only its position distinguishes it from a genuine read, so the parser tracks
  whether a write has been announced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Iterator

from ...core.events import Phase, ProgressEvent

#: ``Writing | ####### | 62% 24.8 s``. avrdude 8 puts a space before the "s";
#: avrdude 6 did not, so the space is optional.
_BAR = re.compile(
    r"^(?P<verb>Writing|Reading)\s*\|(?P<bar>[#\s]*)\|\s*(?P<pct>\d+)%"
    r"(?:\s+(?P<secs>[\d.]+)\s*s)?",
    re.IGNORECASE,
)

#: A bar still being drawn: avrdude 8 appends one ``#`` at a time and prints the
#: percentage only when the bar is full, so mid-flash there is no number to read.
_PARTIAL_BAR = re.compile(r"^(?P<verb>Writing|Reading)\s*\|\s*(?P<hashes>#+)\s*$", re.IGNORECASE)
#: avrdude draws its bars 50 characters wide.
_BAR_WIDTH = 50

_PROCESSING = re.compile(r"^Processing -U\s+(?P<spec>\S+)", re.IGNORECASE)
_READING_INPUT = re.compile(
    r"^Reading (?P<bytes>\d+) bytes? for (?P<mem>\w+) from input file", re.IGNORECASE
)
_WRITING_TO = re.compile(
    r"^Writing (?P<bytes>\d+) bytes? to (?P<mem>\w+)", re.IGNORECASE
)
_VERIFIED = re.compile(
    r"^(?P<bytes>\d+) bytes? of (?P<mem>\w+) verified", re.IGNORECASE
)
_ERASING = re.compile(r"erasing chip|performing chip erase", re.IGNORECASE)
#: avrdude 6 prints ``0x1e9801 (probably m2560)``; avrdude 8 prints
#: ``1E 98 01 (ATmega2560)``. Both are normalised to ``0x1e9801``.
_SIGNATURE = re.compile(
    r"device signature\s*=\s*(?P<sig>0x[0-9a-f]{6}|(?:[0-9a-f]{2}\s+){2}[0-9a-f]{2})"
    r"(?:\s*\((?:probably\s+)?(?P<chip>[\w\-]+)\))?",
    re.IGNORECASE,
)
_ERROR = re.compile(r"^\s*(?:avrdude:\s*)?error:\s*(?P<msg>.+)$", re.IGNORECASE)
_DONE = re.compile(r"^Avrdude done", re.IGNORECASE)


def split_stream(chunk: str) -> list[str]:
    """Split on CR, LF or CRLF, keeping empty segments out.

    Progress bars overwrite themselves with CR, so each redraw is its own
    segment and the caller sees the percentage climb.
    """
    return [part for part in re.split(r"\r\n|\r|\n", chunk) if part.strip()]


@dataclass
class AvrdudeParser:
    """Feed it output chunks, get events out.

    Stateful: it remembers which phase avrdude announced last so an identical
    bar can mean "writing" one moment and "verifying" the next.
    """

    #: Set once "Writing N bytes to flash" is seen.
    write_announced: bool = False
    #: Set once the write bar reaches 100%, so the next bar is the verify pass.
    write_finished: bool = False

    signature: str | None = None
    detected_chip: str | None = None
    bytes_written: int = 0
    bytes_verified: int = 0
    verified: bool = False
    errors: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    _buffer: str = ""
    #: Highest overall percentage emitted so far. avrdude prints the device
    #: signature before "Processing -U", so a naive mapping would jump to 2%
    #: and then drop back to 0. A bar that goes backwards reads as a fault to
    #: an operator, so progress is clamped to never decrease.
    _high_water: float = 0.0

    def feed(self, chunk: str) -> Iterator[ProgressEvent]:
        """Consume a chunk of stderr, yielding every event it implies."""
        self._buffer += chunk
        if self._buffer and self._buffer[-1] in "\r\n":
            segments, self._buffer = self._buffer, ""
        else:
            # Hold back the trailing partial line until more arrives.
            parts = re.split(r"(?<=[\r\n])", self._buffer)
            self._buffer = parts.pop()
            segments = "".join(parts)
            partial = self._partial_bar(self._buffer)
            if partial is not None:
                yield self._monotonic(partial)

        for line in split_stream(segments):
            for event in self._line(line):
                yield self._monotonic(event)

    def finish(self) -> Iterator[ProgressEvent]:
        """Flush whatever is left in the buffer when the process exits."""
        remainder, self._buffer = self._buffer, ""
        for line in split_stream(remainder):
            for event in self._line(line):
                yield self._monotonic(event)

    def _monotonic(self, event: ProgressEvent) -> ProgressEvent:
        """Stop the overall percentage ever moving backwards."""
        if event.overall < self._high_water:
            return replace(event, overall=self._high_water)
        self._high_water = event.overall
        return event

    # -- internals ---------------------------------------------------------

    def _line(self, line: str) -> Iterator[ProgressEvent]:
        text = line.strip()
        if not text:
            return
        self.lines.append(text)

        bar = _BAR.match(text)
        if bar:
            yield self._bar_event(bar, text)
            return

        error = _ERROR.match(text)
        if error:
            self.errors.append(error.group("msg").strip())
            return

        sig = _SIGNATURE.search(text)
        if sig:
            self.signature = "0x" + "".join(sig.group("sig").lower().removeprefix("0x").split())
            self.detected_chip = sig.group("chip")
            yield ProgressEvent(
                phase=Phase.CONNECTING,
                overall=2.0,
                message=f"Found chip {self.signature}",
                raw=text,
            )
            return

        if _ERASING.search(text):
            yield ProgressEvent.in_phase(
                Phase.ERASING, 0.0, "Erasing the chip", raw=text
            )
            return

        reading_input = _READING_INPUT.match(text)
        if reading_input:
            size = int(reading_input.group("bytes"))
            yield ProgressEvent.in_phase(
                Phase.READING_INPUT,
                100.0,
                f"Read {size:,} bytes from the firmware file",
                raw=text,
            )
            return

        writing = _WRITING_TO.match(text)
        if writing:
            self.write_announced = True
            self.write_finished = False
            self.bytes_written = int(writing.group("bytes"))
            yield ProgressEvent.in_phase(
                Phase.WRITING,
                0.0,
                f"Writing {self.bytes_written:,} bytes to {writing.group('mem')}",
                raw=text,
            )
            return

        verified = _VERIFIED.match(text)
        if verified:
            self.verified = True
            self.bytes_verified = int(verified.group("bytes"))
            yield ProgressEvent(
                phase=Phase.VERIFYING,
                overall=100.0,
                phase_percent=100.0,
                message=f"Verified {self.bytes_verified:,} bytes",
                raw=text,
            )
            return

        processing = _PROCESSING.match(text)
        if processing:
            yield ProgressEvent(
                phase=Phase.STARTING, overall=0.0, message="Starting", raw=text
            )
            return

        if _DONE.match(text):
            # Not a success signal: avrdude prints this on failure too.
            return

    def _partial_bar(self, text: str) -> ProgressEvent | None:
        """Progress from a bar that is still being drawn, one ``#`` = 2%."""
        match = _PARTIAL_BAR.match(text.strip())
        if not match:
            return None
        pct = min(99.0, 100.0 * len(match.group("hashes")) / _BAR_WIDTH)
        return self._progress(match.group("verb").lower(), pct, None, text.strip())

    def _bar_event(self, match: re.Match[str], raw: str) -> ProgressEvent:
        secs = float(match.group("secs")) if match.group("secs") else None
        return self._progress(
            match.group("verb").lower(), float(match.group("pct")), secs, raw
        )

    def _progress(
        self, verb: str, pct: float, secs: float | None, raw: str
    ) -> ProgressEvent:
        if verb == "writing":
            phase, label = Phase.WRITING, "Writing to the board"
            if pct >= 100.0:
                self.write_finished = True
        elif self.write_announced:
            # A "Reading" bar after a write is avrdude's verify pass.
            phase, label = Phase.VERIFYING, "Checking what was written"
        else:
            phase, label = Phase.READING_INPUT, "Reading from the board"

        return ProgressEvent.in_phase(
            phase, pct, label, raw=raw, elapsed=secs
        )
