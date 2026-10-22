from __future__ import annotations

import subprocess

import gate_marker


def git(repo, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def repo(tmp_path):
    git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("artifacts/\n")
    (tmp_path / "app.py").write_text("print('v1')\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_write_then_check_is_current(tmp_path):
    root = repo(tmp_path)
    gate_marker.write(root)
    assert gate_marker.check(root) == []


def test_missing_marker_is_a_failure(tmp_path):
    root = repo(tmp_path)
    problems = gate_marker.check(root)
    assert problems and "no gate marker" in problems[0]


def test_edit_after_gate_invalidates(tmp_path):
    root = repo(tmp_path)
    gate_marker.write(root)
    (root / "app.py").write_text("print('v2')\n")
    problems = gate_marker.check(root)
    assert any("working tree changed" in problem for problem in problems)


def test_staging_after_gate_stays_valid(tmp_path):
    root = repo(tmp_path)
    (root / "app.py").write_text("print('v2')\n")
    gate_marker.write(root)
    git(root, "add", "app.py")
    assert gate_marker.check(root) == []


def test_new_commit_invalidates(tmp_path):
    root = repo(tmp_path)
    gate_marker.write(root)
    (root / "new.py").write_text("x = 1\n")
    git(root, "add", "new.py")
    git(root, "commit", "-m", "second")
    problems = gate_marker.check(root)
    assert any("HEAD moved" in problem for problem in problems)


def test_ignored_artifact_does_not_change_the_hash(tmp_path):
    root = repo(tmp_path)
    gate_marker.write(root)
    assert (root / "artifacts" / "gate.json").exists()
    assert gate_marker.check(root) == []


def test_untracked_file_invalidates(tmp_path):
    root = repo(tmp_path)
    gate_marker.write(root)
    (root / "scratch.txt").write_text("not committed yet\n")
    problems = gate_marker.check(root)
    assert any("working tree changed" in problem for problem in problems)
