#!/usr/bin/env python3
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

APP_VERSION = "2.1.1"
MANIFEST_SCHEMA = 1
MANIFEST_FILENAME = "manifest.json"

REPO_OWNER = "Tuxixi-Foundation"
REPO_NAME = "TUXIXI-Terminal"
DEFAULT_REF = "main"
REPO_RAW_BASE = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{DEFAULT_REF}"
)

MAX_MANIFEST_BYTES = 256 * 1024  # 256 KiB
MAX_FILE_BYTES = 16 * 1024 * 1024  # 16 MiB
DOWNLOAD_TIMEOUT = 10
CHUNK_SIZE = 65536

REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VALID_GROUPS = ("self", "theme")

CLI_FILES = {"tuxixi", "ll", "cls"}

# Default files included when running --generate-manifest
# (repo-relative POSIX path, group, executable)
DEFAULT_MANIFEST_SPECS = (
    ("main.py", "self", True),
    ("ui.py", "self", False),
    ("terminal.py", "self", False),
    ("settings.py", "self", False),
    ("updater.py", "self", False),
    ("bin/tuxixi", "self", True),
    ("bin/ll", "self", True),
    ("bin/cls", "self", True),
    ("tuxixi-512.png", "self", False),
    ("themes.py", "theme", False),
)

# Backwards-compatible tuples
SELF_FILES = tuple(
    os.path.basename(p) if p.startswith("bin/") else p
    for p, grp, _ in DEFAULT_MANIFEST_SPECS
    if grp == "self"
)
THEME_FILES = tuple(
    p for p, grp, _ in DEFAULT_MANIFEST_SPECS if grp == "theme"
)
EXECUTABLE_FILES = {
    os.path.basename(p) if p.startswith("bin/") else p
    for p, _, exe in DEFAULT_MANIFEST_SPECS
    if exe
}

RESET = "\033[0m"
BOLD = "\033[1m"
PURPLE = "\033[38;2;192;132;252m"
CYAN = "\033[38;2;34;211;238m"
LIME = "\033[38;2;163;230;53m"
AMBER = "\033[38;2;251;191;36m"
SLATE = "\033[38;2;148;163;184m"
RED = "\033[38;2;248;113;113m"


class UpdateError(Exception):
    """Base error for updater failures."""


class ManifestError(UpdateError):
    """Raised when remote or local manifest is malformed or unsupported."""


class UpdateSecurityError(UpdateError):
    """Raised on path traversal, symlink escape, or integrity violations."""


class UpdateLockError(UpdateError):
    """Raised when another update process already holds the lock."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_local_bytes(path: str):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def validate_ref(ref: str) -> str:
    if not isinstance(ref, str) or not REF_RE.match(ref):
        raise UpdateSecurityError(f"Invalid git ref: {ref!r}")
    if (
        ref.startswith("/")
        or ref.endswith("/")
        or "//" in ref
        or ".." in ref
        or ref.startswith("-")
    ):
        raise UpdateSecurityError(f"Unsafe git ref: {ref!r}")
    return ref


def build_raw_base_url(ref: str = DEFAULT_REF) -> str:
    clean_ref = validate_ref(ref)
    encoded_ref = "/".join(
        urllib.parse.quote(part, safe="") for part in clean_ref.split("/")
    )
    return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{encoded_ref}"


def validate_relative_path(rel_path: str) -> str:
    """Validate that a manifest path is a safe relative POSIX path."""
    if not isinstance(rel_path, str) or not rel_path:
        raise UpdateSecurityError("Manifest path must be a non-empty string.")
    if "\x00" in rel_path or "\\" in rel_path or rel_path.startswith("/"):
        raise UpdateSecurityError(f"Unsafe manifest path: {rel_path!r}")
    parts = rel_path.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise UpdateSecurityError(f"Path traversal rejected: {rel_path!r}")
        if part == ".git" or part.startswith(".tuxixi-update"):
            raise UpdateSecurityError(f"Reserved path rejected: {rel_path!r}")
    if rel_path == MANIFEST_FILENAME:
        raise UpdateSecurityError("Manifest cannot overwrite manifest.json directly.")
    return rel_path


def _ensure_contained_no_symlinks(project_dir: str, rel_parts: tuple) -> str:
    real_root = os.path.realpath(project_dir)
    current = real_root
    for part in rel_parts:
        current = os.path.join(current, part)
        if os.path.islink(current):
            raise UpdateSecurityError(
                f"Refusing to write through symlink: {current}"
            )
    real_dest = os.path.realpath(current)
    try:
        common = os.path.commonpath([real_root, real_dest])
    except ValueError as exc:
        raise UpdateSecurityError(f"Destination escapes project root: {current}") from exc
    if common != real_root or real_dest == real_root:
        raise UpdateSecurityError(f"Destination escapes project root: {current}")
    return current


def resolve_local_path(project_dir: str, filename: str) -> str:
    """Resolve a safe destination path inside project_dir.

    Supports both repo-relative paths (e.g. 'bin/tuxixi') and legacy flat installs
    where CLI helpers live in the root directory instead of 'bin/'.
    """
    clean_rel = validate_relative_path(filename)
    parts = tuple(clean_rel.split("/"))

    has_bin_dir = os.path.isdir(os.path.join(project_dir, "bin"))

    # Legacy manifest/caller passing bare CLI name when bin/ exists
    if len(parts) == 1 and parts[0] in CLI_FILES and has_bin_dir:
        parts = ("bin", parts[0])
    # Manifest specifying bin/<cli> on a legacy flat install without bin/
    elif (
        len(parts) == 2
        and parts[0] == "bin"
        and parts[1] in CLI_FILES
        and not has_bin_dir
        and os.path.isfile(os.path.join(project_dir, parts[1]))
    ):
        parts = (parts[1],)

    return _ensure_contained_no_symlinks(project_dir, parts)


def _download_url(url: str, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise UpdateSecurityError(f"Refusing non-HTTPS URL: {url!r}")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"TUXIXI-Updater/{APP_VERSION}"},
    )
    chunks = []
    total = 0
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
        while True:
            chunk = resp.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise UpdateSecurityError(
                    f"Remote response exceeded size limit ({max_bytes} bytes): {url}"
                )
            chunks.append(chunk)
    return b"".join(chunks)


def parse_manifest(raw_bytes: bytes) -> dict:
    try:
        text = raw_bytes.decode("utf-8")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Invalid manifest JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("Manifest root must be a JSON object.")

    schema = data.get("schema")
    if isinstance(schema, bool) or schema != MANIFEST_SCHEMA:
        raise ManifestError(
            f"Unsupported manifest schema: {schema!r} (expected {MANIFEST_SCHEMA})."
        )

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ManifestError("Manifest 'version' must be a non-empty string.")

    raw_files = data.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ManifestError("Manifest 'files' must be a non-empty list.")

    seen_paths = set()
    validated_files = []
    for idx, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise ManifestError(f"Manifest entry #{idx} must be an object.")

        path = validate_relative_path(item.get("path"))
        if path in seen_paths:
            raise ManifestError(f"Duplicate path in manifest: {path!r}")
        seen_paths.add(path)

        group = item.get("group")
        if group not in VALID_GROUPS:
            raise ManifestError(
                f"Invalid group {group!r} for {path!r} (expected one of {VALID_GROUPS})."
            )

        digest = item.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.match(digest.lower()):
            raise ManifestError(f"Invalid sha256 for {path!r}.")

        size = item.get("size")
        if (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or size > MAX_FILE_BYTES
        ):
            raise ManifestError(f"Invalid size {size!r} for {path!r}.")

        executable = item.get("executable")
        if not isinstance(executable, bool):
            raise ManifestError(f"Invalid executable flag for {path!r}.")

        validated_files.append(
            {
                "path": path,
                "group": group,
                "sha256": digest.lower(),
                "size": size,
                "executable": executable,
            }
        )

    return {
        "schema": schema,
        "version": version.strip(),
        "files": validated_files,
    }


def fetch_manifest(ref: str = DEFAULT_REF) -> dict:
    base_url = build_raw_base_url(ref)
    url = f"{base_url}/{MANIFEST_FILENAME}"
    raw = _download_url(url, max_bytes=MAX_MANIFEST_BYTES)
    return parse_manifest(raw)


def fetch_remote_file(rel_path: str, ref: str = DEFAULT_REF, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    clean_rel = validate_relative_path(rel_path)
    base_url = build_raw_base_url(ref)
    encoded_path = "/".join(
        urllib.parse.quote(part, safe="") for part in clean_rel.split("/")
    )
    return _download_url(f"{base_url}/{encoded_path}", max_bytes=max_bytes)


def atomic_write(dest_path: str, data: bytes, make_exec: bool = False):
    parent = os.path.dirname(dest_path)
    os.makedirs(parent, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=parent,
            prefix=".update.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(data)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        os.chmod(tmp_path, 0o755 if make_exec else 0o644)
        os.replace(tmp_path, dest_path)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


@contextmanager
def acquire_update_lock(project_dir: str):
    """Serialize concurrent updates targeting the same installation directory."""
    real_root = os.path.realpath(project_dir)
    key = hashlib.sha256(real_root.encode("utf-8")).hexdigest()[:16]
    lock_path = os.path.join(tempfile.gettempdir(), f"tuxixi-update-{key}.lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise UpdateLockError(
                "Another TUXIXI update is already in progress."
            ) from exc
        yield lock_path
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def build_manifest_dict(
    project_dir: str,
    version: str = APP_VERSION,
    specs=DEFAULT_MANIFEST_SPECS,
) -> dict:
    files = []
    for rel_path, group, executable in specs:
        clean_rel = validate_relative_path(rel_path)
        local_path = _ensure_contained_no_symlinks(
            project_dir, tuple(clean_rel.split("/"))
        )
        data = read_local_bytes(local_path)
        if data is None:
            raise FileNotFoundError(
                f"Cannot build manifest: missing file {clean_rel!r} in {project_dir}"
            )
        files.append(
            {
                "path": clean_rel,
                "group": group,
                "sha256": sha256_bytes(data),
                "size": len(data),
                "executable": bool(executable),
            }
        )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "version": version,
        "files": files,
    }
    # Self-validate generated manifest before writing
    parse_manifest(json.dumps(manifest).encode("utf-8"))
    return manifest


def generate_manifest(
    project_dir: str = None,
    output_path: str = None,
    version: str = APP_VERSION,
    specs=DEFAULT_MANIFEST_SPECS,
) -> str:
    root = project_dir or os.path.dirname(os.path.abspath(__file__))
    dest = output_path or os.path.join(root, MANIFEST_FILENAME)
    manifest = build_manifest_dict(root, version=version, specs=specs)
    payload = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    atomic_write(dest, payload, make_exec=False)
    return dest


def _stage_verified_files(pending: list, stage_dir: str, ref: str) -> list:
    """Phase 1: Download all pending files into stage_dir and verify SHA256 + size."""
    staged = []
    for idx, item in enumerate(pending):
        entry = item["entry"]
        rel_path = entry["path"]
        expected_hash = entry["sha256"]
        expected_size = entry["size"]

        remote_bytes = fetch_remote_file(
            rel_path,
            ref=ref,
            max_bytes=max(expected_size, 1),
        )
        if len(remote_bytes) != expected_size:
            raise UpdateSecurityError(
                f"Size mismatch for {rel_path}: expected {expected_size}, got {len(remote_bytes)}"
            )
        actual_hash = sha256_bytes(remote_bytes)
        if actual_hash != expected_hash:
            raise UpdateSecurityError(
                f"SHA256 mismatch for {rel_path}: "
                f"expected {expected_hash[:12]}, got {actual_hash[:12]}"
            )

        stage_file = os.path.join(stage_dir, f"{idx:04d}.staged")
        with open(stage_file, "wb") as f:
            f.write(remote_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(stage_file, 0o755 if entry["executable"] else 0o644)

        staged.append(
            {
                "entry": entry,
                "local_path": item["local_path"],
                "local_hash": item["local_hash"],
                "stage_file": stage_file,
            }
        )
    return staged


def _commit_staged_with_rollback(staged: list, backup_dir: str) -> None:
    """Phase 2: Back up existing targets and atomically replace; roll back on any failure."""
    applied = []
    created_dirs = []
    try:
        for idx, item in enumerate(staged):
            local_path = item["local_path"]
            stage_file = item["stage_file"]
            parent = os.path.dirname(local_path)

            if parent and not os.path.isdir(parent):
                # Track missing directories so rollback can remove them if empty
                missing = []
                cur = parent
                while cur and not os.path.exists(cur):
                    missing.append(cur)
                    next_cur = os.path.dirname(cur)
                    if next_cur == cur:
                        break
                    cur = next_cur
                os.makedirs(parent, exist_ok=True)
                created_dirs.extend(missing)

            backup_file = None
            if os.path.exists(local_path):
                backup_file = os.path.join(backup_dir, f"{idx:04d}.bak")
                shutil.copy2(local_path, backup_file)

            os.replace(stage_file, local_path)
            applied.append((local_path, backup_file))
    except Exception:
        rollback_errors = []
        for local_path, backup_file in reversed(applied):
            try:
                if backup_file is not None and os.path.exists(backup_file):
                    os.replace(backup_file, local_path)
                elif os.path.exists(local_path):
                    os.unlink(local_path)
            except OSError as rb_err:
                rollback_errors.append(f"{local_path}: {rb_err}")

        for d in sorted(set(created_dirs), key=len, reverse=True):
            try:
                os.rmdir(d)
            except OSError:
                pass

        if rollback_errors:
            print(
                f"  {RED}✗ Rollback incomplete:{RESET} {'; '.join(rollback_errors)}",
                file=sys.stderr,
            )
        raise


def run_update(
    mode: str = "all",
    check_only: bool = False,
    ref: str = DEFAULT_REF,
    project_dir: str = None,
) -> int:
    root_dir = project_dir or os.path.dirname(os.path.abspath(__file__))

    try:
        clean_ref = validate_ref(ref)
    except UpdateError as exc:
        print(f"{RED}Error:{RESET} {exc}", file=sys.stderr)
        return 1

    if mode == "self":
        title = "TUXIXI SELF UPDATE"
    elif mode == "theme":
        title = "TUXIXI THEME SYNC"
    else:
        title = "TUXIXI UPDATE"

    if check_only:
        title += " (CHECK ONLY)"

    print(f"\n{BOLD}{PURPLE}◆ {title}{RESET} {SLATE}(ref: {clean_ref}){RESET}")
    print(f"{SLATE}────────────────────────────────────────{RESET}\n")

    try:
        manifest = fetch_manifest(ref=clean_ref)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(
                f"  {RED}✗{RESET} Remote {MANIFEST_FILENAME} not found (HTTP 404) on ref '{clean_ref}'.\n"
                f"  {SLATE}Aborted safely — no local files were modified.{RESET}\n",
                file=sys.stderr,
            )
        else:
            print(
                f"  {RED}✗{RESET} Failed to fetch {MANIFEST_FILENAME} (HTTP {exc.code}).\n",
                file=sys.stderr,
            )
        return 1
    except (UpdateError, OSError, urllib.error.URLError) as exc:
        print(
            f"  {RED}✗{RESET} Failed to verify {MANIFEST_FILENAME}: {exc}\n",
            file=sys.stderr,
        )
        return 1

    if mode == "self":
        targets = [e for e in manifest["files"] if e["group"] == "self"]
    elif mode == "theme":
        targets = [e for e in manifest["files"] if e["group"] == "theme"]
    else:
        targets = list(manifest["files"])

    pending = []
    up_to_date_count = 0

    try:
        for entry in targets:
            rel_path = entry["path"]
            local_path = resolve_local_path(root_dir, rel_path)
            local_bytes = read_local_bytes(local_path)
            local_hash = sha256_bytes(local_bytes) if local_bytes is not None else None
            remote_hash = entry["sha256"]

            if local_hash == remote_hash:
                print(
                    f"  {LIME}✓{RESET} {rel_path:<18} "
                    f"{SLATE}up to date ({remote_hash[:7]}){RESET}"
                )
                up_to_date_count += 1
            else:
                old_short = local_hash[:7] if local_hash else "missing"
                new_short = remote_hash[:7]
                if check_only:
                    print(
                        f"  {AMBER}↑{RESET} {rel_path:<18} "
                        f"{AMBER}update available{RESET} {SLATE}({old_short} ➔ {new_short}){RESET}"
                    )
                pending.append(
                    {
                        "entry": entry,
                        "local_path": local_path,
                        "local_hash": local_hash,
                    }
                )
    except (UpdateError, OSError) as exc:
        print(
            f"\n  {RED}✗ Security/path validation failed:{RESET} {exc}\n"
            f"  {SLATE}Aborted safely — no local files were modified.{RESET}\n",
            file=sys.stderr,
        )
        return 1

    if check_only:
        print()
        if pending:
            print(
                f"{PURPLE}◆{RESET} {AMBER}{len(pending)} file(s) have updates available "
                f"(remote v{manifest['version']}).{RESET} "
                f"{SLATE}Run 'tuxixi update' to apply.{RESET}\n"
            )
        else:
            print(
                f"{PURPLE}◆{RESET} {LIME}Everything is up to date "
                f"(v{manifest['version']}).{RESET}\n"
            )
        return 0

    if not pending:
        print()
        print(
            f"{PURPLE}◆{RESET} {LIME}Already up to date "
            f"({up_to_date_count} checked, v{manifest['version']}).{RESET}\n"
        )
        return 0

    stage_dir = None
    backup_dir = None
    try:
        with acquire_update_lock(root_dir):
            stage_dir = tempfile.mkdtemp(
                prefix=".tuxixi-update-stage-", dir=root_dir
            )
            backup_dir = tempfile.mkdtemp(
                prefix=".tuxixi-update-backup-", dir=root_dir
            )

            # Phase 1: Download & verify everything before touching live files
            staged = _stage_verified_files(pending, stage_dir, ref=clean_ref)

            # Phase 2: Atomic swap with rollback on any error
            _commit_staged_with_rollback(staged, backup_dir)

            for item in staged:
                rel_path = item["entry"]["path"]
                old_short = item["local_hash"][:7] if item["local_hash"] else "missing"
                new_short = item["entry"]["sha256"][:7]
                print(
                    f"  {CYAN}↻{RESET} {rel_path:<18} "
                    f"{LIME}updated{RESET} {SLATE}({old_short} ➔ {new_short}){RESET}"
                )

    except UpdateLockError as exc:
        print(f"\n  {AMBER}⚠{RESET} {exc}\n", file=sys.stderr)
        return 1
    except (UpdateError, urllib.error.URLError, OSError) as exc:
        print(
            f"\n  {RED}✗ Update failed:{RESET} {exc}\n"
            f"  {SLATE}All changes were safely aborted/rolled back.{RESET}\n",
            file=sys.stderr,
        )
        return 1
    finally:
        if stage_dir and os.path.isdir(stage_dir):
            shutil.rmtree(stage_dir, ignore_errors=True)
        if backup_dir and os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)

    print()
    print(
        f"{PURPLE}◆{RESET} {LIME}{len(pending)} file(s) updated "
        f"(v{manifest['version']}).{RESET} "
        f"{SLATE}Restart TUXIXI to apply changes.{RESET}\n"
    )
    return 0


def main():
    args = sys.argv[1:]
    want_self = False
    want_theme = False
    check_only = False
    want_generate = False
    ref = DEFAULT_REF

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--self":
            want_self = True
        elif arg == "--theme":
            want_theme = True
        elif arg == "--check":
            check_only = True
        elif arg == "--generate-manifest":
            want_generate = True
        elif arg == "--ref":
            if i + 1 >= len(args):
                print(f"{RED}Missing value for --ref{RESET}", file=sys.stderr)
                sys.exit(2)
            i += 1
            ref = args[i]
        elif arg.startswith("--ref="):
            ref = arg.split("=", 1)[1]
        else:
            print(f"{RED}Unknown update option:{RESET} {arg}", file=sys.stderr)
            print(
                f"Usage: {LIME}tuxixi update [--self | --theme | --check | --ref <tag> | --generate-manifest]{RESET}",
                file=sys.stderr,
            )
            sys.exit(2)
        i += 1

    if want_generate:
        try:
            out_path = generate_manifest()
            print(f"{PURPLE}◆{RESET} {LIME}Generated {out_path}{RESET} {SLATE}(v{APP_VERSION}){RESET}")
            sys.exit(0)
        except Exception as exc:
            print(f"{RED}Error generating manifest:{RESET} {exc}", file=sys.stderr)
            sys.exit(1)

    if want_self and not want_theme:
        mode = "self"
    elif want_theme and not want_self:
        mode = "theme"
    else:
        mode = "all"

    sys.exit(run_update(mode=mode, check_only=check_only, ref=ref))


if __name__ == "__main__":
    main()
