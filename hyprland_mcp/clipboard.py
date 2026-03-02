"""Clipboard access via wl-copy and wl-paste."""

import asyncio

from .errors import ClipboardError, require_tool


async def read() -> str:
    """Read clipboard contents as text."""
    require_tool("wl-paste")
    proc = await asyncio.create_subprocess_exec(
        "wl-paste", "-n",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ClipboardError(f"wl-paste failed: {stderr.decode().strip()}")
    return stdout.decode()


async def write(text: str) -> None:
    """Write text to clipboard."""
    require_tool("wl-copy")
    proc = await asyncio.create_subprocess_exec(
        "wl-copy",
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate(input=text.encode())
    if proc.returncode != 0:
        raise ClipboardError(f"wl-copy failed: {stderr.decode().strip()}")
