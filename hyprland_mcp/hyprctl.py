"""Async wrappers for hyprctl IPC commands."""

import asyncio
import json

from .errors import HyprctlError, require_tool


async def query(command: str) -> dict | list:
    """Run a hyprctl query command and return parsed JSON.

    Example: query("monitors") → list of monitor dicts
    """
    require_tool("hyprctl")
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", command, "-j",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HyprctlError(f"hyprctl {command} failed: {stderr.decode().strip()}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise HyprctlError(f"Failed to parse hyprctl {command} output: {e}") from e


async def dispatch(command: str, args: str = "") -> str:
    """Run a hyprctl dispatch command.

    Example: dispatch("focuswindow", "class:firefox")
    """
    require_tool("hyprctl")
    cmd = ["hyprctl", "dispatch", command]
    if args:
        cmd.append(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HyprctlError(
            f"hyprctl dispatch {command} {args} failed: {stderr.decode().strip()}"
        )
    return stdout.decode().strip()


async def batch(commands: list[str]) -> str:
    """Run multiple hyprctl dispatch commands in a batch.

    Each command should be a full dispatch string like "dispatch focuswindow class:firefox".
    """
    require_tool("hyprctl")
    batch_str = " ; ".join(commands)
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", "--batch", batch_str,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HyprctlError(f"hyprctl --batch failed: {stderr.decode().strip()}")
    return stdout.decode().strip()
