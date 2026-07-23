"""Testes do gatekeeper de reprodutibilidade.

`enforce_clean_environment` é a última barreira antes de horas de simulação:
se uma lib local estiver com alterações não commitadas, o resultado não é
reprodutível e a execução deve ABORTAR (strict). O snapshot é gerado via `uv`,
então aqui ele é simulado — os testes checam o contrato, não a presença do uv.
"""

import json
import subprocess
from pathlib import Path

import pytest

from mathe_core_mlib.io.environment import _get_git_info, enforce_clean_environment, snapshot_environment

UV_PACKAGES = [
    {"name": "numpy", "version": "2.4.3"},
    {"name": "mathe-core-mlib", "version": "2.1.3", "editable_project_location": "."},
]


def _write_snapshot(pasta: Path, data: dict) -> Path:
    arquivo = pasta / "env_snapshot.json"
    arquivo.write_text(json.dumps(data), encoding="utf-8")
    return arquivo


# --------------------------------------------------------------------------- #
# _get_git_info
# --------------------------------------------------------------------------- #


def test_git_info_on_non_repo_returns_unknown_defaults(tmp_path: Path) -> None:
    info = _get_git_info(tmp_path)

    assert info["git_commit"] == "Unknown"
    assert info["git_branch"] == "Unknown"
    assert info["is_dirty"] is False
    assert info["path"] == str(tmp_path)


def test_git_info_reads_real_repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Teste"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("v1", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "commit inicial"], cwd=tmp_path, check=True)

    info = _get_git_info(tmp_path)

    assert info["git_commit"] != "Unknown"
    assert info["last_commit_msg"] == "commit inicial"
    assert info["git_tag"] is None  # sem tag exata
    assert info["is_dirty"] is False

    # Agora suja o repo: precisa ser detectado e listar o arquivo alterado.
    (tmp_path / "a.txt").write_text("v2", encoding="utf-8")
    sujo = _get_git_info(tmp_path)

    assert sujo["is_dirty"] is True
    assert any("a.txt" in f for f in sujo["dirty_files"])


# --------------------------------------------------------------------------- #
# snapshot_environment
# --------------------------------------------------------------------------- #


def test_snapshot_separates_editable_libs_from_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: json.dumps(UV_PACKAGES).encode("utf-8"))

    saida = snapshot_environment(tmp_path)

    assert saida == tmp_path / "env_snapshot.json"
    data = json.loads(saida.read_text(encoding="utf-8"))
    assert data["dependencies"] == {"numpy": "2.4.3"}
    assert "mathe-core-mlib" in data["local_libraries"]
    assert data["local_libraries"]["mathe-core-mlib"]["version"] == "2.1.3"
    assert "python_version" in data and "platform" in data


def test_snapshot_returns_none_when_uv_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def sem_uv(*args, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(subprocess, "check_output", sem_uv)

    assert snapshot_environment(tmp_path) is None
    assert not (tmp_path / "env_snapshot.json").exists()


# --------------------------------------------------------------------------- #
# enforce_clean_environment
# --------------------------------------------------------------------------- #


def test_enforce_without_snapshot_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="snapshot_environment"):
        enforce_clean_environment(tmp_path)


def test_enforce_with_corrupted_snapshot_raises(tmp_path: Path) -> None:
    (tmp_path / "env_snapshot.json").write_text("{ isso nao e json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        enforce_clean_environment(tmp_path)


def test_enforce_passes_on_clean_environment(tmp_path: Path) -> None:
    _write_snapshot(
        tmp_path,
        {
            "simulator_git": {"is_dirty": False},
            "local_libraries": {"mathe-core-mlib": {"is_dirty": False}},
        },
    )

    enforce_clean_environment(tmp_path, strict=True)  # não deve levantar nada


def test_enforce_aborts_when_local_library_is_dirty(tmp_path: Path) -> None:
    _write_snapshot(
        tmp_path,
        {
            "simulator_git": {"is_dirty": False},
            "local_libraries": {"mathe-core-mlib": {"is_dirty": True, "dirty_files": [" M src/x.py"]}},
        },
    )

    with pytest.raises(RuntimeError, match="1 biblioteca"):
        enforce_clean_environment(tmp_path, strict=True)


def test_enforce_only_warns_when_not_strict(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _write_snapshot(
        tmp_path,
        {
            "simulator_git": {"is_dirty": False},
            "local_libraries": {"mathe-core-mlib": {"is_dirty": True, "dirty_files": [" M src/x.py"]}},
        },
    )

    enforce_clean_environment(tmp_path, strict=False)  # avisa, mas deixa passar

    assert "CRITICAL" in capsys.readouterr().out


def test_dirty_simulator_warns_but_does_not_abort(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    # Simulador sujo é só aviso: quem bloqueia são as libs locais.
    _write_snapshot(
        tmp_path,
        {
            "simulator_git": {"is_dirty": True, "dirty_files": [" M run.py"]},
            "local_libraries": {},
        },
    )

    enforce_clean_environment(tmp_path, strict=True)

    saida = capsys.readouterr().out
    assert "WARNING" in saida
    assert "run.py" in saida
