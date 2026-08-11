"""Testes do diagnóstico de submódulos.

O foco é a lógica que decide se um módulo está "reproduzível" e a leitura de
versão nos três layouts que os projetos usam (PEP 621, Poetry e setup.cfg).
As consultas ao git são exercitadas contra repositórios temporários reais.
"""

import subprocess
from pathlib import Path

import pytest

from mathe_core_mlib.io.submodules import (
    ModuleState,
    _read_version,
    _submodule_paths,
    collect_submodule_states,
    diagnose,
    find_repo_root,
    format_report,
    main,
)


def _git_init(path: Path) -> None:
    """Cria um repositório git mínimo com um commit."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "README.md").write_text("teste", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "inicial"], cwd=path, check=True)


def _state(**kwargs) -> ModuleState:
    """Monta um ModuleState com padrões saudáveis, sobrescritos por kwargs."""
    base = {
        "name": "lib",
        "path": Path("."),
        "recorded_commit": "abc123",
        "checkout_commit": "abc123",
        "branch": "main",
        "describe": "v1.0.0",
        "version": "1.0.0",
        "ahead": 0,
        "behind": 0,
        "is_dirty": False,
        "is_published": True,
    }
    return ModuleState(**{**base, **kwargs})


# ---------------------------------------------------------------------------
# Lógica de saúde do módulo
# ---------------------------------------------------------------------------


def test_healthy_when_everything_aligned() -> None:
    assert _state().is_healthy


def test_pointer_mismatch_is_not_healthy() -> None:
    estado = _state(checkout_commit="def456")

    assert not estado.pointer_matches
    assert not estado.is_healthy


@pytest.mark.parametrize(
    "campo",
    [
        {"is_dirty": True},
        {"behind": 3},
        {"is_published": False},
    ],
)
def test_unreproducible_states(campo: dict) -> None:
    assert not _state(**campo).is_healthy


def test_ahead_alone_is_still_healthy() -> None:
    # Estar à frente do remoto não impede reproduzir: o commit existe localmente
    # e a publicação é checada por is_published.
    assert _state(ahead=2, behind=0).is_healthy


def test_unknown_publication_does_not_fail_health() -> None:
    # None significa 'indeterminado', diferente de False ('nao publicado')
    assert _state(is_published=None).is_healthy


# ---------------------------------------------------------------------------
# Leitura de versão nos três layouts
# ---------------------------------------------------------------------------


def test_version_from_pep621(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "2.5.0"\n', encoding="utf-8")

    assert _read_version(tmp_path) == "2.5.0"


def test_version_from_poetry(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "x"\nversion = "3.16.0"\n', encoding="utf-8")

    assert _read_version(tmp_path) == "3.16.0"


def test_version_from_setup_cfg(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text("[metadata]\nname = gnpy\nversion = 3.0.0+thesis\n", encoding="utf-8")

    assert _read_version(tmp_path) == "3.0.0+thesis"


def test_version_unknown_without_declaration(tmp_path: Path) -> None:
    assert _read_version(tmp_path) == "?"


def test_version_survives_malformed_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("isto ][ nao e toml", encoding="utf-8")

    assert _read_version(tmp_path) == "?"


# ---------------------------------------------------------------------------
# Integração com git
# ---------------------------------------------------------------------------


def test_find_repo_root_outside_repository(tmp_path: Path) -> None:
    assert find_repo_root(tmp_path) is None


def test_find_repo_root_inside_repository(tmp_path: Path) -> None:
    _git_init(tmp_path)

    encontrado = find_repo_root(tmp_path)

    assert encontrado is not None
    assert encontrado.resolve() == tmp_path.resolve()


def test_collect_fails_fast_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        collect_submodule_states(tmp_path)


def test_repository_without_submodules_returns_empty(tmp_path: Path) -> None:
    _git_init(tmp_path)

    assert collect_submodule_states(tmp_path) == []
    assert _submodule_paths(tmp_path) == []


def test_submodule_paths_read_from_gitmodules(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitmodules").write_text(
        '[submodule "modules/a"]\n\tpath = modules/a\n\turl = ../a.git\n[submodule "libs/b"]\n\tpath = libs/b\n\turl = ../b.git\n',
        encoding="utf-8",
    )

    # o layout nao e presumido: vem do proprio .gitmodules
    assert _submodule_paths(tmp_path) == ["libs/b", "modules/a"]


def test_declared_but_uninitialized_submodule_is_flagged(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitmodules").write_text('[submodule "modules/a"]\n\tpath = modules/a\n\turl = ../a.git\n', encoding="utf-8")

    estados = collect_submodule_states(tmp_path)

    assert len(estados) == 1
    assert not estados[0].is_healthy
    assert "NAO INICIALIZADO" in format_report(estados, tmp_path)


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def test_report_states_when_there_are_no_submodules(tmp_path: Path) -> None:
    assert "Nenhum submodulo declarado" in format_report([], tmp_path)


def test_report_flags_divergent_pointer(tmp_path: Path) -> None:
    texto = format_report([_state(checkout_commit="def456")], tmp_path)

    assert "DIVERGENTE" in texto
    assert "ATENCAO" in texto


def test_report_confirms_healthy_set(tmp_path: Path) -> None:
    texto = format_report([_state()], tmp_path)

    assert "Todos os modulos estao em estado reproduzivel" in texto
    assert "ATENCAO" not in texto


def test_report_warns_about_unpublished_commit(tmp_path: Path) -> None:
    texto = format_report([_state(is_published=False)], tmp_path)

    assert "so existe nesta maquina" in texto


def test_report_mentions_fetch_hint_only_without_fetch(tmp_path: Path) -> None:
    assert "--fetch" in format_report([_state()], tmp_path, fetched=False)
    assert "--fetch" not in format_report([_state()], tmp_path, fetched=True)


# ---------------------------------------------------------------------------
# CLI: varredura de vários projetos
# ---------------------------------------------------------------------------


def test_diagnose_reports_error_instead_of_raising(tmp_path: Path) -> None:
    # Um projeto invalido nao pode interromper a varredura dos demais
    relatorio, esta_ok = diagnose(tmp_path)

    assert not esta_ok
    assert "ERRO" in relatorio


def test_diagnose_accepts_repository_without_submodules(tmp_path: Path) -> None:
    _git_init(tmp_path)

    relatorio, esta_ok = diagnose(tmp_path)

    assert esta_ok
    assert "Nenhum submodulo declarado" in relatorio


def test_main_scans_several_projects(tmp_path: Path, capsys) -> None:
    primeiro, segundo = tmp_path / "a", tmp_path / "b"
    _git_init(primeiro)
    _git_init(segundo)

    codigo = main([str(primeiro), str(segundo)])
    saida = capsys.readouterr().out

    assert codigo == 0
    assert "MODULOS DE a" in saida
    assert "MODULOS DE b" in saida


def test_main_fails_when_any_project_is_invalid(tmp_path: Path, capsys) -> None:
    valido, invalido = tmp_path / "ok", tmp_path / "sem_git"
    _git_init(valido)
    invalido.mkdir()

    codigo = main([str(valido), str(invalido)])
    saida = capsys.readouterr().out

    # o projeto valido ainda e reportado, mas o codigo de saida acusa a falha
    assert codigo == 1
    assert "MODULOS DE ok" in saida
    assert "ERRO" in saida
