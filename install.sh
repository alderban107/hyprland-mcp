#!/usr/bin/env bash
set -euo pipefail

# hyprland-mcp installer
# Usage: curl -sSL https://raw.githubusercontent.com/alderban107/hyprland-mcp/main/install.sh | bash

REPO="https://github.com/alderban107/hyprland-mcp.git"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

echo "hyprland-mcp installer"
echo "======================"
echo

# Check for Hyprland
if ! command -v hyprctl &>/dev/null; then
    error "hyprctl not found — this MCP server requires Hyprland."
    exit 1
fi
info "Hyprland detected"

# Check system dependencies
MISSING=()
for tool in grim wtype ydotool wl-copy wl-paste tesseract; do
    if ! command -v "$tool" &>/dev/null; then
        MISSING+=("$tool")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    warn "Missing system tools: ${MISSING[*]}"

    # Map tool names to package names
    PKGS=()
    for tool in "${MISSING[@]}"; do
        case "$tool" in
            wl-copy|wl-paste) PKGS+=("wl-clipboard") ;;
            tesseract)        PKGS+=("tesseract" "tesseract-data-eng") ;;
            *)                PKGS+=("$tool") ;;
        esac
    done
    # Deduplicate
    PKGS=($(printf '%s\n' "${PKGS[@]}" | sort -u))

    if command -v pacman &>/dev/null; then
        echo "  Install with: sudo pacman -S ${PKGS[*]}"
    elif command -v apt &>/dev/null; then
        echo "  Install with: sudo apt install ${PKGS[*]}"
    elif command -v dnf &>/dev/null; then
        echo "  Install with: sudo dnf install ${PKGS[*]}"
    else
        echo "  Install these packages with your package manager: ${PKGS[*]}"
    fi
    exit 1
fi
info "All system tools found"

# Check for pipx
if ! command -v pipx &>/dev/null; then
    error "pipx not found."
    if command -v pacman &>/dev/null; then
        echo "  Install with: sudo pacman -S python-pipx"
    elif command -v apt &>/dev/null; then
        echo "  Install with: sudo apt install pipx"
    else
        echo "  Install with: pip install --user pipx"
    fi
    exit 1
fi
info "pipx found"

# Check for claude
if ! command -v claude &>/dev/null; then
    error "claude (Claude Code) not found on PATH."
    echo "  Install from: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi
info "Claude Code found"

# Install the package
echo
echo "Installing hyprland-mcp..."
if pipx list 2>/dev/null | grep -q "hyprland-mcp"; then
    pipx upgrade hyprland-mcp 2>/dev/null || pipx install --force "$REPO"
    info "hyprland-mcp upgraded"
else
    pipx install "$REPO"
    info "hyprland-mcp installed"
fi

# Register with Claude Code
echo
echo "Registering MCP server with Claude Code..."
claude mcp add --transport stdio --scope user hyprland -- hyprland-mcp
info "MCP server registered"

echo
info "Done! Restart Claude Code to use the hyprland tools."
echo "  Verify with: claude mcp list"
