#!/usr/bin/env python3
import os
os.environ.setdefault("TERM", "xterm-256color")

import readline, shlex, socket, subprocess, sys, signal, time

readline.parse_and_bind("set editing-mode emacs")
readline.parse_and_bind("tab: complete")
readline.parse_and_bind("set horizontal-scroll-mode Off")

def get_prompt():
    u, h = os.environ.get("USER", "user"), socket.gethostname()
    cwd, home = os.getcwd(), os.path.expanduser("~")
    display_cwd = "~" if cwd == home else ("~" + cwd[len(home):] if cwd.startswith(home + "/") else cwd)

    return f"\001\033[01;32m\002{u}@{h}\001\033[00m\002:\001\033[01;34m\002{display_cwd}\001\033[00m\002$ "

def get_system_shells():
    shells = set()
    try:
        with open("/etc/shells", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    shells.add(os.path.basename(line))
    except Exception:
        shells = {"bash", "sh", "zsh", "fish", "dash", "csh", "tcsh"}
    return shells

def run_command(cmd):
    cmd = cmd.strip()
    if not cmd: return

    if cmd == "tuxixi/help":
        try:
            from aliases import get_help
            print("\n".join([""] + get_help() + [""]))
        except Exception as e:
            print(f"Xəta: {e}", file=sys.stderr)
        return

    try:
        from aliases import get_alias
        alias = get_alias(cmd)
        if alias:
            cmd = alias
    except Exception as e:
        print(f"Alias xətası: {e}", file=sys.stderr)

    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        print(f"Sintaksis xətası: {e}", file=sys.stderr)
        return

    if parts and parts[0] == "cd":
        t = os.path.expanduser(parts[1]) if len(parts) > 1 else os.path.expanduser("~")
        try:
            os.chdir(t)
        except Exception as e:
            print(f"cd: {t}: {e}", file=sys.stderr)
        return

    shell_executable = os.environ.get("SHELL", "/bin/bash")
    if not (os.path.isfile(shell_executable) and os.access(shell_executable, os.X_OK)):
        shell_executable = "/bin/sh"

    if not (os.path.isfile(shell_executable) and os.access(shell_executable, os.X_OK)):
        raise FileNotFoundError("Sistemdə icra edilə bilən heç bir qabıq (shell) tapılmadı.")

    valid_shells = get_system_shells()
    is_interactive = False
    if parts:
        cmd_name = os.path.basename(parts[0])
        if cmd_name in valid_shells:
            is_interactive = True

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            executable=shell_executable,
            env=os.environ.copy(),
            start_new_session=not is_interactive
        )
        while proc.poll() is None:
            time.sleep(0.05)
    except KeyboardInterrupt:
        if proc and proc.poll() is None:
            try:
                if not is_interactive:
                    os.killpg(proc.pid, signal.SIGINT)
                else:
                    proc.send_signal(signal.SIGINT)
                proc.wait(timeout=1)
            except Exception:
                try:
                    if not is_interactive:
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    pass
        print()

def main():
    try:
        os.chdir(os.path.expanduser("~"))
    except Exception:
        pass

    run_command("tuxixi/help")

    while True:
        try:
            raw_cmd = input(get_prompt())
            cmd = raw_cmd.replace("\r", " ").replace("\n", " ")
            if cmd.strip() in ("exit", "logout"):
                break
            run_command(cmd)
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print()
            break

if __name__ == "__main__":
    main()
