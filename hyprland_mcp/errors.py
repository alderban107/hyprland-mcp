"""Exception hierarchy and tool availability checks."""

import shutil


class HyprlandMCPError(Exception):
    """Base exception for hyprland-mcp."""


class HyprctlError(HyprlandMCPError):
    """Error communicating with Hyprland via hyprctl."""


class ScreenshotError(HyprlandMCPError):
    """Error capturing screenshot via grim."""


class InputError(HyprlandMCPError):
    """Error simulating input via ydotool/wtype."""


class ClipboardError(HyprlandMCPError):
    """Error accessing clipboard via wl-copy/wl-paste."""


class ToolNotFoundError(HyprlandMCPError):
    """A required system tool is not installed."""

    def __init__(self, tool: str) -> None:
        self.tool = tool
        super().__init__(
            f"Required tool '{tool}' is not installed. "
            f"Install it with your package manager (e.g. pacman -S {tool})."
        )


REQUIRED_TOOLS = {
    "grim": "Screenshots",
    "hyprctl": "Hyprland IPC",
    "wtype": "Keyboard input",
    "ydotool": "Mouse input",
    "wl-copy": "Clipboard write",
    "wl-paste": "Clipboard read",
    "tesseract": "OCR (text recognition)",
}


def check_tools() -> dict[str, bool]:
    """Check which system tools are installed. Returns {tool_name: is_available}."""
    return {tool: shutil.which(tool) is not None for tool in REQUIRED_TOOLS}


def require_tool(name: str) -> None:
    """Raise ToolNotFoundError if the given tool is not installed."""
    if shutil.which(name) is None:
        raise ToolNotFoundError(name)
