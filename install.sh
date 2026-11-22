#!/usr/bin/env bash

set -euo pipefail

# ==========================================================
# TUXIXI TERMINAL INSTALLER (one-line edition)
#
# Install TUXIXI with a single command, no manual downloads:
#
#   curl -fsSL https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/install.sh | bash
#
# The installer will:
#   1. Detect your distribution and package manager
#   2. Check Python 3 & GTK4 / VTE / PyGObject dependencies
#      (asks permission before installing any missing packages)
#   3. Download the latest release archive from GitHub Releases
#   4. Install into ~/.local/opt/tuxixi (no root required)
#   5. Create icons and the desktop entry
# ==========================================================

REPO="Tuxixi-project/TUXIXI-Terminal"
GH_URL="https://github.com/${REPO}"

APP_NAME="TUXIXI Terminal"
ARCHIVE_NAME=""
TMP_DL=""
TMP_DIR=""
APP_VERSION=""

APP_DIR="$HOME/.local/opt/tuxixi"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
BASE_ICON_DIR="$USER_DATA_DIR/icons"
ICON_DIR="$BASE_ICON_DIR/hicolor/512x512/apps"
DESKTOP_DIR="$USER_DATA_DIR/applications"

cleanup() {
    [[ -n "${TMP_DIR:-}" ]] && rm -rf -- "$TMP_DIR"
    [[ -n "${TMP_DL:-}" ]] && rm -rf -- "$TMP_DL"
}
trap cleanup EXIT

echo ""
echo "  ◆ TUXIXI TERMINAL INSTALLER"
echo "  ──────────────────────────────────"
echo ""

# ----------------------------------------------------------
# 0. Helpers
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

ask_install() {
    local question="$1" answer=""
    if ! can_ask_user; then
        return 1
    fi
    printf "%s [y/N]: " "$question" > /dev/tty
    read -r answer < /dev/tty || return 1
    [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]
}

# ----------------------------------------------------------
# 1. Detect distribution and package manager
# ----------------------------------------------------------

DISTRO_NAME="Unknown Linux"
PKG_MGR=""

if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_NAME="${NAME:-Unknown Linux}"
fi

if need_cmd apt-get; then
    PKG_MGR="apt"
elif need_cmd dnf; then
    PKG_MGR="dnf"
elif need_cmd yum; then
    PKG_MGR="yum"
elif need_cmd pacman; then
    PKG_MGR="pacman"
elif need_cmd zypper; then
    PKG_MGR="zypper"
elif need_cmd apk; then
    PKG_MGR="apk"
fi

echo "▸ Detecting distribution..."
echo "• Detected : $DISTRO_NAME"
if [[ -n "$PKG_MGR" ]]; then
    echo "• Packaging: $PKG_MGR"
else
    echo "• Packaging: unknown (dependency auto-install disabled)"
fi
echo ""

# ----------------------------------------------------------
# 2. Privilege helper for package installation
# ----------------------------------------------------------

run_as_root() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    elif need_cmd sudo; then
        sudo "$@"
    elif need_cmd doas; then
        doas "$@"
    else
        return 2
    fi
}

install_pkgs() {
    local pkgs="$1"
    case "$PKG_MGR" in
        apt)
            run_as_root env DEBIAN_FRONTEND=noninteractive apt-get update -y || true
            run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y $pkgs
            ;;
        dnf|yum)
            run_as_root "$PKG_MGR" install -y $pkgs
            ;;
        pacman)
            run_as_root pacman -S --needed --noconfirm $pkgs
            ;;
        zypper)
            run_as_root zypper install -y $pkgs
            ;;
        apk)
            run_as_root apk add $pkgs
            ;;
        *)
            return 3
            ;;
    esac
}

# ----------------------------------------------------------
# 3. Check all runtime dependencies (Python 3, GTK4, VTE, PyGObject)
#    Never installs system packages without asking the user first.
# ----------------------------------------------------------

echo "▸ Checking runtime dependencies..."

HAS_PYTHON=0
HAS_GTK_VTE=0
MISSING_LABELS=()

if need_cmd python3; then
    HAS_PYTHON=1
    echo "✓ Python 3 found: $(python3 --version 2>&1)"
    if python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Gdk','4.0'); gi.require_version('Vte','3.91'); from gi.repository import Gtk, Gdk, Vte" >/dev/null 2>&1; then
        HAS_GTK_VTE=1
        echo "✓ GTK4 / VTE 3.91 / PyGObject are available."
    else
        MISSING_LABELS+=("GTK4 / VTE 3.91 / PyGObject")
        echo "✗ GTK4 / VTE 3.91 / PyGObject not detected."
    fi
else
    MISSING_LABELS+=("Python 3" "GTK4 / VTE 3.91 / PyGObject")
    echo "✗ Python 3 not detected."
fi

DEPS_OK=1
if [[ "$HAS_PYTHON" -ne 1 || "$HAS_GTK_VTE" -ne 1 ]]; then
    DEPS_OK=0
fi

dep_hint() {
    echo ""
    echo "  TUXIXI requires Python 3, GTK4, VTE 3.91 and PyGObject. On your system, run:"
    case "$PKG_MGR" in
        apt)
            echo "    sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-vte-3.91"
            ;;
        dnf|yum)
            echo "    sudo $PKG_MGR install python3 python3-gobject gtk4 vte291-gtk4"
            ;;
        pacman)
            echo "    sudo pacman -S python python-gobject gtk4 vte4"
            ;;
        zypper)
            echo "    sudo zypper install python3 python3-gobject gtk4"
            echo "    (plus the VTE GTK4 typelib package for your openSUSE version)"
            ;;
        apk)
            echo "    sudo apk add python3 py3-gobject3"
            echo "    (plus GTK4 and VTE packages for your Alpine version)"
            ;;
        *)
            echo "    Install Python 3, GTK4, VTE 3.91 and PyGObject using your package manager."
            ;;
    esac
    echo ""
}

if [[ "$DEPS_OK" -eq 0 ]]; then
    MISSING_STR="$(IFS=', '; echo "${MISSING_LABELS[*]}")"
    echo ""

    if [[ -n "$PKG_MGR" ]] && ask_install "▸ Some required dependencies are missing (${MISSING_STR}). Would you like to install them now?"; then
        dep_pkgs=""
        case "$PKG_MGR" in
            apt)
                [[ "$HAS_PYTHON" -eq 0 ]] && dep_pkgs+="python3 "
                [[ "$HAS_GTK_VTE" -eq 0 ]] && dep_pkgs+="python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-vte-3.91"
                ;;
            dnf|yum)
                [[ "$HAS_PYTHON" -eq 0 ]] && dep_pkgs+="python3 "
                [[ "$HAS_GTK_VTE" -eq 0 ]] && dep_pkgs+="python3-gobject gtk4 vte291-gtk4"
                ;;
            pacman)
                [[ "$HAS_PYTHON" -eq 0 ]] && dep_pkgs+="python "
                [[ "$HAS_GTK_VTE" -eq 0 ]] && dep_pkgs+="python-gobject gtk4 vte4"
                ;;
        esac

        if [[ -n "$dep_pkgs" ]] && install_pkgs "$dep_pkgs"; then
            echo "✓ Missing dependencies installed."
            DEPS_OK=1
        else
            echo "✗ Automatic installation failed or is unsupported on this distro."
            dep_hint
        fi
    else
        dep_hint
        echo "  (Continuing installation: TUXIXI will be installed, but it will not"
        echo "   launch until these dependencies are installed.)"
        echo ""
    fi
fi

# ----------------------------------------------------------
# 4. Get the archive: reuse newest local copy if present,
#    otherwise download the latest release from GitHub Releases
# ----------------------------------------------------------

echo "▸ Locating $APP_NAME archive..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
ARCHIVE=""

LOCAL_ARCHIVE=$(ls -1v ./tuxixi_terminal_v*.tar.gz 2>/dev/null | tail -1 || true)
if [[ -z "$LOCAL_ARCHIVE" && -n "$SCRIPT_DIR" ]]; then
    LOCAL_ARCHIVE=$(ls -1v "$SCRIPT_DIR"/tuxixi_terminal_v*.tar.gz 2>/dev/null | tail -1 || true)
fi
if [[ -n "$LOCAL_ARCHIVE" ]]; then
    ARCHIVE="$LOCAL_ARCHIVE"
    echo "✓ Using local archive: $ARCHIVE"
fi

if [[ -z "$ARCHIVE" ]]; then
    echo "• Resolving latest GitHub release..."

    if ! need_cmd curl; then
        echo "✗ curl is required to download TUXIXI. Install curl and re-run."
        exit 1
    fi

    TAG=""
    ARCHIVE_URL=""
    LATEST_URL="$(curl -fsSL -o /dev/null -w '%{url_effective}' "$GH_URL/releases/latest" 2>/dev/null || true)"
    TAG="${LATEST_URL##*/}"

    if [[ "$TAG" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        APP_VERSION="${TAG#v}"
        ARCHIVE_NAME="tuxixi_terminal_v${APP_VERSION}.tar.gz"
        ARCHIVE_URL="$GH_URL/releases/download/${TAG}/${ARCHIVE_NAME}"
        if ! curl -fsSL --range 0-0 -o /dev/null "$ARCHIVE_URL" 2>/dev/null; then
            ARCHIVE_URL=""
        fi
    fi

    if [[ -z "$ARCHIVE_URL" ]]; then
        ARCHIVE_URL="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
            | grep -o '"browser_download_url": *"[^"]*\.tar\.gz"' | head -1 | cut -d'"' -f4 || true)"
    fi

    if [[ -z "$ARCHIVE_URL" ]]; then
        echo "✗ Could not resolve the latest TUXIXI release archive."
        echo "  Check https://github.com/${REPO}/releases"
        exit 1
    fi

    if [[ -z "$APP_VERSION" ]]; then
        APP_VERSION="$(basename "$ARCHIVE_URL" | sed -E 's/^.*_v([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz$/\1/')"
    fi

    TMP_DL="$(mktemp -d)"

    echo "• Downloading $(basename "$ARCHIVE_URL") ..."
    curl -fSL --retry 3 -o "$TMP_DL/$(basename "$ARCHIVE_URL")" "$ARCHIVE_URL"

    ARCHIVE="$TMP_DL/$(basename "$ARCHIVE_URL")"
    echo "✓ Downloaded: $(basename "$ARCHIVE_URL")"
fi

if [[ -z "$APP_VERSION" ]]; then
    APP_VERSION="$(basename "$ARCHIVE" | sed -E 's/^.*_v([0-9]+\.[0-9]+\.[0-9]+)\.tar\.gz$/\1/')"
fi
if [[ ! "$APP_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    APP_VERSION="latest"
fi

# ----------------------------------------------------------
# 5. Validate archive
# ----------------------------------------------------------

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

# ----------------------------------------------------------
# 6. Extract and locate project files
# ----------------------------------------------------------

echo "▸ Extracting archive..."

TMP_DIR="$(mktemp -d)"
tar -xzf "$ARCHIVE" -C "$TMP_DIR"

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

# ----------------------------------------------------------
# 7. Install application
# ----------------------------------------------------------

echo ""
echo "▸ Installing TUXIXI..."

mkdir -p "$(dirname "$APP_DIR")"
rm -rf -- "$APP_DIR"
mkdir -p "$APP_DIR"

cp -a "$PROJECT_DIR/." "$APP_DIR/"

echo "✓ Application installed!"

echo "▸ Setting executable permissions..."
chmod 755 "$APP_DIR" "$APP_DIR/bin"
chmod 755 "$APP_DIR/main.py" "$APP_DIR/bin/"*
echo "✓ Permissions configured!"

# ----------------------------------------------------------
# 8. Remove old global CLI launcher (if any)
# ----------------------------------------------------------

echo "▸ Cleaning old global CLI launcher..."

if [[ -e "$HOME/.local/bin/tuxixi" || -L "$HOME/.local/bin/tuxixi" ]]; then
    rm -f -- "$HOME/.local/bin/tuxixi"
    echo "✓ Old global launcher removed!"
else
    echo "• No old global launcher found."
fi

# ----------------------------------------------------------
# 9. Install icons
# ----------------------------------------------------------

echo "▸ Installing TUXIXI icon..."

mkdir -p "$BASE_ICON_DIR" "$ICON_DIR"

for icon_name in "tuxixi.png" "tuxixi-512.png" "org.tuxixi.Terminal.png"; do
    cp -f "$APP_DIR/tuxixi-512.png" "$ICON_DIR/$icon_name"
    cp -f "$APP_DIR/tuxixi-512.png" "$BASE_ICON_DIR/$icon_name"
done

echo "✓ Icon installed!"

# ----------------------------------------------------------
# 10. Create desktop entry
# ----------------------------------------------------------

echo "▸ Creating desktop entry..."

mkdir -p "$DESKTOP_DIR"
rm -f -- "$DESKTOP_DIR/tuxixi.desktop"

cat > "$DESKTOP_DIR/org.tuxixi.Terminal.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=TUXIXI Terminal
Comment=TUXIXI Terminal Emulator v${APP_VERSION}
Exec=python3 "$APP_DIR/main.py"
Icon=$ICON_DIR/tuxixi-512.png
Terminal=false
Categories=System;TerminalEmulator;
StartupNotify=true
StartupWMClass=org.tuxixi.Terminal
EOF

chmod 644 "$DESKTOP_DIR/org.tuxixi.Terminal.desktop"

if need_cmd update-desktop-database; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if need_cmd gtk-update-icon-cache && [[ -d "$BASE_ICON_DIR/hicolor" ]]; then
    gtk-update-icon-cache -f -t "$BASE_ICON_DIR/hicolor" 2>/dev/null || true
fi

echo "✓ Desktop entry created!"

# ----------------------------------------------------------
# 11. Finish
# ----------------------------------------------------------

echo ""
echo "  ──────────────────────────────────"
echo "  ◆ TUXIXI v${APP_VERSION} INSTALLED!"
echo "  ──────────────────────────────────"
echo ""
echo "  Distribution: $DISTRO_NAME"
echo "  Application : $APP_DIR"
echo "  Desktop     : $DESKTOP_DIR/org.tuxixi.Terminal.desktop"
echo "  Icon        : $ICON_DIR/tuxixi-512.png"
echo ""
echo "  Launch TUXIXI from your application menu."
echo ""
echo "  TUXIXI commands (tuxixi --help) are available"
echo "  only inside TUXIXI Terminal."
echo ""

if [[ "$DEPS_OK" -ne 1 ]]; then
    dep_hint
fi

echo "  Thank you for using TUXIXI! <3"
echo ""
