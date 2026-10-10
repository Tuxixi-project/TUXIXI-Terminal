#!/usr/bin/env python3
import os, readline, shlex, socket, subprocess, sys, signal

readline.parse_and_bind("set editing-mode emacs")

def get_prompt():
    u, h = os.environ.get("USER", "user"), socket.gethostname()
    cwd, home = os.getcwd(), os.path.expanduser("~")
    display_cwd = "~" if cwd == home else ("~" + cwd[len(home):] if cwd.startswith(home + "/") else cwd)
    return f"\033[01;32m{u}@{h}\033[00m:\033[01;34m{display_cwd}\033[00m$ "

def run_command(cmd):
    cmd = cmd.strip()
    if not cmd: return
    if cmd == "tuxixi/help":
        from aliases import get_help
        print("\n".join([""] + get_help() + [""]))
        return
    from aliases import get_alias
    alias = get_alias(cmd)
    if alias:
        subprocess.run(alias, shell=True, executable="/bin/bash")
        return
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        print(f"bash: {e}"); return
    if parts and parts[0] == "cd":
        t = os.path.expanduser(parts[1]) if len(parts) > 1 else os.path.expanduser("~")
        try: os.chdir(t)
        except Exception as e: print(f"bash: cd: {t}: {e}")
        return
    
    try:
        subprocess.run(cmd, shell=True, executable="/bin/bash", env={**os.environ, "SHELL": "/bin/bash"})
    except KeyboardInterrupt:
        print()

def main():
    os.chdir(os.path.expanduser("~"))
    while True:
        try:
            raw_cmd = input(get_prompt())
            # Yapışdırılan mətndəki bütün yeni sətir (enter) simvollarını təmizləyirik:
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
