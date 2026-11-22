#!/usr/bin/env bash

set -e

# ==========================================
# TUXIXI TERMINAL 2.1.0 INSTALLER
# ==========================================

VERSION="2.1.0"
APP_NAME="TUXIXI Terminal"
ARCHIVE_NAME="tuxixi_terminal_v2.1.0.tar.gz"

APP_DIR="$HOME/.local/opt/tuxixi"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
BASE_ICON_DIR="$USER_DATA_DIR/icons"
ICON_DIR="$BASE_ICON_DIR/hicolor/512x512/apps"
DESKTOP_DIR="$USER_DATA_DIR/applications"

echo ""
echo "  ◆ TUXIXI TERMINAL v${VERSION} INSTALLER"
echo "  ──────────────────────────────────"
echo ""

# 1. Find archive (check current/script dir first, then $HOME excluding Trash)
echo "▸ Searching for $ARCHIVE_NAME..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE=""

if [[ -f "./$ARCHIVE_NAME" ]]; then
    ARCHIVE="$(pwd)/$ARCHIVE_NAME"
elif [[ -f "$SCRIPT_DIR/$ARCHIVE_NAME" ]]; then
    ARCHIVE="$SCRIPT_DIR/$ARCHIVE_NAME"
else
    ARCHIVE=$(find "$HOME" \
        -path "$HOME/.local/share/Trash" -prune -o \
        -type f -name "$ARCHIVE_NAME" \
        -print -quit 2>/dev/null || true)
fi

if [[ -z "$ARCHIVE" ]]; then
    echo "✗ Archive not found!"
    echo "  Please place $ARCHIVE_NAME in your Home directory or next to install.sh."
    exit 1
fi

echo "✓ Archive found: $ARCHIVE"

# 2. Validate archive
echo ""
echo "▸ Checking archive..."

if ! tar -tzf "$ARCHIVE" >/dev/null 2>&1; then
    echo "✗ Invalid archive!"
    exit 1
fi

if tar -tzf "$ARCHIVE" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    echo "✗ Unsafe archive paths detected!"
    exit 1
fi

# 3. Extract archive
echo "▸ Extracting archive..."

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

tar -xzf "$ARCHIVE" -C "$TMP_DIR"

# 4. Locate project automatically (works regardless of top-level folder name)
echo "▸ Locating TUXIXI files..."

MAIN_PY=$(find "$TMP_DIR" -maxdepth 3 -type f -name "main.py" -print -quit)

if [[ -z "$MAIN_PY" ]]; then
    echo "✗ main.py not found in archive!"
    exit 1
fi

PROJECT_DIR="$(dirname "$MAIN_PY")"

for req_file in "main.py" "ui.py" "terminal.py" "settings.py" "themes.py" "tuxixi-512.png" "bin/tuxixi"; do
    if [[ ! -f "$PROJECT_DIR/$req_file" ]]; then
        echo "✗ Required file not found: $req_file"
        exit 1
    fi
done

# 5. Install application
echo ""
echo "▸ Installing TUXIXI..."

mkdir -p "$(dirname "$APP_DIR")"
rm -rf -- "$APP_DIR"
mkdir -p "$APP_DIR"

cp -a "$PROJECT_DIR/." "$APP_DIR/"

echo "✓ Application installed!"

# 6. Set permissions
echo "▸ Setting executable permissions..."

chmod 755 "$APP_DIR" "$APP_DIR/bin"
chmod 755 "$APP_DIR/main.py" "$APP_DIR/bin/"*

echo "✓ Permissions configured!"

# 7. Remove old global CLI launcher (if any)
echo "▸ Cleaning old global CLI launcher..."

if [[ -e "$HOME/.local/bin/tuxixi" || -L "$HOME/.local/bin/tuxixi" ]]; then
    rm -f -- "$HOME/.local/bin/tuxixi"
    echo "✓ Old global launcher removed!"
else
    echo "• No old global launcher found."
fi

# 8. Install icons (matching GTK 4 application_id & Dock)
echo "▸ Installing TUXIXI icon..."

mkdir -p "$BASE_ICON_DIR" "$ICON_DIR"

for icon_name in "tuxixi.png" "tuxixi-512.png" "org.tuxixi.Terminal.png"; do
    cp -f "$APP_DIR/tuxixi-512.png" "$ICON_DIR/$icon_name"
    cp -f "$APP_DIR/tuxixi-512.png" "$BASE_ICON_DIR/$icon_name"
done

echo "✓ Icon installed!"

# 9. Create desktop entry (matching org.tuxixi.Terminal for Wayland & X11 Docks)
echo "▸ Creating desktop entry..."

mkdir -p "$DESKTOP_DIR"
rm -f -- "$DESKTOP_DIR/tuxixi.desktop"

cat > "$DESKTOP_DIR/org.tuxixi.Terminal.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=TUXIXI Terminal
Comment=TUXIXI Terminal Emulator v${VERSION}
Exec=python3 "$APP_DIR/main.py"
Icon=$ICON_DIR/tuxixi-512.png
Terminal=false
Categories=System;TerminalEmulator;
StartupNotify=true
StartupWMClass=org.tuxixi.Terminal
EOF

chmod 644 "$DESKTOP_DIR/org.tuxixi.Terminal.desktop"

# Refresh desktop & icon caches silently
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1 && [[ -d "$BASE_ICON_DIR/hicolor" ]]; then
    gtk-update-icon-cache -f -t "$BASE_ICON_DIR/hicolor" 2>/dev/null || true
fi

echo "✓ Desktop entry created!"

# 10. Finish
echo ""
echo "  ──────────────────────────────────"
echo "  ◆ TUXIXI v${VERSION} INSTALLED!"
echo "  ──────────────────────────────────"
echo ""
echo "  Application : $APP_DIR"
echo "  Desktop     : $DESKTOP_DIR/org.tuxixi.Terminal.desktop"
echo "  Icon        : $ICON_DIR/tuxixi-512.png"
echo ""
echo "  Launch TUXIXI from your application menu."
echo ""
echo "  TUXIXI commands (tuxixi --help) are available"
echo "  only inside TUXIXI Terminal."
echo ""
echo "  Thank you for using TUXIXI! <3"
echo ""
