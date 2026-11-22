# ◆ TUXİXİ Terminal

**A simple, customizable terminal emulator for Linux.**

TUXİXİ is a Linux terminal emulator built with Python, GTK4 and VTE.

It provides a clean, modern interface while allowing you to use your system's real shell, such as Bash, Zsh or Fish.

The goal of TUXİXİ is simple: a comfortable, lightweight terminal with its own identity, without getting in the way of your Linux environment.

## ✨ Features

- **Real Shell Support:** Use your system's Bash, Zsh or Fish seamlessly.
- **Minimalist Tab System:** Slim top tab bar with `+` button, hover-to-reveal `×` close buttons, overflow scrolling, and independent tab sessions.
- **Dynamic Tab Titles:** Tabs automatically display your current directory or running program (`1: ~`, `2: Projects`, `3: htop`) with smart `1..N` renumbering.
- **Glass & Blur Modes:** Switch between **Glass Mode** (clean transparency), **Static Blur** (zero-GPU cached desktop wallpaper blur), and **Smoky Blur** (dark matte glass).
- **19 Built-in Themes:** Instantly switch themes with live synchronization across all open windows and tabs.
- **Custom Commands:** Built-in `tuxixi`, `ll`, and `cls` utilities available cleanly inside TUXİXİ's own environment.
- **TrueColor Support:** 24-bit colors for a rich terminal experience.
- **Multiple Windows & Tabs:** Open multiple independent windows or tabs with instant switching.
- **Atomic Configuration:** Safe, validated settings stored in `~/.config/tuxixi/config.json`.
- **System & Network Diagnostics:** View kernel, uptime, CPU load, memory, disk usage, and network/IP status in a clean layout.

## 🛠️ Built With

- Python 3
- GTK4
- VTE (3.91)
- POSIX Shell Scripts

## 📦 Installation

### One-line install (recommended)

Install the latest TUXİXİ release with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/install.sh | bash
```

The installer handles everything for you:

- Detects your distribution and package manager.
- Checks Python 3 and installs it automatically if it is missing.
- Checks GTK4 / VTE / PyGObject runtime dependencies and offers to install them.
- Downloads the latest release archive from GitHub Releases (no manual downloads).
- Extracts and installs TUXİXİ into `~/.local/opt/tuxixi`.
- Configures executable permissions for its commands.
- Installs the application icons (`tuxixi-512.png`).
- Creates the desktop entry (`org.tuxixi.Terminal.desktop`) for your application menu and dock.

No root permissions are required (package installation only asks for `sudo` when something is actually missing).

Prefer to review the script before running it?

```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/Tuxixi-project/TUXIXI-Terminal/main/install.sh
less install.sh
chmod +x install.sh && ./install.sh
```

### Manual install

1. Download `tuxixi_terminal_v2.1.0.tar.gz` and `install.sh` from the project's Releases page.

2. Place `tuxixi_terminal_v2.1.0.tar.gz` next to `install.sh` (or anywhere in your Home directory), open a terminal, and run:

```bash
chmod +x install.sh
./install.sh
```

If a local archive is found next to the installer, it is used directly and nothing is downloaded.

### Requirements

- Linux (X11 or Wayland)
- Python 3
- GTK4
- VTE (GTK4 / 3.91)
- Python GObject Introspection bindings (`PyGObject`)

## ⌨️ TUXİXİ Commands

TUXİXİ includes its own built-in commands:

- `tuxixi --help` – Show available commands and shortcuts
- `tuxixi --system` / `tuxixi --sys` – Display system status (Kernel, Uptime, Load, RAM, Disk)
- `tuxixi --ip` – Display network interface, internal IP and external IP
- `tuxixi --version` – Show TUXİXİ version
- `ll` – List files and directories with human-readable sizes
- `cls` – Clear the terminal screen

These commands are available inside TUXİXİ's own shell environment. They are not globally installed into other terminals.

## 🎨 Themes, Glass & Blur

TUXİXİ includes **19 built-in themes** along with modern visual modes:

- **Cycle Themes:** `Ctrl + Shift + T`
- **Toggle Glass Mode (Transparency):** `Ctrl + Shift + O`
- **Cycle Blur Modes (`Static` / `Smoky` / `Off`):** `Ctrl + Shift + B`

All changes are saved automatically and synchronized live across every open window and tab.

## ⌨️ Keyboard Shortcuts

TUXİXİ includes keyboard shortcuts for everyday terminal operations:

- `Ctrl + Shift + Enter` – New tab
- `Ctrl + Shift + W` – Close active tab
- `Alt + 1..9` / `Ctrl + Tab` – Switch between tabs
- `Ctrl + Shift + C` – Copy
- `Ctrl + Shift + V` – Paste
- `Ctrl + Shift + T` – Change theme
- `Ctrl + Shift + O` – Toggle Glass mode (transparency)
- `Ctrl + Shift + B` – Cycle Blur mode (`Static` / `Smoky` / `Off`)
- `Ctrl + Shift + N` – New window
- `Ctrl + Shift + +` – Zoom in
- `Ctrl + Shift + -` – Zoom out

## 🗑️ Uninstallation

To remove TUXİXİ, run:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

The uninstaller removes the application, desktop entries, and installed icons, and optionally asks if you want to remove `~/.config/tuxixi` without touching your personal shell configuration.

## 🚀 Project Status

TUXİXİ is an actively developed project. New features, performance improvements and bug fixes are part of its ongoing development.

Feedback and bug reports are welcome!

## ❤️ Contributing

Have an idea or found a bug?

Feel free to open an issue or contribute to the project.

Every suggestion and contribution is appreciated.

- **Website:** https://tuxixi-project.github.io
- **Email:** tuxixi_team@proton.me

---

**TUXİXİ Terminal 2.1.0**

*More freedom. More flexibility. More TUXİXİ.* 🐧
