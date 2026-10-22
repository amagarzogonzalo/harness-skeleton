from __future__ import annotations

import json

import check_modules


def write_state(root, name, role="review"):
    state = root / "modules" / ".enabled.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(
        json.dumps(
            {
                "modules": {
                    name: {
                        "name": name,
                        "role": role,
                        "agents": [],
                        "files": [],
                    }
                }
            }
        )
    )


def test_no_modules_is_not_a_failure(tmp_path, capsys):
    assert check_modules.main([str(tmp_path)]) == 0
    assert "no modules enabled" in capsys.readouterr().out


def test_agents_only_module_is_skipped(tmp_path, capsys):
    write_state(tmp_path, "review-universal")
    (tmp_path / "modules" / "review-universal").mkdir(parents=True)
    (tmp_path / "modules" / "review-universal" / "module.toml").write_text(
        'name = "review-universal"\ncheck = ""\n'
    )
    assert check_modules.main([str(tmp_path)]) == 0
    assert "agents and skills only" in capsys.readouterr().out


def test_declared_missing_check_is_a_failure(tmp_path, capsys):
    write_state(tmp_path, "lang-python")
    (tmp_path / "modules" / "lang-python").mkdir(parents=True)
    (tmp_path / "modules" / "lang-python" / "module.toml").write_text(
        'name = "lang-python"\ncheck = "check.sh"\n'
    )
    assert check_modules.main([str(tmp_path)]) == 1
    assert "declared check is missing" in capsys.readouterr().err


def test_missing_manifest_is_a_failure(tmp_path, capsys):
    write_state(tmp_path, "ghost")
    assert check_modules.main([str(tmp_path)]) == 1
    assert "module.toml is missing" in capsys.readouterr().err
