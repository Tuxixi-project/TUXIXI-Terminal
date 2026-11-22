# TUXIXI Terminal

A lightweight, customizable Linux terminal emulator built with Python 3, GTK4, and VTE.

![Python](https://img.shields.io/badge/Python-3-3776AB)
![GTK4](https://img.shields.io/badge/GTK4-VTE%203.91-007ec6)
![Platform](https://img.shields.io/badge/Platform-Linux-4c1)
![License](https://img.shields.io/badge/License-GPL--3.0-dfb317)
![Version](https://img.shields.io/badge/Version-2.1.0-7c3aed)

## Features

- Works with your real system shell (Bash, Zsh, Fish)
- Minimalist top tab bar with dynamic titles, hover close button, and overflow scrolling
- Glass transparency mode and dual Blur modes (Static wallpaper blur & Smoky matte)
- 19 built-in themes with live multi-window synchronization
- Built-in utilities (`tuxixi`, `ll`, `cls`) isolated to TUXIXI sessions
- X11 and Wayland support

## Installation

### Quick Install (One-Line)

```bash
curl -fsSL https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/install.sh | bash
```

### Manual / Offline Install

1. Download `tuxixi_terminal_v2.1.0.tar.gz` and `install.sh` from the Releases page into the same folder.
2. Open a terminal in that folder and run:

```bash
chmod +x install.sh
./install.sh
```

The installer detects your distro, checks dependencies (Python 3, GTK4, VTE 3.91, PyGObject), asks before installing any missing packages, and installs TUXIXI into `~/.local/opt/tuxixi`.

## Commands

Available inside TUXIXI Terminal:

- `tuxixi --help` – Show help and shortcuts
- `tuxixi --system` / `tuxixi --sys` – System status
- `tuxixi --ip` – Network and IP info
- `tuxixi --version` – Version info
- `ll` – Human-readable directory listing
- `cls` – Clear terminal

## Shortcuts

- `Ctrl + Shift + Enter` – New tab
- `Ctrl + Shift + W` – Close tab
- `Alt + 1..9` / `Ctrl + Tab` – Switch tabs
- `Ctrl + Shift + O` – Glass mode (transparency)
- `Ctrl + Shift + B` – Blur mode (Static / Smoky / Off)
- `Ctrl + Shift + T` – Change theme
- `Ctrl + Shift + N` – New window
- `Ctrl + Shift + +` / `-` – Font size
- `Ctrl + Shift + C` / `V` – Copy / Paste

## Uninstallation

One-line uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/uninstall.sh | bash
```

Or run `uninstall.sh` locally:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

Removes TUXIXI files, desktop entries, and icons without touching system packages or your shell configuration.

## Links

- Website: https://tuxixi-project.github.io
- Email: tuxixi_team@proton.me

---

**TUXIXI Terminal 2.1.0** — *More freedom. More flexibility. More TUXIXI.*
