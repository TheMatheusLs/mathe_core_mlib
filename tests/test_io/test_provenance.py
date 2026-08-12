"""Testes da construção de metadados de proveniência.

A regra da lib é que nenhum artefato vá para o disco sem registrar quem o gerou.
Estes testes fixam o contrato mínimo do bloco de metadados e a serialização
str -> str exigida pelo Parquet/Arrow.
"""

import json
from datetime import datetime

import pytest

from mathe_core_mlib.io import provenance
from mathe_core_mlib.io.provenance import as_string_mapping, build_metadata, command_line


@pytest.fixture(autouse=True)
def _clear_git_cache() -> None:
    """Zera o cache de git entre testes para não vazar estado de um caso a outro."""
    provenance._git_state.cache_clear()


def test_metadata_has_minimum_contract() -> None:
    meta = build_metadata("3.15.1", include_git=False)

    assert meta["software_version"] == "3.15.1"
    assert set(meta) >= {"created_at", "software_version", "python_version", "platform"}


def test_created_at_is_utc_iso8601() -> None:
    meta = build_metadata("1.0.0", include_git=False)

    parsed = datetime.fromisoformat(meta["created_at"])

    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_software_is_omitted_when_not_given() -> None:
    assert "software" not in build_metadata("1.0.0", include_git=False)
    assert build_metadata("1.0.0", software="Sim", include_git=False)["software"] == "Sim"


def test_extra_fields_are_merged() -> None:
    meta = build_metadata("1.0.0", extra={"seed": 42, "scenario": "parabolic"}, include_git=False)

    assert meta["seed"] == 42
    assert meta["scenario"] == "parabolic"


@pytest.mark.parametrize("version_invalida", ["", "   ", "\n"])
def test_blank_version_is_rejected(version_invalida: str) -> None:
    with pytest.raises(ValueError):
        build_metadata(version_invalida)


@pytest.mark.parametrize("version_invalida", [1.0, None, 315, ["1.0"]])
def test_non_string_version_is_rejected(version_invalida) -> None:
    with pytest.raises(TypeError):
        build_metadata(version_invalida)


def test_git_state_is_cached_across_calls() -> None:
    build_metadata("1.0.0")
    build_metadata("1.0.0")
    build_metadata("1.0.0")

    # 3 chamadas, no máximo 1 consulta real ao git: salvar em laço não pode
    # disparar um subprocesso por arquivo
    assert provenance._git_state.cache_info().misses <= 1


def test_string_mapping_keeps_strings_raw_and_json_encodes_the_rest() -> None:
    achatado = as_string_mapping({"software": "Sim", "git_dirty": False, "seed": 42, "tags": ["a", "b"]})

    # str não pode ganhar aspas extras, senão o valor fica ilegível no Parquet
    assert achatado["software"] == "Sim"
    assert achatado["git_dirty"] == "false"
    assert achatado["seed"] == "42"
    assert json.loads(achatado["tags"]) == ["a", "b"]


def test_string_mapping_produces_only_strings() -> None:
    achatado = as_string_mapping(build_metadata("1.0.0", extra={"seed": 1}, include_git=False))

    assert all(isinstance(k, str) and isinstance(v, str) for k, v in achatado.items())


def test_command_line_returns_string() -> None:
    assert isinstance(command_line(), str)


# ---------------------------------------------------------------------------
# Hostname e o opt-out de privacidade
# ---------------------------------------------------------------------------


def test_hostname_is_recorded_by_default() -> None:
    import platform

    meta = build_metadata("1.0.0", include_git=False)

    assert meta["hostname"] == platform.node()


def test_hostname_is_omitted_when_opted_out(monkeypatch) -> None:
    # Nome de maquina costuma conter o nome da pessoa: precisa ser suprimivel
    # antes de publicar dados como material suplementar.
    monkeypatch.setenv(provenance.NO_HOSTNAME_ENV_VAR, "1")

    assert "hostname" not in build_metadata("1.0.0", include_git=False)


def test_opt_out_only_triggers_on_exact_value(monkeypatch) -> None:
    monkeypatch.setenv(provenance.NO_HOSTNAME_ENV_VAR, "0")

    assert "hostname" in build_metadata("1.0.0", include_git=False)
