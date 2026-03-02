#!/usr/bin/env bash
set -euo pipefail

# hyprland-mcp installer
# Usage: curl -sSL https://raw.githubusercontent.com/alderban107/hyprland-mcp/main/install.sh | bash

REPO="https://github.com/alderban107/hyprland-mcp.git"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

echo -e "${BOLD}hyprland-mcp installer${NC}"
echo "======================"
echo

# ── Detect package manager ─────────────────────────────────────────────

PM=""
PM_INSTALL=""
if command -v pacman &>/dev/null; then
    PM="pacman"
    PM_INSTALL="sudo pacman -S --needed --noconfirm"
elif command -v apt-get &>/dev/null; then
    PM="apt"
    PM_INSTALL="sudo apt-get install -y"
elif command -v dnf &>/dev/null; then
    PM="dnf"
    PM_INSTALL="sudo dnf install -y"
elif command -v zypper &>/dev/null; then
    PM="zypper"
    PM_INSTALL="sudo zypper install -y"
elif command -v xbps-install &>/dev/null; then
    PM="xbps"
    PM_INSTALL="sudo xbps-install -y"
elif command -v emerge &>/dev/null; then
    PM="emerge"
    PM_INSTALL="sudo emerge --ask --noreplace"
elif command -v nix-env &>/dev/null; then
    PM="nix"
fi

# Map a tool name to the correct package name for the detected package manager
pkg_name() {
    local tool="$1"
    case "$tool" in
        wl-copy|wl-paste)
            case "$PM" in
                emerge) echo "gui-apps/wl-clipboard" ;;
                *)      echo "wl-clipboard" ;;
            esac
            ;;
        tesseract)
            case "$PM" in
                apt)     echo "tesseract-ocr tesseract-ocr-eng" ;;
                emerge)  echo "app-text/tesseract" ;;
                *)       echo "tesseract tesseract-data-eng" ;;
            esac
            ;;
        grim)
            case "$PM" in
                emerge) echo "gui-apps/grim" ;;
                *)      echo "grim" ;;
            esac
            ;;
        wtype)
            case "$PM" in
                emerge) echo "gui-apps/wtype" ;;
                *)      echo "wtype" ;;
            esac
            ;;
        ydotool)
            case "$PM" in
                emerge) echo "gui-apps/ydotool" ;;
                *)      echo "ydotool" ;;
            esac
            ;;
        *)
            echo "$tool"
            ;;
    esac
}

# ── Check for Hyprland ─────────────────────────────────────────────────

if ! command -v hyprctl &>/dev/null; then
    error "hyprctl not found — this MCP server requires Hyprland."
    exit 1
fi
info "Hyprland detected"

# ── Check system dependencies ──────────────────────────────────────────

MISSING_TOOLS=()
for tool in grim wtype ydotool wl-copy wl-paste tesseract; do
    if ! command -v "$tool" &>/dev/null; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    warn "Missing system tools: ${MISSING_TOOLS[*]}"

    # Build package list
    PKGS=()
    for tool in "${MISSING_TOOLS[@]}"; do
        for pkg in $(pkg_name "$tool"); do
            PKGS+=("$pkg")
        done
    done
    # Deduplicate
    PKGS=($(printf '%s\n' "${PKGS[@]}" | sort -u))

    if [ "$PM" = "nix" ]; then
        echo
        echo "  Add these to your configuration.nix environment.systemPackages:"
        echo "    ${PKGS[*]}"
        echo "  Then run: sudo nixos-rebuild switch"
        echo
        echo "  Or install imperatively:"
        echo "    nix profile install ${PKGS[*]/#/nixpkgs#}"
        echo
        echo "  Re-run this installer after installing the dependencies."
        exit 1
    elif [ -n "$PM_INSTALL" ]; then
        echo
        read -rp "  Install them now with $PM? [Y/n] " response
        response="${response:-y}"
        if [[ "$response" =~ ^[Yy]$ ]]; then
            $PM_INSTALL "${PKGS[@]}"
            info "System dependencies installed"
        else
            echo "  Install manually: $PM_INSTALL ${PKGS[*]}"
            exit 1
        fi
    else
        echo "  Install these packages with your package manager: ${PKGS[*]}"
        echo "  Re-run this installer after installing the dependencies."
        exit 1
    fi
fi
info "All system tools found"

# ── Check for pipx ─────────────────────────────────────────────────────

if ! command -v pipx &>/dev/null; then
    warn "pipx not found"

    PIPX_PKG="pipx"
    case "$PM" in
        pacman)  PIPX_PKG="python-pipx" ;;
        apt)     PIPX_PKG="pipx" ;;
        dnf)     PIPX_PKG="pipx" ;;
        zypper)  PIPX_PKG="python3-pipx" ;;
        xbps)    PIPX_PKG="pipx" ;;
        emerge)  PIPX_PKG="dev-python/pipx" ;;
    esac

    if [ "$PM" = "nix" ]; then
        echo "  Add pipx to your configuration, or: nix profile install nixpkgs#pipx"
        exit 1
    elif [ -n "$PM_INSTALL" ]; then
        read -rp "  Install pipx with $PM? [Y/n] " response
        response="${response:-y}"
        if [[ "$response" =~ ^[Yy]$ ]]; then
            $PM_INSTALL "$PIPX_PKG"
            # Ensure pipx bin dir is on PATH for this script
            export PATH="$HOME/.local/bin:$PATH"
            info "pipx installed"
        else
            echo "  Install manually: $PM_INSTALL $PIPX_PKG"
            exit 1
        fi
    else
        echo "  Install pipx with your package manager or: pip install --user pipx"
        exit 1
    fi
fi
info "pipx found"

# ── Check for Claude Code ─────────────────────────────────────────────

if ! command -v claude &>/dev/null; then
    error "Claude Code not found on PATH."
    echo "  Install from: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi
info "Claude Code found"

# ── Install the package ────────────────────────────────────────────────

echo
echo "Installing hyprland-mcp..."
if pipx list 2>/dev/null | grep -q "hyprland-mcp"; then
    pipx upgrade hyprland-mcp 2>/dev/null || pipx install --force "$REPO"
    info "hyprland-mcp upgraded"
else
    pipx install "$REPO"
    info "hyprland-mcp installed"
fi

# ── Register with Claude Code ─────────────────────────────────────────

echo
echo "Registering MCP server with Claude Code..."
claude mcp add --transport stdio --scope user hyprland -- hyprland-mcp
info "MCP server registered"

echo
info "Done! Restart Claude Code to use the hyprland tools."
echo "  Verify with: claude mcp list"
