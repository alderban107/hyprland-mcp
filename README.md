# hyprland-mcp

MCP server for Hyprland desktop automation. Gives AI assistants the ability to see the screen, control mouse and keyboard, manage windows, and interact with the desktop — all through Hyprland's native Wayland tools.

Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), but works with any MCP client.

## What it does

- **Screenshots** — Capture the full desktop, a specific monitor, window, or region. Images are automatically resized and JPEG-compressed to fit within MCP output limits. Every screenshot includes a coordinate mapping so the AI knows how to translate image positions to screen coordinates.
- **OCR** — Find and click text on screen using Tesseract. `click_text("Send")` captures a screenshot, runs OCR, finds the text, and clicks it — all in one tool call. Auto-scopes to the active window for better accuracy.
- **Mouse** — Move, click, scroll, and drag. Positioning uses Hyprland's native `movecursor` (pixel-accurate, no mouse acceleration issues).
- **Keyboard** — Type text or send key combinations. Shortcuts can target specific windows without focusing them.
- **Window management** — List, focus, close, move, resize, fullscreen, and float windows.
- **Workspaces & monitors** — List workspaces, switch between them, query monitor layout and cursor position.
- **Clipboard** — Read and write clipboard text.
- **App launching** — Launch applications through Hyprland (detached, no shell expansion).

## Requirements

- [Hyprland](https://hyprland.org/) (Wayland compositor)
- Python 3.10+
- System tools:
  - `grim` — screenshots
  - `hyprctl` — Hyprland IPC (comes with Hyprland)
  - `wtype` — keyboard input
  - `ydotool` — mouse click/scroll events
  - `wl-copy` / `wl-paste` — clipboard (`wl-clipboard` package)
  - `tesseract` — OCR text recognition (`tesseract` + `tesseract-data-eng` packages)

On Arch-based distros:
```bash
sudo pacman -S grim wtype ydotool wl-clipboard tesseract tesseract-data-eng
```

## Installation

```bash
git clone https://github.com/alderban107/hyprland-mcp.git
cd hyprland-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Register with Claude Code

```bash
claude mcp add --transport stdio --scope user hyprland -- /path/to/hyprland-mcp/.venv/bin/hyprland-mcp
```

Or using the Python module directly:

```bash
claude mcp add --transport stdio --scope user hyprland -- /path/to/hyprland-mcp/.venv/bin/python3 -m hyprland_mcp.server
```

Verify with `claude mcp list` — you should see `hyprland: ✓ Connected`.

## Tools (27)

### Screenshot & OCR

| Tool | Description |
|------|-------------|
| `screenshot` | Capture desktop, monitor, window, or region. Returns inline JPEG + coordinate mapping for translating image positions to screen coordinates. |
| `screenshot_with_ocr` | Screenshot + OCR in one call. Returns the image and all detected text. Auto-scopes to active window. |
| `click_text` | Find text on screen via OCR and click it. One tool call replaces screenshot → parse → click. Auto-scopes to active window. |
| `find_text_on_screen` | Find text on screen via OCR. Returns screen coordinates of all matches, ready for `mouse_click`. |
| `type_into` | Find a text input field by placeholder text, click it, type, and optionally press Enter. |

### Mouse

| Tool | Description |
|------|-------------|
| `mouse_move` | Move cursor to absolute coordinates (pixel-accurate via Hyprland's `movecursor`) |
| `mouse_click` | Click at position or current location (left/right/middle, single/double) |
| `mouse_scroll` | Scroll wheel up/down at position or current location |
| `mouse_drag` | Click-drag from one position to another |

### Keyboard

| Tool | Description |
|------|-------------|
| `type_text` | Type text as keyboard input (via `wtype`) |
| `key_press` | Press a key combination like `ctrl+c`, `alt+F4` (via Hyprland `sendshortcut`) |
| `send_shortcut` | Send a shortcut with explicit modifiers and key, optionally targeting a specific window |

### Window Management

| Tool | Description |
|------|-------------|
| `list_windows` | List all windows with class, title, size, position (filterable by workspace/monitor) |
| `get_active_window` | Get details about the currently focused window |
| `focus_window` | Focus a window by class or title selector |
| `close_window` | Close a window (WM_CLOSE — apps can show save dialogs) |
| `move_window` | Move a window to a pixel position or workspace |
| `resize_window` | Resize a window to exact pixel dimensions |
| `toggle_fullscreen` | Toggle fullscreen or maximize mode |
| `toggle_floating` | Toggle floating mode |

### Workspace & Monitor

| Tool | Description |
|------|-------------|
| `list_monitors` | List connected monitors with resolution, position, refresh rate |
| `list_workspaces` | List active workspaces with window counts |
| `switch_workspace` | Switch to a workspace by name or number |
| `get_cursor_position` | Get current cursor position in absolute layout coordinates |

### Clipboard & System

| Tool | Description |
|------|-------------|
| `clipboard_read` | Read current clipboard text |
| `clipboard_write` | Write text to clipboard |
| `launch_app` | Launch an application (detached, via `hyprctl dispatch exec`) |

## How it works

### Screenshot coordinate mapping

Multi-monitor setups and image scaling make coordinate translation tricky. Every `screenshot` call returns a coordinate mapping alongside the image:

```
Coordinate mapping: This 941x1030 image covers screen region
starting at absolute (5447, 38), native size 941x1030.
To convert image coordinates to absolute screen coordinates:
  screen_x = image_x * 1.00 + 5447
  screen_y = image_y * 1.00 + 38
```

This prevents the AI from using image pixel positions directly as screen coordinates — a common failure mode on multi-monitor setups where monitors have different positions in the layout.

### OCR and dark themes

Tesseract OCR was designed for black text on white paper. Most desktop apps use dark themes, which tanks OCR accuracy. hyprland-mcp automatically detects dark-background screenshots and inverts them before running OCR, significantly improving text detection.

OCR tools auto-scope to the active window by default (configurable with `scope="full"` for the entire desktop). Smaller capture area = better OCR accuracy = more reliable coordinate mapping.

### Mouse positioning

Mouse movement uses `hyprctl dispatch movecursor` — Hyprland's native IPC command that sets the cursor to exact pixel coordinates. No mouse acceleration, no relative movement, no coordinate drift. ydotool is only used for click and scroll events (which don't involve positioning).

### Screenshot sizing

Screenshots are automatically scaled to fit within MCP output limits. Default: max width 1024px, JPEG quality 60. A 2560x1440 desktop becomes ~80-100KB — small enough for inline display in the conversation.

For reading fine text or UI details, use the `region` parameter to capture a smaller area at full resolution, or capture a specific `window`.

## Project structure

```
hyprland_mcp/
  server.py       # FastMCP instance, all tool definitions, entry point
  hyprctl.py      # Async wrappers for hyprctl IPC (query, dispatch, batch)
  screenshot.py   # grim capture + Pillow resize/compress + coordinate mapping
  input.py        # Mouse (movecursor + ydotool) and keyboard (wtype + sendshortcut)
  clipboard.py    # wl-copy / wl-paste wrappers
  ocr.py          # Tesseract OCR with dark-theme preprocessing
  errors.py       # Exception hierarchy + tool availability checks
```

## Safety

- `close_window` sends WM_CLOSE — apps can show "save changes?" dialogs. There is no force-kill tool.
- `launch_app` goes through `hyprctl dispatch exec` — detached from the MCP process, no shell expansion.
- No file system access — the MCP can see the screen and interact with it, but cannot read or write files.
- Missing system tools produce clear error messages listing what to install.

## License

MIT
