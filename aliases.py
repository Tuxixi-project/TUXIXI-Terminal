import subprocess

ALIASES = {
    "tuxixi/sys": "echo -e '\033[1;32m--- TUXIXI System Status ---\033[0m' && free -h && echo '' && df -h /",
    "tuxixi/ip": "echo -e 'Internal IP: '$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}' || hostname -i 2>/dev/null) && echo -e 'External IP: '$(curl -s --max-time 3 ifconfig.me 2>/dev/null || echo 'Error')",
    "ll": "ls -la --color=auto --group-directories-first",
    "cls": "clear",
    "tuxixi/ver": "echo 'TUXIXI Terminal v1.1.2 (GTK 4 / VTE 3.91)'"
}

DESCRIPTIONS = {
    "tuxixi/sys": "Displays system resource status",
    "tuxixi/ip": "Shows local and public IP addresses",
    "ll": "Lists directory contents in detailed format with colors",
    "cls": "Clears the terminal screen",
    "tuxixi/ver": "Displays TUXIXI Terminal version info"
}

HOTKEYS = {
    "Ctrl + Shift + C": "Copy selected text",
    "Ctrl + Shift + V": "Paste text cleanly",
    "Ctrl + Shift + T": "Cycle through color themes",
    "Ctrl + Shift + +": "Increase font size",
    "Ctrl + Shift + -": "Decrease font size",
    "Ctrl + Shift + N": "Open a new TUXIXI window"
}

def get_alias(cmd):
    return ALIASES.get(cmd.strip(), None)

def get_help():
    lines = ["\033[1;36mTUXIXI Custom Commands:\033[0m"]
    for k, desc in DESCRIPTIONS.items():
        lines.append(f"  \033[1;32m{k:<15}\033[0m -> {desc}")

    lines.append("\n\033[1;36mTUXIXI Keyboard Shortcuts:\033[0m")
    for hk, desc in HOTKEYS.items():
        lines.append(f"  \033[1;33m{hk:<20}\033[0m -> {desc}")

    return lines
