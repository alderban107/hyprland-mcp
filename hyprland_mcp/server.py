"""Hyprland MCP server — desktop automation tools for Claude."""

from mcp.server.fastmcp import FastMCP, Image

from . import hyprctl
from .errors import check_tools

mcp = FastMCP(
    "hyprland",
    instructions=(
        "Desktop automation server for Hyprland (Wayland). "
        "Provides screenshots, mouse/keyboard input, window management, "
        "clipboard access, and app launching. All tools wrap native Hyprland "
        "and Wayland utilities — no X11 required."
    ),
)


# ── Monitors & Workspaces ──────────────────────────────────────────────


@mcp.tool()
async def list_monitors() -> str:
    """List all connected monitors with resolution, position, and active workspace."""
    monitors = await hyprctl.query("monitors")
    lines = []
    for m in monitors:
        lines.append(
            f"- {m['name']}: {m['width']}x{m['height']}@{m['refreshRate']:.0f}Hz "
            f"at ({m['x']},{m['y']}), workspace {m['activeWorkspace']['name']}"
            f"{' [focused]' if m.get('focused') else ''}"
        )
    return "\n".join(lines)


@mcp.tool()
async def list_workspaces() -> str:
    """List all active workspaces with window counts."""
    workspaces = await hyprctl.query("workspaces")
    workspaces.sort(key=lambda w: w["id"])
    lines = []
    for w in workspaces:
        lines.append(
            f"- Workspace {w['name']} (id={w['id']}): "
            f"{w['windows']} window(s), monitor {w['monitor']}"
        )
    return "\n".join(lines)


@mcp.tool()
async def switch_workspace(workspace: str) -> str:
    """Switch to a workspace by name or number.

    Args:
        workspace: Workspace name or number (e.g. "1", "3", "special:scratchpad")
    """
    await hyprctl.dispatch("workspace", workspace)
    return f"Switched to workspace {workspace}"


@mcp.tool()
async def get_cursor_position() -> str:
    """Get the current cursor position in absolute layout coordinates."""
    pos = await hyprctl.query("cursorpos")
    return f"Cursor at ({pos['x']}, {pos['y']})"


# ── Window Management ──────────────────────────────────────────────────


@mcp.tool()
async def list_windows(workspace: int | None = None, monitor: str | None = None) -> str:
    """List all open windows with class, title, size, and position.

    Args:
        workspace: Filter to a specific workspace number
        monitor: Filter to a specific monitor name
    """
    clients = await hyprctl.query("clients")
    if workspace is not None:
        clients = [c for c in clients if c["workspace"]["id"] == workspace]
    if monitor is not None:
        clients = [c for c in clients if c["monitor"] == monitor]
    if not clients:
        return "No windows found matching the filter."
    lines = []
    for c in clients:
        focused = " [focused]" if c.get("focusHistoryID") == 0 else ""
        lines.append(
            f"- [{c['class']}] \"{c['title']}\" — "
            f"{c['size'][0]}x{c['size'][1]} at ({c['at'][0]},{c['at'][1]}), "
            f"workspace {c['workspace']['name']}{focused}"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_active_window() -> str:
    """Get details about the currently focused window."""
    w = await hyprctl.query("activewindow")
    if not w or not w.get("class"):
        return "No window is currently focused."
    return (
        f"Active window: [{w['class']}] \"{w['title']}\"\n"
        f"Size: {w['size'][0]}x{w['size'][1]}, Position: ({w['at'][0]},{w['at'][1]})\n"
        f"Workspace: {w['workspace']['name']}, Monitor: {w['monitor']}\n"
        f"Floating: {w['floating']}, Fullscreen: {w['fullscreen']}"
    )


@mcp.tool()
async def focus_window(target: str) -> str:
    """Focus a window by class or title.

    Args:
        target: Window selector — "class:firefox", "title:My Document", etc.
    """
    await hyprctl.dispatch("focuswindow", target)
    return f"Focused window matching '{target}'"


@mcp.tool()
async def close_window(target: str | None = None) -> str:
    """Close a window (sends WM_CLOSE — apps can show save dialogs).

    Args:
        target: Window selector (e.g. "class:firefox"). If omitted, closes the active window.
    """
    await hyprctl.dispatch("closewindow", target or "")
    return f"Closed window{f' matching {target!r}' if target else ' (active)'}"


@mcp.tool()
async def move_window(
    target: str | None = None,
    x: int | None = None,
    y: int | None = None,
    workspace: str | None = None,
) -> str:
    """Move a window to a position or workspace.

    Args:
        target: Window selector. If omitted, moves the active window.
        x: Target X position in pixels
        y: Target Y position in pixels
        workspace: Target workspace name/number to move the window to
    """
    results = []
    addr = target or ""
    if x is not None and y is not None:
        await hyprctl.dispatch("movewindowpixel", f"exact {x} {y},{addr}")
        results.append(f"Moved to ({x},{y})")
    if workspace is not None:
        if target:
            await hyprctl.dispatch("movetoworkspace", f"{workspace},{target}")
        else:
            await hyprctl.dispatch("movetoworkspace", workspace)
        results.append(f"Moved to workspace {workspace}")
    if not results:
        return "No position or workspace specified — nothing to do."
    return "; ".join(results)


@mcp.tool()
async def resize_window(
    width: int,
    height: int,
    target: str | None = None,
) -> str:
    """Resize a window to exact pixel dimensions.

    Args:
        width: Target width in pixels
        height: Target height in pixels
        target: Window selector. If omitted, resizes the active window.
    """
    await hyprctl.dispatch("resizewindowpixel", f"exact {width} {height},{target or ''}")
    return f"Resized to {width}x{height}"


@mcp.tool()
async def toggle_fullscreen(mode: str = "fullscreen") -> str:
    """Toggle fullscreen for the active window.

    Args:
        mode: "fullscreen" for real fullscreen, "maximize" for maximized (keeps bar)
    """
    flag = "0" if mode == "fullscreen" else "1"
    await hyprctl.dispatch("fullscreen", flag)
    return f"Toggled {mode}"


@mcp.tool()
async def toggle_floating(target: str | None = None) -> str:
    """Toggle floating mode for a window.

    Args:
        target: Window selector. If omitted, toggles the active window.
    """
    await hyprctl.dispatch("togglefloating", target or "")
    return f"Toggled floating{f' for {target}' if target else ''}"


# ── Clipboard ──────────────────────────────────────────────────────────


@mcp.tool()
async def clipboard_read() -> str:
    """Read the current clipboard contents as text."""
    from . import clipboard
    return await clipboard.read()


@mcp.tool()
async def clipboard_write(text: str) -> str:
    """Write text to the clipboard.

    Args:
        text: The text to copy to the clipboard
    """
    from . import clipboard
    await clipboard.write(text)
    return f"Copied {len(text)} characters to clipboard"


# ── App Launching ──────────────────────────────────────────────────────


@mcp.tool()
async def launch_app(command: str) -> str:
    """Launch an application (detached, via Hyprland).

    Args:
        command: The command to run (e.g. "firefox", "kitty", "nautilus ~/Documents")
    """
    await hyprctl.dispatch("exec", command)
    return f"Launched: {command}"


# ── Input: Mouse ───────────────────────────────────────────────────────


@mcp.tool()
async def mouse_move(x: int, y: int) -> str:
    """Move the mouse cursor to absolute layout coordinates.

    Uses Hyprland's native movecursor — pixel-accurate, no acceleration issues.

    Args:
        x: Target X coordinate
        y: Target Y coordinate
    """
    from . import input as inp
    await inp.move_cursor(x, y)
    return f"Moved cursor to ({x}, {y})"


@mcp.tool()
async def mouse_click(
    button: str = "left",
    x: int | None = None,
    y: int | None = None,
    double: bool = False,
) -> str:
    """Click the mouse at a position (or current position if no coordinates given).

    Args:
        button: "left", "right", or "middle"
        x: X coordinate to click at (optional — clicks at current position if omitted)
        y: Y coordinate to click at (optional)
        double: Whether to double-click
    """
    from . import input as inp
    if x is not None and y is not None:
        await inp.move_cursor(x, y)
    await inp.click(button, double=double)
    pos = f" at ({x},{y})" if x is not None and y is not None else ""
    kind = "Double-clicked" if double else "Clicked"
    return f"{kind} {button}{pos}"


@mcp.tool()
async def mouse_scroll(
    direction: str = "down",
    amount: int = 3,
    x: int | None = None,
    y: int | None = None,
) -> str:
    """Scroll the mouse wheel.

    Args:
        direction: "up" or "down"
        amount: Number of scroll steps (default 3)
        x: X coordinate to scroll at (optional)
        y: Y coordinate to scroll at (optional)
    """
    from . import input as inp
    if x is not None and y is not None:
        await inp.move_cursor(x, y)
    await inp.scroll(direction, amount)
    pos = f" at ({x},{y})" if x is not None and y is not None else ""
    return f"Scrolled {direction} {amount} steps{pos}"


@mcp.tool()
async def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
) -> str:
    """Drag from one position to another.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        button: Mouse button to hold during drag ("left", "right", "middle")
    """
    from . import input as inp
    await inp.drag(start_x, start_y, end_x, end_y, button)
    return f"Dragged {button} from ({start_x},{start_y}) to ({end_x},{end_y})"


# ── Input: Keyboard ────────────────────────────────────────────────────


@mcp.tool()
async def type_text(text: str, delay_ms: int = 0) -> str:
    """Type text as if from a keyboard.

    Args:
        text: The text to type
        delay_ms: Delay between keystrokes in milliseconds (0 = instant)
    """
    from . import input as inp
    await inp.type_text(text, delay_ms=delay_ms)
    return f"Typed {len(text)} characters"


@mcp.tool()
async def key_press(keys: str, target: str | None = None) -> str:
    """Press a key combination.

    Uses Hyprland's native sendshortcut — can target specific windows without focusing them.

    Args:
        keys: Key combo string like "ctrl+c", "alt+F4", "super+1", "Return"
        target: Optional window selector to send the key to (e.g. "class:firefox").
                If omitted, sends to the active window.
    """
    from . import input as inp
    await inp.key_press(keys, target=target)
    return f"Pressed {keys}{f' on {target}' if target else ''}"


@mcp.tool()
async def send_shortcut(mods: str, key: str, target: str | None = None) -> str:
    """Send a keyboard shortcut via Hyprland (can target specific windows).

    Args:
        mods: Modifier keys (e.g. "CTRL", "SUPER SHIFT", "ALT CTRL", or "" for none)
        key: Key name (e.g. "c", "F4", "Return", "space")
        target: Optional window selector (e.g. "class:firefox"). Empty = active window.
    """
    target_str = target or ""
    await hyprctl.dispatch("sendshortcut", f"{mods}, {key}, {target_str}")
    desc = f"{mods}+{key}" if mods else key
    return f"Sent shortcut {desc}{f' to {target}' if target else ''}"


# ── Screenshot ─────────────────────────────────────────────────────────


@mcp.tool()
async def screenshot(
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    max_width: int = 1024,
    quality: int = 60,
    include_cursor: bool = False,
) -> list:
    """Take a screenshot and return it as an inline image with coordinate mapping.

    Returns the image AND a coordinate mapping guide so you can convert image
    pixel positions to absolute screen coordinates for mouse tools.

    Supports three capture modes:
    - Full desktop/monitor (default): overview at reduced resolution
    - Window: capture a specific window by class/title
    - Region: capture a specific rectangle at higher resolution

    Args:
        monitor: Capture a specific monitor (e.g. "DP-1"). Default: all monitors.
        window: Capture a specific window by selector (e.g. "class:firefox")
        region: Capture a region as "X,Y WxH" (e.g. "100,200 800x600")
        max_width: Maximum output width in pixels (default 1024, lower = smaller output)
        quality: JPEG quality 1-100 (default 60, lower = smaller output)
        include_cursor: Whether to include the cursor in the screenshot
    """
    from . import screenshot as ss
    image, coord_info = await ss.take_screenshot(
        monitor=monitor,
        window=window,
        region=region,
        max_width=max_width,
        quality=quality,
        include_cursor=include_cursor,
    )
    return [image, coord_info]


# ── OCR & Smart Actions ────────────────────────────────────────────────


async def _auto_scope_capture(
    monitor: str | None, window: str | None, region: str | None,
) -> tuple[bytes, int, int]:
    """Capture screenshot, auto-scoping to the active window if no scope specified.

    When no monitor/window/region is given, captures just the active window
    instead of the entire desktop. This gives OCR a smaller, higher-quality
    image to work with — much better accuracy than a full multi-monitor capture.
    """
    from . import screenshot as ss

    if monitor or window or region:
        return await ss.capture_raw(monitor=monitor, window=window, region=region)

    # Auto-scope to active window
    active = await hyprctl.query("activewindow")
    if active and active.get("class"):
        x, y = active["at"]
        w, h = active["size"]
        return await ss.capture_raw(region=f"{x},{y} {w}x{h}")

    # No active window — fall back to full desktop
    return await ss.capture_raw()


@mcp.tool()
async def find_text_on_screen(
    target: str,
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    scope: str = "auto",
) -> str:
    """Find text on screen using OCR. Returns matching locations in screen coordinates.

    Take a screenshot, run OCR, and find all occurrences of the target text.
    Coordinates are in absolute screen space — ready to pass to mouse_click.

    Args:
        target: Text to find (case-insensitive, supports multi-word)
        monitor: Limit search to a specific monitor
        window: Limit search to a specific window (e.g. "class:discord")
        region: Limit search to a region "X,Y WxH"
        scope: "auto" (default) captures just the active window for better accuracy.
               "full" captures the entire desktop.
    """
    from . import screenshot as ss, ocr

    if scope == "full" and not (monitor or window or region):
        png_bytes, origin_x, origin_y = await ss.capture_raw()
    else:
        png_bytes, origin_x, origin_y = await _auto_scope_capture(
            monitor, window, region,
        )

    boxes = ocr.extract_boxes(png_bytes)
    matches = ocr.find_text(boxes, target)

    if not matches:
        all_text = ocr.extract_text(png_bytes)
        preview = all_text[:500] + "..." if len(all_text) > 500 else all_text
        return f"Text '{target}' not found.\n\nOCR detected text:\n{preview}"

    lines = [f"Found {len(matches)} match(es) for '{target}':"]
    for m in matches:
        screen_x = m["x"] + origin_x + m["w"] // 2
        screen_y = m["y"] + origin_y + m["h"] // 2
        lines.append(
            f"- \"{m['text']}\" at screen ({screen_x}, {screen_y}) "
            f"[box: {m['x']+origin_x},{m['y']+origin_y} {m['w']}x{m['h']}, "
            f"conf: {m['conf']}%]"
        )
    return "\n".join(lines)


@mcp.tool()
async def click_text(
    target: str,
    button: str = "left",
    double: bool = False,
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    occurrence: int = 1,
    scope: str = "auto",
) -> str:
    """Find text on screen and click it — screenshot + OCR + click in one call.

    By default, searches only the active window for better accuracy and speed.

    Args:
        target: Text to find and click (case-insensitive)
        button: Mouse button ("left", "right", "middle")
        double: Whether to double-click
        monitor: Limit search to a specific monitor
        window: Limit search to a specific window (e.g. "class:discord")
        region: Limit search to a region "X,Y WxH"
        occurrence: Which match to click if multiple found (1 = first/best, 2 = second, etc.)
        scope: "auto" (default) searches the active window. "full" searches entire desktop.
    """
    from . import screenshot as ss, ocr, input as inp

    if scope == "full" and not (monitor or window or region):
        png_bytes, origin_x, origin_y = await ss.capture_raw()
    else:
        png_bytes, origin_x, origin_y = await _auto_scope_capture(
            monitor, window, region,
        )

    boxes = ocr.extract_boxes(png_bytes)
    matches = ocr.find_text(boxes, target)

    if not matches:
        all_text = ocr.extract_text(png_bytes)
        preview = all_text[:500] + "..." if len(all_text) > 500 else all_text
        return f"Could not find '{target}' on screen.\n\nOCR detected text:\n{preview}"

    if occurrence > len(matches):
        return (
            f"Only found {len(matches)} match(es) for '{target}', "
            f"but occurrence={occurrence} requested."
        )

    match = matches[occurrence - 1]
    screen_x = match["x"] + origin_x + match["w"] // 2
    screen_y = match["y"] + origin_y + match["h"] // 2

    await inp.move_cursor(screen_x, screen_y)
    await inp.click(button, double=double)

    kind = "Double-clicked" if double else "Clicked"
    return (
        f"{kind} '{match['text']}' at ({screen_x}, {screen_y}) "
        f"[conf: {match['conf']}%]"
    )


@mcp.tool()
async def type_into(
    text: str,
    input_hint: str | None = None,
    submit: bool = False,
    window: str | None = None,
) -> str:
    """Find a text input field, click it, type text, and optionally submit.

    Combines focus + OCR + click + type + Enter into one action. Searches for
    placeholder text in the active window to find the input field.

    Args:
        text: The text to type
        input_hint: Placeholder or label text near the input field to click on
                    (e.g. "Type a message", "Search", "Message"). If omitted,
                    tries common placeholders.
        submit: Whether to press Enter after typing (default False)
        window: Target a specific window (e.g. "class:signal"). Default: active window.
    """
    from . import screenshot as ss, ocr, input as inp
    import asyncio

    # Focus the window if specified
    if window:
        await hyprctl.dispatch("focuswindow", window)
        await asyncio.sleep(0.1)

    png_bytes, origin_x, origin_y = await _auto_scope_capture(
        None, window, None,
    )

    boxes = ocr.extract_boxes(png_bytes)

    # Try to find the input field by hint text or common placeholders
    hints = [input_hint] if input_hint else [
        "Type a message",
        "Message",
        "Search",
        "Type here",
        "Write a message",
        "Enter message",
        "Say something",
    ]

    match = None
    used_hint = None
    for hint in hints:
        matches = ocr.find_text(boxes, hint)
        if matches:
            match = matches[0]
            used_hint = hint
            break

    if not match:
        all_text = ocr.extract_text(png_bytes)
        preview = all_text[:500] + "..." if len(all_text) > 500 else all_text
        tried = ", ".join(f'"{h}"' for h in hints)
        return (
            f"Could not find input field. Tried: {tried}\n\n"
            f"OCR detected text:\n{preview}"
        )

    # Click the center of the matched text
    screen_x = match["x"] + origin_x + match["w"] // 2
    screen_y = match["y"] + origin_y + match["h"] // 2

    await inp.move_cursor(screen_x, screen_y)
    await inp.click("left")
    await asyncio.sleep(0.1)

    # Type the text
    await inp.type_text(text)

    result = f"Found '{used_hint}' at ({screen_x},{screen_y}), typed {len(text)} chars"

    # Submit if requested
    if submit:
        await asyncio.sleep(0.05)
        await hyprctl.dispatch("sendshortcut", ", Return, ")
        result += ", pressed Enter"

    return result


@mcp.tool()
async def screenshot_with_ocr(
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    max_width: int = 1024,
    quality: int = 60,
    scope: str = "auto",
) -> list:
    """Take a screenshot AND run OCR, returning both the image and extracted text.

    More efficient than calling screenshot + find_text_on_screen separately.
    The text includes screen coordinates for every detected word.

    Args:
        monitor: Capture a specific monitor
        window: Capture a specific window (e.g. "class:discord")
        region: Capture a region as "X,Y WxH"
        max_width: Maximum output width for the image (default 1024)
        quality: JPEG quality for the image (default 60)
        scope: "auto" (default) captures the active window. "full" captures entire desktop.
    """
    from . import screenshot as ss, ocr

    if scope == "full" and not (monitor or window or region):
        png_bytes, origin_x, origin_y = await ss.capture_raw()
    else:
        png_bytes, origin_x, origin_y = await _auto_scope_capture(
            monitor, window, region,
        )

    text = ocr.extract_text(png_bytes)
    image, _ = ss.resize_and_compress(png_bytes, max_width=max_width, quality=quality)

    return [image, f"OCR text:\n{text}"]


# ── Entry Point ────────────────────────────────────────────────────────


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
