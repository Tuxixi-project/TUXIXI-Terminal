#!/usr/bin/env bash

set -euo pipefail

# ==========================================================
# TUXIXI TERMINAL UNINSTALLER (one-line edition)
#
# Uninstall TUXIXI with a single command:
#
#   curl -fsSL https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/uninstall.sh | bash
#
# The uninstaller will:
#   1. Ask for confirmation (works even when piped via curl | bash)
#   2. Remove ~/.local/opt/tuxixi
#   3. Remove CLI launchers, desktop entries and icons
#   4. Optionally remove ~/.config/tuxixi settings
#   5. Refresh desktop and icon caches
# ==========================================================

APP_DIR="$HOME/.local/opt/tuxixi"
BIN_DIR="$HOME/.local/bin"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
BASE_ICON_DIR="$USER_DATA_DIR/icons"
ICON_DIR_512="$BASE_ICON_DIR/hicolor/512x512/apps"
ICON_DIR_256="$BASE_ICON_DIR/hicolor/256x256/apps"
DESKTOP_DIR="$USER_DATA_DIR/applications"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tuxixi"

AUTO_YES=0
for arg in "$@"; do
    case "$arg" in
        -y|--yes) AUTO_YES=1 ;;
    esac
done

echo ""
echo "  ◆ TUXIXI TERMINAL UNINSTALLER"
echo "  ──────────────────────────────────"
echo ""

# ----------------------------------------------------------
# 0. Helpers (supports interactive prompts in curl | bash)
# ----------------------------------------------------------

need_cmd() {
    command -v "$1" >/dev/null 2>&1
}

can_ask_user() {
    if [[ -t 2 ]]; then
        return 0
    fi
    if printf '' > /dev/tty 2>/dev/null; then
        return 0
    fi
    return 1
}

ask_confirm() {
    local question="$1" answer=""
    if [[ "$AUTO_YES" -eq 1 ]]; then
        return 0
    fi
    if ! can_ask_user; then
        return 1
    fi
    printf "%s [y/N]: " "$question" > /dev/tty
    read -r answer < /dev/tty || return 1
    [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]
}

# ----------------------------------------------------------
# 1. Confirm removal
# ----------------------------------------------------------

if ! ask_confirm "▸ Are you sure you want to uninstall TUXIXI?"; then
    echo ""
    echo "✗ Uninstallation cancelled."
    exit 0
fi

echo ""

# ----------------------------------------------------------
# 2. Remove application
# ----------------------------------------------------------

echo "▸ Removing application..."

if [[ -d "$APP_DIR" ]]; then
    rm -rf -- "$APP_DIR"
    echo "✓ Application removed."
else
    echo "• Application directory not found."
fi

# ----------------------------------------------------------
# 3. Remove CLI command (if any)
# ----------------------------------------------------------

echo "▸ Removing CLI command..."

if [[ -e "$BIN_DIR/tuxixi" || -L "$BIN_DIR/tuxixi" ]]; then
    rm -f -- "$BIN_DIR/tuxixi"
    echo "✓ CLI command removed."
else
    echo "• CLI command not found."
fi

# ----------------------------------------------------------
# 4. Remove desktop entries
# ----------------------------------------------------------

echo "▸ Removing desktop entries..."

REMOVED_DESKTOP=0
for df in "org.tuxixi.Terminal.desktop" "tuxixi.desktop"; do
    if [[ -f "$DESKTOP_DIR/$df" || -L "$DESKTOP_DIR/$df" ]]; then
        rm -f -- "$DESKTOP_DIR/$df"
        REMOVED_DESKTOP=1
    fi
done

if [[ "$REMOVED_DESKTOP" -eq 1 ]]; then
    echo "✓ Desktop entries removed."
else
    echo "• Desktop entries not found."
fi

# ----------------------------------------------------------
# 5. Remove icons
# ----------------------------------------------------------

echo "▸ Removing icons..."

REMOVED_ICON=0
for dir in "$BASE_ICON_DIR" "$ICON_DIR_512" "$ICON_DIR_256"; do
    for icon in "tuxixi.png" "tuxixi-512.png" "org.tuxixi.Terminal.png"; do
        if [[ -f "$dir/$icon" || -L "$dir/$icon" ]]; then
            rm -f -- "$dir/$icon"
            REMOVED_ICON=1
        fi
    done
done

if [[ "$REMOVED_ICON" -eq 1 ]]; then
    echo "✓ Icons removed."
else
    echo "• Icons not found."
fi

# ----------------------------------------------------------
# 6. Optionally remove configuration
# ----------------------------------------------------------

if [[ -d "$CONFIG_DIR" ]]; then
    echo ""
    if ask_confirm "▸ Also remove TUXIXI settings ($CONFIG_DIR)?"; then
        rm -rf -- "$CONFIG_DIR"
        echo "✓ Configuration removed."
    else
        echo "• Configuration kept."
    fi
fi

# ----------------------------------------------------------
# 7. Refresh desktop & icon caches
# ----------------------------------------------------------

if need_cmd update-desktop-database; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if need_cmd gtk-update-icon-cache && [[ -d "$BASE_ICON_DIR/hicolor" ]]; then
    gtk-update-icon-cache -f -t "$BASE_ICON_DIR/hicolor" 2>/dev/null || true
fi

# ----------------------------------------------------------
# 8. Finish
# ----------------------------------------------------------

echo ""
echo "  ──────────────────────────────────"
echo "  ◆ TUXIXI UNINSTALLED!"
echo "  ──────────────────────────────────"
echo ""
echo "  TUXIXI has been removed from your system."
echo ""
echo "  Your personal shell configuration"
echo "  and other files were not touched."
echo ""
echo "  Thank you for using TUXIXI! <3"
echo ""
