"""What Windows itself might do to this program.

These used to live in a separate .cmd script shipped beside the executable.
Folding them in here means the program has nothing sitting next to it that can
be lost, renamed, or blocked by a script policy - the operator gets one
executable and nothing else to run.

Standard library only: winreg and plain file access. Nothing here shells out,
so it works the same whether the tool is frozen or run from source.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

#: Smart App Control states, as Windows records them.
SAC_OFF = 0
SAC_ENFORCED = 1
SAC_EVALUATION = 2

_SAC_KEY = r"SYSTEM\CurrentControlSet\Control\CI\Policy"
_SAC_VALUE = "VerifiedAndReputablePolicyState"


@dataclass(frozen=True)
class WindowsEnvironment:
    """What the operating system thinks of this program."""

    is_windows: bool
    release: str
    smart_app_control: int | None
    marked_as_downloaded: bool
    program_path: Path

    @property
    def sac_enforced(self) -> bool:
        return self.smart_app_control == SAC_ENFORCED

    @property
    def sac_description(self) -> str:
        return {
            SAC_OFF: "off",
            SAC_ENFORCED: "on (enforcing)",
            SAC_EVALUATION: "evaluation mode",
        }.get(self.smart_app_control, "not present on this Windows version")


def program_path() -> Path:
    """The executable when frozen, the entry script otherwise."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def smart_app_control_state() -> int | None:
    """Read Smart App Control's state, or None where the key does not exist.

    It is on by default on new Windows 11 installs and refuses to run unsigned
    executables that have no established reputation, which is what any
    PyInstaller build is. Reading it lets the program say so plainly instead of
    leaving the operator with a bare Windows dialog.
    """
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:  # pragma: no cover - Windows only
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _SAC_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, _SAC_VALUE)
            return int(value)
    except (OSError, ValueError, TypeError):
        return None


def is_marked_as_downloaded(path: Path | None = None) -> bool:
    """True when the file still carries Windows' mark of the web.

    Windows attaches this to anything that arrived by email or download, and it
    is the usual reason a freshly extracted copy refuses to start. It lives in
    an alternate data stream, which is just a file with a colon in its name.
    """
    if os.name != "nt":
        return False
    target = Path(path) if path else program_path()
    try:
        with open(f"{target}:Zone.Identifier", "rb"):
            return True
    except OSError:
        return False


def describe() -> WindowsEnvironment:
    return WindowsEnvironment(
        is_windows=os.name == "nt",
        release=_release(),
        smart_app_control=smart_app_control_state(),
        marked_as_downloaded=is_marked_as_downloaded(),
        program_path=program_path(),
    )


def _release() -> str:
    import platform

    parts = [platform.system(), platform.release()]
    version = platform.version()
    if version:
        parts.append(f"build {version.split('.')[-1]}")
    return " ".join(p for p in parts if p)
