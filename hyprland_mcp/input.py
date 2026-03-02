"""Mouse and keyboard input simulation.

Mouse positioning: hyprctl dispatch movecursor (native, pixel-accurate)
Mouse events: ydotool (click, scroll — events only, no positioning)
Key combos: hyprctl dispatch sendshortcut (native, can target windows)
Text typing: wtype (only remaining wtype use)
"""

import asyncio

from . import hyprctl
from .errors import InputError, require_tool

# ydotool button codes (hex, with 0xC0 = down+up mask)
_BUTTON_MAP = {
    "left": "0xC0",
    "right": "0xC1",
    "middle": "0xC2",
}

# For mouse_drag: separate down/up codes
_BUTTON_DOWN = {
    "left": "0x40",
    "right": "0x41",
    "middle": "0x42",
}
_BUTTON_UP = {
    "left": "0x80",
    "right": "0x81",
    "middle": "0x82",
}


async def move_cursor(x: int, y: int) -> None:
    """Move cursor to absolute coordinates using Hyprland's native movecursor."""
    await hyprctl.dispatch("movecursor", f"{x} {y}")


async def click(button: str = "left", double: bool = False) -> None:
    """Click at the current cursor position using ydotool."""
    require_tool("ydotool")
    code = _BUTTON_MAP.get(button)
    if code is None:
        raise InputError(f"Unknown button: {button}. Use 'left', 'right', or 'middle'.")

    cmd = ["ydotool", "click", code]
    if double:
        cmd.extend(["-r", "2", "-D", "50"])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise InputError(f"ydotool click failed: {stderr.decode().strip()}")


async def scroll(direction: str = "down", amount: int = 3) -> None:
    """Scroll the mouse wheel using ydotool."""
    require_tool("ydotool")
    # ydotool mousemove --wheel: positive Y = down, negative Y = up
    y_val = amount if direction == "down" else -amount
    proc = await asyncio.create_subprocess_exec(
        "ydotool", "mousemove", "--wheel", "-x", "0", "-y", str(y_val),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise InputError(f"ydotool scroll failed: {stderr.decode().strip()}")


async def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
) -> None:
    """Drag from one position to another."""
    require_tool("ydotool")
    down_code = _BUTTON_DOWN.get(button)
    up_code = _BUTTON_UP.get(button)
    if down_code is None:
        raise InputError(f"Unknown button: {button}")

    # Move to start position
    await move_cursor(start_x, start_y)
    await asyncio.sleep(0.05)

    # Button down
    proc = await asyncio.create_subprocess_exec(
        "ydotool", "click", down_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()

    await asyncio.sleep(0.05)

    # Move to end position
    await move_cursor(end_x, end_y)
    await asyncio.sleep(0.05)

    # Button up
    proc = await asyncio.create_subprocess_exec(
        "ydotool", "click", up_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()


async def type_text(text: str, delay_ms: int = 0) -> None:
    """Type text using wtype."""
    require_tool("wtype")
    cmd = ["wtype"]
    if delay_ms > 0:
        cmd.extend(["-d", str(delay_ms)])
    cmd.extend(["--", text])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise InputError(f"wtype failed: {stderr.decode().strip()}")


async def key_press(keys: str, target: str | None = None) -> None:
    """Press a key combination using hyprctl dispatch sendshortcut.

    Args:
        keys: Key combo like "ctrl+c", "alt+F4", "Return", "super+1"
        target: Optional window selector
    """
    # Parse "ctrl+shift+c" into mods="CTRL SHIFT" and key="c"
    parts = keys.split("+")
    if len(parts) == 1:
        mods = ""
        key = parts[0]
    else:
        key = parts[-1]
        mods = " ".join(p.upper() for p in parts[:-1])

    target_str = target or ""
    await hyprctl.dispatch("sendshortcut", f"{mods}, {key}, {target_str}")
