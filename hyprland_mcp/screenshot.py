"""Screenshot capture and optimization using grim + Pillow."""

import asyncio
import io

from PIL import Image as PILImage
from mcp.server.fastmcp import Image

from . import hyprctl
from .errors import ScreenshotError, require_tool


def _compute_scale(native_width: int, max_width: int) -> float | None:
    """Compute scale factor to fit within max_width. Returns None if no scaling needed."""
    if native_width <= max_width:
        return None
    return max_width / native_width


async def _get_monitor_width(monitor: str | None) -> int:
    """Get the native width of a monitor (or the widest if none specified)."""
    monitors = await hyprctl.query("monitors")
    if monitor:
        for m in monitors:
            if m["name"] == monitor:
                return m["width"]
        raise ScreenshotError(f"Monitor '{monitor}' not found")
    # No specific monitor — use combined width for multi-monitor, or single monitor width
    if len(monitors) == 1:
        return monitors[0]["width"]
    # Multi-monitor: total horizontal span
    max_x = max(m["x"] + m["width"] for m in monitors)
    min_x = min(m["x"] for m in monitors)
    return max_x - min_x


async def _get_window_geometry(selector: str) -> str:
    """Get a window's geometry as 'X,Y WxH' for grim -g."""
    clients = await hyprctl.query("clients")
    for c in clients:
        # Match by class or title
        if selector.startswith("class:"):
            target = selector[6:]
            if c["class"].lower() == target.lower():
                x, y = c["at"]
                w, h = c["size"]
                return f"{x},{y} {w}x{h}"
        elif selector.startswith("title:"):
            target = selector[6:]
            if target.lower() in c["title"].lower():
                x, y = c["at"]
                w, h = c["size"]
                return f"{x},{y} {w}x{h}"
        elif c["class"].lower() == selector.lower():
            x, y = c["at"]
            w, h = c["size"]
            return f"{x},{y} {w}x{h}"
    raise ScreenshotError(f"No window found matching '{selector}'")


async def capture_raw(
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    include_cursor: bool = False,
) -> tuple[bytes, int, int]:
    """Capture a raw PNG screenshot. Returns (png_bytes, origin_x, origin_y).

    origin_x/y are the screen coordinates of the top-left corner of the capture.
    For full desktop or monitor captures, this comes from monitor position.
    For region captures, it's parsed from the region string.
    For window captures, it's the window position.
    """
    require_tool("grim")

    cmd = ["grim", "-t", "png", "-l", "0"]
    origin_x, origin_y = 0, 0

    if include_cursor:
        cmd.append("-c")

    if window:
        geometry = await _get_window_geometry(window)
        cmd.extend(["-g", geometry])
        # Parse origin from geometry "X,Y WxH"
        pos_part = geometry.split(" ")[0]
        origin_x, origin_y = (int(v) for v in pos_part.split(","))
    elif region:
        cmd.extend(["-g", region])
        pos_part = region.split(" ")[0]
        origin_x, origin_y = (int(v) for v in pos_part.split(","))
    elif monitor:
        cmd.extend(["-o", monitor])
        monitors = await hyprctl.query("monitors")
        for m in monitors:
            if m["name"] == monitor:
                origin_x, origin_y = m["x"], m["y"]
                break

    cmd.append("-")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ScreenshotError(f"grim failed: {stderr.decode().strip()}")
    if not stdout:
        raise ScreenshotError("grim produced no output")

    return stdout, origin_x, origin_y


def resize_and_compress(
    png_bytes: bytes,
    max_width: int = 1024,
    quality: int = 60,
) -> tuple[Image, float]:
    """Resize and JPEG-compress a PNG. Returns (Image, scale_factor)."""
    img = PILImage.open(io.BytesIO(png_bytes))
    scale = 1.0

    if img.width > max_width:
        scale = max_width / img.width
        new_size = (max_width, int(img.height * scale))
        img = img.resize(new_size, PILImage.LANCZOS)

    if img.mode == "RGBA":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)

    return Image(data=buf.getvalue(), format="jpeg"), scale


async def take_screenshot(
    monitor: str | None = None,
    window: str | None = None,
    region: str | None = None,
    max_width: int = 1024,
    quality: int = 60,
    include_cursor: bool = False,
) -> tuple[Image, str]:
    """Capture a screenshot, resize to fit max_width.

    Returns (Image, coordinate_info_string) where coordinate_info_string
    explains how to map image pixel positions to absolute screen coordinates.
    """
    png_bytes, origin_x, origin_y = await capture_raw(
        monitor=monitor, window=window, region=region, include_cursor=include_cursor,
    )

    # Get native dimensions before resize
    native_img = PILImage.open(io.BytesIO(png_bytes))
    native_w, native_h = native_img.width, native_img.height

    image, scale = resize_and_compress(png_bytes, max_width=max_width, quality=quality)

    # Build coordinate mapping info
    img_w = int(native_w * scale) if scale != 1.0 else native_w
    img_h = int(native_h * scale) if scale != 1.0 else native_h
    inv_scale = 1.0 / scale if scale != 1.0 else 1.0

    coord_info = (
        f"Coordinate mapping: This {img_w}x{img_h} image covers screen region "
        f"starting at absolute ({origin_x}, {origin_y}), "
        f"native size {native_w}x{native_h}.\n"
        f"To convert image coordinates to absolute screen coordinates:\n"
        f"  screen_x = image_x * {inv_scale:.2f} + {origin_x}\n"
        f"  screen_y = image_y * {inv_scale:.2f} + {origin_y}\n"
        f"IMPORTANT: Always use absolute screen coordinates with mouse tools, "
        f"never raw image pixel positions."
    )

    return image, coord_info
