"""A stand-in for avrdude, so the whole stack can be exercised without a board.

It reproduces ``avrdude 8.0-arduino.1``'s output byte for byte, including the
carriage-return progress redraws, and picks a scenario from the port name:

    COM_OK           a clean flash that verifies
    COM_SLOW         the same, drawn out, for cancel and watchdog tests
    COM_NOSYNC       the ISP is not answering (bad wiring, missing capacitor)
    COM_WRONGCHIP    a different AVR than the one selected
    COM_VERIFYFAIL   written, but reads back wrong
    COM_BUSY         the port is held by another program
    COM_MISSING      the port does not exist
    COM_STALL        opens and then says nothing, like a Bluetooth port
    COM_GARBAGE      output no rule has ever seen, to prove the fallback

Run it the way the programmer does::

    python tests/fake_avrdude.py -C conf -p atmega2560 -c stk500v1 -P COM_OK ...
"""

from __future__ import annotations

import argparse
import sys
import time

BAR_WIDTH = 50
DONE = "\nAvrdude done.  Thank you.\n"

#: What each chip reports, in avrdude 8's format: spaced hex bytes, then the
#: part's name. avrdude 6 printed "0x1e9801 (probably m2560)" instead.
SIGNATURES = {
    "atmega2560": ("1E 98 01", "ATmega2560"),
    "atmega1280": ("1E 97 03", "ATmega1280"),
    "atmega328p": ("1E 95 0F", "ATmega328P"),
    "atmega168": ("1E 94 06", "ATmega168"),
}


def err(text: str) -> None:
    sys.stderr.write(text)
    sys.stderr.flush()


def draw_bar(verb: str, seconds: float, steps: int = 10) -> None:
    """Draw a progress bar the way avrdude 8 does against a slow programmer.

    One ``#`` at a time, flushed, then the percentage and timing once the bar
    is full. An ISP write at 19200 baud emits a character every second or so,
    which is what the tool's output reader and watchdog have to cope with.
    """
    err(f"{verb} | ")
    for _ in range(BAR_WIDTH):
        err("#")
        if seconds:
            time.sleep(seconds / BAR_WIDTH)
    err(f" | 100% {seconds:.2f} s\n")


def scenario_of(port: str) -> str:
    return (port or "").upper().replace("\\\\.\\", "")


def emit_signature(chip: str) -> None:
    signature, name = SIGNATURES.get(chip, ("1E 98 01", "ATmega2560"))
    err(f"Device signature = {signature} ({name})\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-C")
    parser.add_argument("-p", default="atmega2560")
    parser.add_argument("-c", default="stk500v1")
    parser.add_argument("-P", default="")
    parser.add_argument("-b")
    parser.add_argument("-B")
    parser.add_argument("-U", action="append", default=[])
    parser.add_argument("-e", action="store_true")
    parser.add_argument("-D", action="store_true")
    parser.add_argument("-V", action="store_true")
    parser.add_argument("-n", action="store_true")
    parser.add_argument("-F", action="store_true")
    parser.add_argument("-v", action="count", default=0)
    parser.add_argument("-?", dest="help", action="store_true")
    args, _unknown = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    if args.help:
        err("avrdude version 8.0-arduino.1, https://github.com/avrdudes/avrdude\n")
        return 0

    port = scenario_of(args.P)

    # -- failures that happen before the port is even usable ---------------

    if port == "COM_MISSING":
        err(
            f"Error: cannot open port \\\\.\\{args.P}: "
            "The system cannot find the file specified.\n\n"
            f"Error: unable to open port {args.P} for programmer {args.c}\n"
        )
        err(DONE)
        return 1

    if port == "COM_BUSY":
        err(
            f"Error: cannot open port \\\\.\\{args.P}: Access is denied.\n\n"
            f"Error: unable to open port {args.P} for programmer {args.c}\n"
        )
        err(DONE)
        return 1

    if port == "COM_STALL":
        # Opens, then never speaks. This is the Bluetooth failure mode, and the
        # only way out is the caller's watchdog.
        time.sleep(600)
        return 0

    if port == "COM_GARBAGE":
        err("Error: the flux capacitor is misaligned at 1.21 GW\n")
        err(DONE)
        return 1

    if port == "COM_NOSYNC":
        err("Error: stk500_getsync() attempt 1 of 10: not in sync: resp=0x00\n")
        err("Error: stk500_recv(): programmer is not responding\n")
        err(f"Error: unable to open programmer {args.c} on port {args.P}\n")
        err(DONE)
        return 1

    # -- the port is alive; report the chip --------------------------------

    if port == "COM_WRONGCHIP":
        # A different part answers. avrdude reports what it found, then either
        # warns (with -F) or refuses.
        emit_signature("atmega328p")
        if args.F:
            err(f"Warning: expected signature for {args.p} is 1E 98 01\n")
        else:
            err(f"Error: expected signature for {args.p} is 1E 98 01\n")
            err("       Double check chip or use -F to override this check\n")
            err(DONE)
            return 1
    elif args.v:
        # avrdude 8 prints the signature only in verbose mode. Without -v a
        # successful read is silent, which the tool once mistook for failure.
        emit_signature(args.p)

    if args.n or not args.U:
        err(DONE)
        return 0

    # -- the write -----------------------------------------------------

    spec = args.U[0]
    try:
        path = _path_from_spec(spec)
    except ValueError:
        err(f"Error: invalid memory specification {spec!r}\n")
        err(DONE)
        return 1

    try:
        size = _measure(path)
    except OSError:
        err(f"Error: can't open input file {path}: No such file or directory\n")
        err(DONE)
        return 1

    slow = port == "COM_SLOW"
    pace = 6.0 if slow else 0.0

    if args.e:
        err("Erasing chip\n")

    err(f"Processing -U {spec}\n")
    err(f"Reading {size} bytes for flash from input file {path}\n")
    err(f"Writing {size} bytes to flash\n")
    draw_bar("Writing", pace or 0.4, steps=20 if slow else 10)

    if args.V:
        err(DONE)
        return 0

    if port == "COM_VERIFYFAIL":
        draw_bar("Reading", pace or 0.2, steps=5)
        err("Error: verification error, first mismatch at byte 0x0200\n")
        err("       0x0c != 0xff\n")
        err("Error: verification error; content mismatch\n")
        err(DONE)
        return 1

    draw_bar("Reading", pace or 0.3, steps=10)
    err(f"{size} bytes of flash verified\n")
    err(DONE)
    return 0


#: Format characters avrdude accepts at the end of a -U spec.
_FORMATS = set("iravdmsIhbo")


def _path_from_spec(spec: str) -> str:
    """Pull the filename out of ``flash:w:C:\\builds\\fw.hex:i``.

    Splitting on ":" from the left eats the Windows drive letter, so the
    trailing format is stripped from the right first. The suffix is optional -
    ``-U flash:w:fw.hex`` is valid and means "work the format out".
    """
    parts = spec.split(":", 2)
    if len(parts) < 3:
        raise ValueError(spec)
    rest = parts[2]
    if len(rest) > 2 and rest[-2] == ":" and rest[-1] in _FORMATS:
        rest = rest[:-2]
    if not rest:
        raise ValueError(spec)
    return rest


def _measure(path: str) -> int:
    """Count the bytes an Intel HEX file puts in flash, like avrdude reports."""
    with open(path, "rb") as handle:
        raw = handle.read()
    if not raw.lstrip().startswith(b":"):
        return len(raw)
    total = 0
    for line in raw.decode("ascii", errors="replace").splitlines():
        line = line.strip()
        if len(line) < 11 or not line.startswith(":"):
            continue
        if int(line[7:9], 16) == 0x00:
            total += int(line[1:3], 16)
    return total


if __name__ == "__main__":
    raise SystemExit(main())
