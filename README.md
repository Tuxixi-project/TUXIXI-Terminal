# TUXIXI Terminal

**TUXIXI Terminal is a GTK4-based terminal emulator for Linux, built with Python, PyGObject, and VTE.** It provides a graphical terminal window, a custom prompt and shell interface, configurable color themes, font-size controls, and a small set of built-in command aliases.

> **Project status:** This README describes the features implemented in the current source code. TUXIXI's shell interface is custom, but ordinary system commands are executed through Bash; TUXIXI is not a replacement shell implementation.

## Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Ubuntu and Debian-based distributions](#ubuntu-and-debian-based-distributions)
  - [Arch Linux](#arch-linux)
  - [Other distributions](#other-distributions)
- [Run TUXIXI](#run-tuxixi)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Built-in commands](#built-in-commands)
- [Shell behavior](#shell-behavior)
- [Settings and configuration](#settings-and-configuration)
- [Color themes](#color-themes)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## Overview

TUXIXI Terminal is a Linux desktop application written in Python. GTK4 provides the application window and interface, while VTE provides the embedded terminal widget. PyGObject exposes the GTK, GDK, and VTE APIs to Python.

The application starts a separate Python process for the TUXIXI shell interface. That interface provides a colored prompt showing the username, hostname, and current directory. It handles a few commands directly and forwards other commands to `/bin/bash` for execution.

## Features

- GTK4 application window with an embedded VTE terminal.
- Scrollback configured for 10,000 lines.
- Custom prompt showing the user, hostname, and current directory.
- Bash-based execution of regular system commands.
- Built-in TUXIXI commands and aliases.
- 19 built-in foreground/background color themes.
- Font-size adjustment from 6 to 48 points.
- Saved theme and font-size preferences.
- Keyboard shortcuts for copy, paste, theme switching, font-size adjustment, and opening another window.
- User configuration stored under `~/.config/tuxixi/`.

## Requirements

The current source code requires:

- Linux with a working graphical desktop session.
- Python 3.
- GTK 4 and its GObject introspection bindings.
- PyGObject (`gi`).
- VTE for GTK 4, with the `Vte` introspection namespace version `3.91` available.
- Bash at `/bin/bash` for regular command execution.

Some built-in commands call external utilities. For example, `tuxixi/ip` uses `hostname`, `awk`, and `curl`; public-IP lookup requires an internet connection and access to the external service used by the command.

## Installation

### 1. Download and extract the source archive

Download `TUXIXI-1.0.0.tar.gz` from the project's GitHub Releases page. Open a terminal in the directory where the archive was saved and run:

```bash
tar -xzf TUXIXI-1.0.0.tar.gz
```

The archive is packaged with a top-level `TUXIXI/` directory. Enter it with:

```bash
cd TUXIXI
```

If you extracted the archive somewhere else, first navigate to that location. The source files should be together in the project directory.

### Ubuntu and Debian-based distributions

On supported releases where the packages are available, install Python, PyGObject, GTK4 introspection data, and the GTK4 version of VTE:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-vte-3.91
```

Package availability depends on the distribution release. The important requirement is that the installed packages provide GTK 4 and the `Vte-3.91` introspection namespace. Do not substitute GTK 3-only VTE bindings.

### Arch Linux

On Arch Linux, the corresponding packages are available from the official repositories:

```bash
sudo pacman -S python python-gobject gtk4 vte4
```

The application specifically requests VTE namespace version `3.91`; make sure the installed `vte4` package provides it.

### Other distributions

Install the equivalent packages from your distribution's official repositories. Package names differ between distributions, so use the distribution's package search or documentation to find:

- Python 3
- PyGObject / Python GObject bindings
- GTK 4
- VTE for GTK 4, including the `Vte-3.91` introspection typelib
- Bash

After installing the dependencies, continue with [Run TUXIXI](#run-tuxixi).

## Run TUXIXI

From the directory containing `main.py` and the other project files, execute:

```bash
python3 main.py
```

The main application loads the user's settings, creates the GTK4 window, embeds the VTE terminal, and starts `tuxixi_shell.py`.

Run the command from the project directory. The Python modules (`ui.py`, `terminal.py`, `settings.py`, `themes.py`, `aliases.py`, and `tuxixi_shell.py`) are expected to be alongside `main.py`.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl` + `Shift` + `C` | Copy selected terminal text |
| `Ctrl` + `Shift` + `V` | Paste text after replacing line breaks with spaces |
| `Ctrl` + `Shift` + `T` | Switch to the next color theme |
| `Ctrl` + `Shift` + `+` | Increase font size by one point |
| `Ctrl` + `Shift` + `-` | Decrease font size by one point |
| `Ctrl` + `Shift` + `N` | Open another TUXIXI window |

Font size is restricted to the range of 6–48 points. The exact key combination for `+` can vary with keyboard layout. The paste shortcut flattens line breaks into spaces before sending the text to the terminal; take care when pasting commands whose line breaks are meaningful.

## Built-in commands

Enter these commands exactly as shown in the TUXIXI prompt.

| Command | Description | Notes |
|---|---|---|
| `tuxixi/help` | Displays the custom command list and shortcut reference. | Handled by the TUXIXI shell. |
| `tuxixi/sys` | Shows memory usage and disk usage for `/`. | Uses `free -h` and `df -h /`. |
| `tuxixi/ip` | Shows the first local IP address and attempts to retrieve the public IP address. | Requires `hostname` and `awk`; public lookup also requires `curl` and network access. |
| `tuxixi/ver` | Prints the version string currently defined in the source. | The current alias text says `TUXIXI Terminal v1.0.0 (GTK 4 / VTE 3.91)`. |
| `ll` | Lists files, including hidden files, in a detailed format. | Uses `ls -la --color=auto --group-directories-first`. |
| `cls` | Clears the terminal display. | Uses `clear`. |

The aliases are defined in `aliases.py`. The alias lookup currently matches the entire entered command; these aliases are not general-purpose commands with their own argument parser.

## Shell behavior

The shell interface is implemented in `tuxixi_shell.py`.

### Prompt

The prompt displays the username, hostname, and current directory. The home directory is shown as `~` and subdirectories within the home directory are shown with a `~` prefix.

### Directory navigation

Use `cd` to change directories within the running TUXIXI shell:

```bash
cd /path/to/directory
cd ~
cd
```

Running `cd` without a path returns to the home directory. The directory change is handled inside the TUXIXI shell process so it persists for that shell session.

### Regular commands

Commands that are not recognized as TUXIXI-specific commands are executed using `/bin/bash`. Examples include:

```bash
ls
pwd
free -h
df -h /
```

The commands available depend on the utilities installed on the system and the current user's permissions. TUXIXI does not bypass Linux permissions or provide elevated privileges automatically.

### Exit

Enter either of the following to leave the TUXIXI shell:

```bash
exit
logout
```

These commands end the shell loop running inside the terminal window.

## Settings and configuration

TUXIXI stores user preferences in:

```text
~/.config/tuxixi/config.json
```

If the file does not exist, TUXIXI creates it with these default values:

```json
{
  "font": "Monospace",
  "font_size": 11,
  "theme": "Alacritty Dark"
}
```

| Setting | Meaning | Default |
|---|---|---|
| `font` | Terminal font family | `Monospace` |
| `font_size` | Terminal font size, in points | `11` |
| `theme` | Selected color theme | `Alacritty Dark` |

The theme and font-size keyboard shortcuts save their changes to this file. The application reads the saved settings at startup.

### Reset settings

To reset the stored preferences, close TUXIXI and remove the configuration file:

```bash
rm ~/.config/tuxixi/config.json
```

The next launch creates the default configuration again. This removes the saved settings file only; it does not uninstall the application or delete the source code.

## Color themes

TUXIXI currently defines the following themes in `themes.py`:

1. Matrix
2. Alacritty Dark
3. Monokai
4. Dracula
5. Nord
6. Gruvbox Dark
7. Solarized Dark
8. One Dark
9. Tokyo Night
10. Catppuccin
11. Cyberpunk
12. Classic Black/White
13. Classic White/Black
14. Solarized Light
15. PaperColor Light
16. Gruvbox Light
17. Purple Haze
18. Ocean Breeze
19. Retro Amber

Press `Ctrl` + `Shift` + `T` to cycle through the themes. The selected theme is saved in the user configuration file.

## Project structure

```text
TUXIXI/
├── main.py
├── ui.py
├── terminal.py
├── tuxixi_shell.py
├── settings.py
├── themes.py
└── aliases.py
```

### Source files

- **`main.py`** — Application entry point. Initializes the GTK4 application, loads the settings through the window activation flow, and starts the main window.
- **`ui.py`** — Creates the main GTK4 application window, embeds the terminal widget, and applies CSS styling.
- **`terminal.py`** — Creates and configures the VTE terminal, binds keyboard shortcuts, applies font and color settings, saves supported changes, and launches the shell process.
- **`tuxixi_shell.py`** — Implements the prompt, TUXIXI command handling, directory navigation, and Bash-based execution of regular commands.
- **`settings.py`** — Defines default settings and loads or saves the JSON configuration.
- **`themes.py`** — Defines theme foreground/background colors and converts them to GDK color objects.
- **`aliases.py`** — Defines custom command aliases, their descriptions, and the shortcut reference displayed by the help command.

## Troubleshooting

### `ModuleNotFoundError: No module named 'gi'`

PyGObject is missing from the Python environment being used. Install the system-provided PyGObject package for your distribution (for example, `python3-gi` on Ubuntu/Debian or `python-gobject` on Arch Linux). Then retry `python3 main.py`.

### `Namespace Vte not available` or a VTE version error

TUXIXI requests the `Vte` namespace at version `3.91`, which is the GTK4 VTE binding. Install the VTE GTK4 package and its introspection data. A GTK3-only VTE installation is not sufficient.

### `Namespace Gtk not available`

Check that GTK4 and its introspection bindings are installed. On Ubuntu/Debian-based systems, the relevant package is commonly `gir1.2-gtk-4.0`.

### `No such file or directory: tuxixi_shell.py` or a missing Python module

Make sure all seven source files are present in the same directory and start TUXIXI from that directory:

```bash
cd /path/to/TUXIXI
python3 main.py
```

Replace `/path/to/TUXIXI` with the actual path where you extracted the project.

### `tuxixi/ip` does not show the public IP address

The public-IP lookup depends on `curl`, a working internet connection, and the remote service being reachable. The alias prints `Error` if the lookup fails. Local IP detection can also vary on systems with multiple network interfaces.

### Theme or font-size changes are not saved

Check that your user account can write to `~/.config/tuxixi/`. The configuration file is managed by TUXIXI's `settings.py` module.

### Need more diagnostic information

Launch TUXIXI from an existing terminal:

```bash
python3 main.py
```

Read the error output printed to that terminal. Include the full relevant traceback and your Linux distribution when reporting an issue; do not include passwords, private keys, or other sensitive information.

## Development

To work from a Git checkout, clone the repository and enter the directory created by Git:

```bash
git clone <REPOSITORY_URL>
cd <CLONED_DIRECTORY>
python3 main.py
```

Replace `<REPOSITORY_URL>` with the actual repository URL and `<CLONED_DIRECTORY>` with the directory name created by `git clone`. Install the dependencies listed in [Requirements](#requirements) before launching the application.

The code is divided into modules so that the application startup, window UI, terminal widget, settings, themes, aliases, and shell interface have separate responsibilities. When changing a module, run the application again and test the affected behavior.

## License

TUXIXI Terminal is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See the [`LICENSE`](LICENSE) file for the full license text.

---

**TUXIXI Terminal — built for Linux.**
