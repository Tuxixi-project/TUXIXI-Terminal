# TUXIXI Terminal

TUXIXI Terminal is a Linux terminal emulator built with **Python, GTK4, and VTE**.

## Requirements

Before running TUXIXI, make sure you have:

- Python 3
- GTK4
- PyGObject
- VTE for GTK4 (`Vte-3.91`)

### Install dependencies

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-vte-3.91
```

**Arch Linux:**

```bash
sudo pacman -S python python-gobject gtk4 vte4
```

## Installation

1. Download `TUXIXI-Terminal-v1.0.0.tar.gz` and `install.sh` from the project's release page.
2. Put both files in the **same directory**.
3. Open a terminal in that directory.
4. Give the installation script permission to run:

```bash
chmod +x install.sh
```

5. Run the installer:

```bash
./install.sh
```

The installer will extract the archive and create the `tuxixi` directory.

## Run TUXIXI

Enter the project directory:

```bash
cd tuxixi
```

Start the terminal:

```bash
python3 main.py
```

Make sure all project files remain together inside the `tuxixi` directory.

## Contact

For questions, feedback, bug reports, or other inquiries, contact the project team:

**Email:** [tuxixi_team@proton.me](mailto:tuxixi_team@proton.me)

---

**TUXIXI Terminal Team**


> **Coming soon:** TUXIXI Terminal will also be available in AppImage format. Stay tuned!
