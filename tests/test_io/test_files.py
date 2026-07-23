"""Testes das funções de IO de arquivos.

O contrato Fail-Fast da lib exige que ler um arquivo inexistente estoure
FileNotFoundError imediatamente (e não devolva None/vazio silenciosamente), e
que salvar crie a árvore de diretórios sozinho — o chamador (simulador) não
gerencia pastas intermediárias.
"""

import hashlib
from pathlib import Path

import polars as pl
import pytest

from mathe_core_mlib.io.files import (
    calculate_file_hash,
    load_csv,
    load_json,
    load_parquet,
    load_pickle,
    load_yaml,
    save_json,
    save_pickle,
    save_yaml,
)


def test_json_roundtrip_preserves_data_and_accents(tmp_path: Path) -> None:
    data = {"potência": 1.5, "canais": [1, 2, 3], "ativo": True}
    destino = tmp_path / "config.json"

    save_json(data, destino)

    assert load_json(destino) == data
    # ensure_ascii=False: acentos gravados literalmente, não como \uXXXX
    assert "potência" in destino.read_text(encoding="utf-8")


def test_yaml_roundtrip_preserves_data(tmp_path: Path) -> None:
    data = {"span_km": 80, "amplificadores": {"tipo": "EDFA", "nf_db": 5.5}}
    destino = tmp_path / "setup.yaml"

    save_yaml(data, destino)

    assert load_yaml(destino) == data


def test_pickle_roundtrip_preserves_objects(tmp_path: Path) -> None:
    data = {"matriz": [[1, 2], [3, 4]], "tupla": (1, "a")}
    destino = tmp_path / "estado.pkl"

    save_pickle(data, destino)

    assert load_pickle(destino) == data


@pytest.mark.parametrize(
    ("save_func", "nome"),
    [(save_json, "a/b/c/dados.json"), (save_yaml, "x/y/dados.yaml"), (save_pickle, "p/q/dados.pkl")],
)
def test_save_creates_missing_parent_directories(tmp_path: Path, save_func, nome: str) -> None:
    destino = tmp_path / nome

    save_func({"k": 1}, destino)

    assert destino.is_file()


@pytest.mark.parametrize("load_func", [load_json, load_yaml, load_pickle, load_csv, load_parquet])
def test_load_missing_file_fails_fast(tmp_path: Path, load_func) -> None:
    with pytest.raises(FileNotFoundError):
        load_func(tmp_path / "nao_existe.ext")


def test_load_csv_returns_polars_dataframe(tmp_path: Path) -> None:
    origem = tmp_path / "resultados.csv"
    origem.write_text("osnr,ber\n20.5,1e-3\n21.0,5e-4\n", encoding="utf-8")

    df = load_csv(origem)

    assert isinstance(df, pl.DataFrame)
    assert df.shape == (2, 2)
    assert df.columns == ["osnr", "ber"]


def test_load_parquet_returns_polars_dataframe(tmp_path: Path) -> None:
    origem = tmp_path / "resultados.parquet"
    pl.DataFrame({"osnr": [20.5, 21.0], "ber": [1e-3, 5e-4]}).write_parquet(origem)

    df = load_parquet(origem)

    assert df.shape == (2, 2)
    assert df["osnr"].to_list() == [20.5, 21.0]


def test_calculate_file_hash_matches_hashlib(tmp_path: Path) -> None:
    arquivo = tmp_path / "dados.bin"
    conteudo = b"conteudo binario de teste" * 1000  # força leitura em varios chunks
    arquivo.write_bytes(conteudo)

    assert calculate_file_hash(arquivo) == hashlib.sha256(conteudo).hexdigest()
    assert calculate_file_hash(arquivo, algorithm="md5") == hashlib.md5(conteudo).hexdigest()


def test_calculate_file_hash_is_stable_across_chunk_sizes(tmp_path: Path) -> None:
    arquivo = tmp_path / "dados.bin"
    arquivo.write_bytes(b"x" * 20_000)

    assert calculate_file_hash(arquivo, chunk_size=1) == calculate_file_hash(arquivo, chunk_size=65_536)


def test_calculate_file_hash_missing_file_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        calculate_file_hash(tmp_path / "nao_existe.bin")
