"""Testes da leitura de metadados de proveniência.

O contrato central é ser inofensivo: inspecionar um artefato não pode alterá-lo,
e um arquivo sem proveniência devolve None em vez de estourar — é justamente o
caso que a auditoria procura.
"""

import json
from pathlib import Path

import matplotlib
import polars as pl
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from mathe_core_mlib.io.files import save_json, save_parquet, save_pickle, save_yaml  # noqa: E402
from mathe_core_mlib.io.metadata_reader import find_identifying_fields, iter_artifacts, read_metadata  # noqa: E402
from mathe_core_mlib.style.utils import save_figure  # noqa: E402

VERSION = "9.9.9"


# ---------------------------------------------------------------------------
# Leitura por formato
# ---------------------------------------------------------------------------


def test_reads_json_metadata(tmp_path: Path) -> None:
    destino = tmp_path / "cfg.json"
    save_json({"span_km": 80}, destino, VERSION, software="Sim")

    meta = read_metadata(destino)

    assert meta is not None
    assert meta["software_version"] == VERSION
    assert meta["software"] == "Sim"


def test_reads_yaml_metadata(tmp_path: Path) -> None:
    destino = tmp_path / "cfg.yaml"
    save_yaml({"span_km": 80}, destino, VERSION)

    assert read_metadata(destino)["software_version"] == VERSION


def test_reads_parquet_metadata(tmp_path: Path) -> None:
    destino = tmp_path / "res.parquet"
    save_parquet(pl.DataFrame({"a": [1]}), destino, VERSION, extra_meta={"seed": 7})

    meta = read_metadata(destino)

    assert meta["software_version"] == VERSION
    assert meta["seed"] == "7"
    # a chave interna do Polars nao e proveniencia
    assert "ARROW:schema" not in meta


def test_reads_pdf_info_dict(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    save_figure(fig, tmp_path / "grafico", VERSION, software="Sim")
    plt.close(fig)

    meta = read_metadata(tmp_path / "grafico.pdf")

    assert meta["Title"] == "grafico"
    assert VERSION in meta["Creator"]


def test_sidecar_is_metadata_in_full(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    save_figure(fig, tmp_path / "grafico", VERSION, software="Sim")
    plt.close(fig)

    # o companheiro nao aninha em '_meta': ele proprio e o registro
    meta = read_metadata(tmp_path / "grafico.meta.json")

    assert meta["software_version"] == VERSION
    assert meta["files"] == ["grafico.pdf"]


# ---------------------------------------------------------------------------
# Ausência de proveniência (o caso de auditoria)
# ---------------------------------------------------------------------------


def test_file_without_provenance_returns_none(tmp_path: Path) -> None:
    destino = tmp_path / "antigo.json"
    destino.write_text(json.dumps({"dados": 1}), encoding="utf-8")

    assert read_metadata(destino) is None


def test_parquet_without_provenance_returns_none(tmp_path: Path) -> None:
    destino = tmp_path / "antigo.parquet"
    pl.DataFrame({"a": [1]}).write_parquet(destino)

    assert read_metadata(destino) is None


def test_json_that_is_not_a_mapping_returns_none(tmp_path: Path) -> None:
    destino = tmp_path / "lista.json"
    destino.write_text("[1, 2, 3]", encoding="utf-8")

    assert read_metadata(destino) is None


# ---------------------------------------------------------------------------
# Segurança e contratos
# ---------------------------------------------------------------------------


def test_pickle_requires_explicit_authorization(tmp_path: Path) -> None:
    destino = tmp_path / "estado.pkl"
    save_pickle({"x": 1}, destino, VERSION)

    # desserializar pickle executa codigo: exige opt-in
    with pytest.raises(ValueError, match="allow_pickle"):
        read_metadata(destino)

    assert read_metadata(destino, allow_pickle=True)["software_version"] == VERSION


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    destino = tmp_path / "nota.txt"
    destino.write_text("oi", encoding="utf-8")

    with pytest.raises(ValueError, match="nao suportada"):
        read_metadata(destino)


def test_missing_file_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_metadata(tmp_path / "nao_existe.json")


def test_reading_does_not_modify_the_artifact(tmp_path: Path) -> None:
    destino = tmp_path / "res.parquet"
    save_parquet(pl.DataFrame({"a": [1, 2]}), destino, VERSION)

    antes_bytes = destino.read_bytes()
    antes_mtime = destino.stat().st_mtime_ns

    read_metadata(destino)

    assert destino.read_bytes() == antes_bytes
    assert destino.stat().st_mtime_ns == antes_mtime


# ---------------------------------------------------------------------------
# Varredura de pastas
# ---------------------------------------------------------------------------


def test_iter_artifacts_finds_supported_files(tmp_path: Path) -> None:
    save_json({"a": 1}, tmp_path / "a.json", VERSION)
    save_parquet(pl.DataFrame({"a": [1]}), tmp_path / "b.parquet", VERSION)
    (tmp_path / "ignorado.txt").write_text("x", encoding="utf-8")

    nomes = [p.name for p in iter_artifacts(tmp_path)]

    assert nomes == ["a.json", "b.parquet"]


def test_iter_artifacts_recurses_by_default(tmp_path: Path) -> None:
    save_json({"a": 1}, tmp_path / "sub" / "profundo.json", VERSION)

    assert [p.name for p in iter_artifacts(tmp_path)] == ["profundo.json"]
    assert list(iter_artifacts(tmp_path, recursive=False)) == []


def test_iter_artifacts_accepts_a_single_file(tmp_path: Path) -> None:
    destino = tmp_path / "a.json"
    save_json({"a": 1}, destino, VERSION)

    assert list(iter_artifacts(destino)) == [destino]


def test_iter_artifacts_missing_path_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(iter_artifacts(tmp_path / "nao_existe"))


# ---------------------------------------------------------------------------
# Revisão de privacidade antes de publicar
# ---------------------------------------------------------------------------


def test_hostname_is_flagged_as_identifying() -> None:
    achados = find_identifying_fields({"hostname": "Yoga7iMatheus", "software": "Sim"})

    assert achados == {"hostname": "nome da maquina"}


@pytest.mark.parametrize(
    "valor",
    [
        r"C:\Dev_Local\doc-mathe\dados.parquet",
        "C:/Users/joao/dados.parquet",
        "/home/joao/dados.parquet",
        "/Users/joao/dados.parquet",
    ],
)
def test_absolute_paths_are_flagged(valor: str) -> None:
    assert find_identifying_fields({"entrada": valor}) == {"entrada": "caminho absoluto"}


def test_neutral_fields_are_not_flagged() -> None:
    neutro = {
        "software": "MGNPyEONv3",
        "software_version": "3.17.0",
        "created_at": "2026-08-11T12:00:00+00:00",
        "git_commit": "b5535f1",
        "input_file": "ga_sim_input_otm.parquet",
        "n_scenarios": 9,
    }

    assert find_identifying_fields(neutro) == {}


def test_privacy_review_on_a_real_artifact(tmp_path: Path) -> None:
    destino = tmp_path / "res.parquet"
    save_parquet(pl.DataFrame({"a": [1]}), destino, VERSION, software="Sim")

    achados = find_identifying_fields(read_metadata(destino))

    # o bloco padrao carrega hostname, e nada mais identificavel
    assert list(achados) == ["hostname"]
