#!/usr/bin/env bash

set -e

# ==========================================
# TUXIXI TERMINAL 2.1.0 UNINSTALLER
# ==========================================

VERSION="2.1.0"
APP_DIR="$HOME/.local/opt/tuxixi"
BIN_DIR="$HOME/.local/bin"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
BASE_ICON_DIR="$USER_DATA_DIR/icons"
ICON_DIR_512="$BASE_ICON_DIR/hicolor/512x512/apps"
ICON_DIR_256="$BASE_ICON_DIR/hicolor/256x256/apps"
DESKTOP_DIR="$USER_DATA_DIR/applications"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tuxixi"

echo ""
echo "  ◆ TUXIXI TERMINAL v${VERSION} UNINSTALLER"
echo "  ────────────────────────────────────"
echo ""

# 1. Confirm removal
read -r -p "▸ Are you sure you want to uninstall TUXIXI? [y/N]: " ANSWER

if [[ ! "$ANSWER" =~ ^[Yy]$ ]]; then
    echo ""
    echo "✗ Uninstallation cancelled."
    exit 0
fi

echo ""

# 2. Remove application
echo "▸ Removing application..."

if [[ -d "$APP_DIR" ]]; then
    rm -rf -- "$APP_DIR"
    echo "✓ Application removed."
else
    echo "• Application directory not found."
fi

# 3. Remove CLI command
echo "▸ Removing CLI command..."

if [[ -e "$BIN_DIR/tuxixi" || -L "$BIN_DIR/tuxixi" ]]; then
    rm -f -- "$BIN_DIR/tuxixi"
    echo "✓ CLI command removed."
else
    echo "• CLI command not found."
fi

# 4. Remove desktop entries
echo "▸ Removing desktop entries..."

REMOVED_DESKTOP=0
for df in "tuxixi.desktop" "org.tuxixi.Terminal.desktop"; do
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

# 5. Remove icons
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

# 6. Optionally remove configuration
if [[ -d "$CONFIG_DIR" ]]; then
    echo ""
    read -r -p "▸ Also remove TUXIXI settings ($CONFIG_DIR)? [y/N]: " REMOVE_CFG
    if [[ "$REMOVE_CFG" =~ ^[Yy]$ ]]; then
        rm -rf -- "$CONFIG_DIR"
        echo "✓ Configuration removed."
    else
        echo "• Configuration kept."
    fi
fi

# 7. Refresh desktop & icon caches silently
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1 && [[ -d "$BASE_ICON_DIR/hicolor" ]]; then
    gtk-update-icon-cache -f -t "$BASE_ICON_DIR/hicolor" 2>/dev/null || true
fi

# 8. Finish
echo ""
echo "  ────────────────────────────────────"
echo "  ◆ TUXIXI v${VERSION} UNINSTALLED!"
echo "  ────────────────────────────────────"
echo ""
echo "  TUXIXI has been removed from your system."
echo ""
echo "  Your personal shell configuration"
echo "  and other files were not touched."
echo ""
echo "  Thank you for using TUXIXI! <3"
echo ""
