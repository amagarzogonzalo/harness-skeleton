#!/usr/bin/env python3
"""Enable, disable, and inspect the opt-in modules in `modules/`.

    python bin/modules.py list
    python bin/modules.py enable lang-python
    python bin/modules.py enable lang-python --with-hooks
    python bin/modules.py disable lang-python

A module is a self-contained folder: `module.toml` plus agents, skills, hooks,
and a check script. Enabling copies *only* the agents and skills into the active
paths. Hooks are not copied unless `--with-hooks` is passed, because every file
in `.opencode/plugins/` loads at startup and runs with the harness's privileges.

`modules/.enabled.json` records every copied file and its SHA-256. Disabling
removes only files whose content still matches the recorded hash, so a file you
edited is never deleted. There is no `--force` for disable for that reason.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path("modules") / ".enabled.json"
NAME_RE = r"^[a-z0-9][a-z0-9-]*$"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_state(root: Path) -> dict:
    path = root / STATE
    if not path.exists():
        return {"modules": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("modules", {})
    return data


def save_state(root: Path, state: dict) -> None:
    path = root / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


CORE_AGENTS = {
    "plan",
    "build",
    "critic",
    "scribe",
    "security-reviewer",
    "explore",
    "general",
}


def load_opencode(root: Path) -> dict:
    path = root / "opencode.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_opencode(root: Path, config: dict) -> None:
    (root / "opencode.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def task_map(config: dict) -> dict:
    permission = config.setdefault("permission", {})
    task = permission.get("task")
    if task is None:
        task = {"*": "deny"}
        permission["task"] = task
    if not isinstance(task, dict):
        raise SystemExit("opencode.json: permission.task must be an object")
    return task


def grant_task(root: Path, agents: list[str], existing: dict) -> tuple[dict, list[str]]:
    """Allow the module's agents to be spawned, while recording how to undo it.

    A user-set `deny` is respected, not overwritten. The previous value for every
    agent is stored in the module state so `disable` restores it instead of
    deleting a permission the user wrote.
    """
    config = load_opencode(root)
    task = task_map(config)
    previous = dict(existing.get("task_permissions", {}))
    changed: list[str] = []

    for agent in agents:
        if agent in CORE_AGENTS:
            continue
        if agent in previous:
            if task.get(agent) in (None, "allow", "ask"):
                task[agent] = "allow"
            continue

        prior = task.get(agent)
        previous[agent] = prior
        if prior == "deny":
            print(
                f"warn: permission.task[{agent!r}] is deny; leaving it. "
                "Change it to allow if you want the agent available.",
                file=sys.stderr,
            )
            continue
        task[agent] = "allow"
        changed.append(agent)

    if changed:
        save_opencode(root, config)
    return previous, changed


def revoke_task(root: Path, entry: dict) -> list[str]:
    config = load_opencode(root)
    task = task_map(config)
    changed: list[str] = []

    for agent, prior in entry.get("task_permissions", {}).items():
        if agent in CORE_AGENTS or task.get(agent) != "allow":
            continue
        if prior is None:
            task.pop(agent, None)
        else:
            task[agent] = prior
        changed.append(agent)

    if changed:
        save_opencode(root, config)
    return changed


def module_paths(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    base = root / "modules"
    if not base.exists():
        return found
    for manifest in sorted(base.glob("*/module.toml")):
        found[manifest.parent.name] = manifest
    return found


def load_manifest(path: Path) -> dict:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    data.setdefault("name", path.parent.name)
    data.setdefault("agents", [])
    data.setdefault("skills", [])
    data.setdefault("hooks", [])
    data.setdefault("stack", [])
    data.setdefault("role", "review")
    data.setdefault("status", "stable")
    return data


def validate_name(name: str) -> None:
    import re

    if not re.fullmatch(NAME_RE, name):
        raise SystemExit(f"invalid module name {name!r}; expected [a-z0-9-]")


def planned_files(root: Path, manifest: dict, with_hooks: bool) -> list[tuple[Path, Path]]:
    base = root / "modules" / manifest["name"]
    pairs: list[tuple[Path, Path]] = []

    for agent in manifest["agents"]:
        src = base / "agent" / f"{agent}.md"
        if not src.is_file():
            raise SystemExit(f"{manifest['name']}: missing agent file {src}")
        pairs.append((src, root / ".opencode" / "agent" / src.name))

    for skill in manifest["skills"]:
        src_dir = base / "skills" / skill
        if not src_dir.is_dir():
            raise SystemExit(f"{manifest['name']}: missing skill directory {src_dir}")
        for src in sorted(p for p in src_dir.rglob("*") if p.is_file()):
            rel = src.relative_to(src_dir)
            pairs.append((src, root / ".opencode" / "skills" / skill / rel))

    if with_hooks:
        for hook in manifest["hooks"]:
            src = base / "hooks" / hook
            if not src.is_file():
                raise SystemExit(f"{manifest['name']}: missing hook file {src}")
            pairs.append((src, root / ".opencode" / "plugins" / src.name))

    return pairs


def enable(root: Path, name: str, force: bool, with_hooks: bool, dry_run: bool) -> int:
    manifests = module_paths(root)
    if name not in manifests:
        raise SystemExit(f"unknown module {name!r}; available: {', '.join(manifests) or 'none'}")

    manifest = load_manifest(manifests[name])
    if manifest["name"] != name:
        raise SystemExit(f"{manifests[name]}: name is {manifest['name']!r}, expected {name!r}")
    state = load_state(root)
    existing = state["modules"].get(name, {})
    recorded = {entry["dst"]: entry["sha256"] for entry in existing.get("files", [])}
    pairs = planned_files(root, manifest, with_hooks)

    actions: list[str] = []
    updates: list[dict] = []
    blocked: list[str] = []

    for src, dst in pairs:
        rel_dst = dst.relative_to(root).as_posix()
        rel_src = src.relative_to(root).as_posix()
        new_hash = sha256(src)

        if dst.exists():
            current = sha256(dst)
            if current == new_hash:
                actions.append(f"unchanged {rel_dst}")
                updates.append({"src": rel_src, "dst": rel_dst, "sha256": new_hash})
                continue
            if rel_dst not in recorded:
                blocked.append(f"{rel_dst} exists and was not created by this module")
                continue
            if not force:
                blocked.append(f"{rel_dst} differs from the module copy (use --force)")
                continue
            actions.append(f"overwrite {rel_dst}")
        else:
            actions.append(f"copy      {rel_src} -> {rel_dst}")

        updates.append({"src": rel_src, "dst": rel_dst, "sha256": new_hash})
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    if blocked:
        for item in blocked:
            print(f"error: {item}", file=sys.stderr)
        print("nothing changed; resolve the conflicts or omit the module", file=sys.stderr)
        return 1

    if dry_run:
        for action in actions:
            print(f"dry-run: {action}")
        for agent in manifest["agents"]:
            if agent not in CORE_AGENTS:
                print(f"dry-run: task allow {agent}")
        return 0

    task_previous, task_changed = grant_task(root, manifest["agents"], existing)

    # Keep records for files that are still present but no longer declared, so
    # `disable` can still find and remove them. New/updated records win.
    by_dst = {entry["dst"]: entry for entry in existing.get("files", [])}
    by_dst.update({entry["dst"]: entry for entry in updates})
    state["modules"][name] = {
        "name": name,
        "role": manifest["role"],
        "agents": manifest["agents"],
        "task_permissions": task_previous,
        "files": sorted(by_dst.values(), key=lambda item: item["dst"]),
    }
    save_state(root, state)

    for action in actions:
        print(action)
    for agent in task_changed:
        print(f"task allow {agent}")
    print(f"enabled {name} ({len(updates)} files)")

    if manifest["hooks"]:
        state_hooks = ", ".join(manifest["hooks"])
        if with_hooks:
            print(f"hooks loaded: {state_hooks} (restart opencode)")
        else:
            print(f"hooks available but not copied: {state_hooks} (re-run with --with-hooks)")

    return 0


def disable(root: Path, name: str, dry_run: bool) -> int:
    state = load_state(root)
    entry = state["modules"].get(name)
    if not entry:
        print(f"{name} is not enabled")
        return 0

    removed = 0
    for record in entry.get("files", []):
        dst = root / record["dst"]
        if not dst.exists():
            continue
        if sha256(dst) != record["sha256"]:
            print(f"kept {record['dst']}: modified since enable")
            continue
        if dry_run:
            print(f"dry-run: remove {record['dst']}")
        else:
            dst.unlink()
            print(f"remove {record['dst']}")
        removed += 1

    if dry_run:
        task_changed = sorted(entry.get("task_permissions", {}))
        for agent in task_changed:
            print(f"dry-run: task revoke {agent}")
    else:
        task_changed = revoke_task(root, entry)
        for agent in task_changed:
            print(f"task revoke {agent}")

    if not dry_run:
        # Remove now-empty skill directories, deepest first.
        for record in sorted(entry.get("files", []), key=lambda item: item["dst"], reverse=True):
            parent = (root / record["dst"]).parent
            while parent != root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        del state["modules"][name]
        save_state(root, state)

    print(f"{'would disable' if dry_run else 'disabled'} {name} ({removed} files)")
    return 0


def list_modules(root: Path) -> int:
    manifests = module_paths(root)
    state = load_state(root)
    enabled = state["modules"]

    if not manifests:
        print("no modules found under modules/")
        return 0

    print(f"{'module':<20} {'status':<9} {'on':<4} {'agents':>6} {'skills':>6} {'hooks':>5}  stack")
    print("-" * 78)
    for name, path in manifests.items():
        manifest = load_manifest(path)
        marker = next((m for m in manifest["stack"] if (root / m).exists()), "-")
        on = "yes" if name in enabled else "no"
        print(
            f"{name:<20} {manifest['status']:<9} {on:<4} "
            f"{len(manifest['agents']):>6} {len(manifest['skills']):>6} "
            f"{len(manifest['hooks']):>5}  {marker}"
        )

    if enabled:
        print("\nenabled: " + ", ".join(sorted(enabled)))
    else:
        print("\nenabled: none (core only)")
    print("enable with: make enable M=<module>")
    return 0


def apply_profile(root: Path) -> int:
    script = root / "bin" / "apply_profile.py"
    if not script.exists():
        return 0
    result = subprocess.run(
        [sys.executable, str(script), "--offline"],
        cwd=root,
        check=False,
    )
    if result.returncode != 0:
        print("warn: bin/apply_profile.py failed; run `make profile` manually", file=sys.stderr)
    return result.returncode


def module_has_agents(root: Path, name: str) -> bool:
    """Return whether a module brings agents that need a model binding.

    Args:
        root: Repository root.
        name: Module name.

    Returns:
        bool: True when the module declares at least one agent.
    """
    manifest = load_manifest(root / "modules" / name / "module.toml")
    return bool(manifest.get("agents"))


def refresh_models(root: Path, name: str) -> int:
    """Re-apply the active profile only when the module contains agents.

    Skill-only modules do not add model entries, so re-applying the profile
    would just overwrite the user's current model choice.

    Args:
        root: Repository root.
        name: Module name.

    Returns:
        int: Zero on success, or the profile subprocess exit code.
    """
    if module_has_agents(root, name):
        return apply_profile(root)
    print("models unchanged: skill-only module (run `make profile` to change models)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show the catalog and which modules are enabled")

    enable_parser = sub.add_parser("enable", help="copy a module's agents and skills")
    enable_parser.add_argument("name")
    enable_parser.add_argument(
        "--force", action="store_true", help="overwrite files this module created"
    )
    enable_parser.add_argument(
        "--with-hooks", action="store_true", help="also copy hooks into .opencode/plugins/"
    )
    enable_parser.add_argument("--dry-run", action="store_true")
    enable_parser.add_argument(
        "--no-apply", action="store_true", help="do not refresh opencode.json"
    )

    disable_parser = sub.add_parser("disable", help="remove files this module created")
    disable_parser.add_argument("name")
    disable_parser.add_argument("--dry-run", action="store_true")
    disable_parser.add_argument("--no-apply", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "list":
        return list_modules(root)

    validate_name(args.name)

    if args.command == "enable":
        code = enable(root, args.name, args.force, args.with_hooks, args.dry_run)
        if code == 0 and not args.dry_run and not args.no_apply:
            code = refresh_models(root, args.name)
        return code

    code = disable(root, args.name, args.dry_run)
    if code == 0 and not args.dry_run and not args.no_apply:
        code = refresh_models(root, args.name)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
