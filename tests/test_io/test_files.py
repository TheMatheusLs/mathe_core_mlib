"""Testes das funções de IO de arquivos.

O contrato Fail-Fast da lib exige que ler um arquivo inexistente estoure
FileNotFoundError imediatamente (e não devolva None/vazio silenciosamente), e
que salvar crie a árvore de diretórios sozinho — o chamador (simulador) não
gerencia pastas intermediárias.

A partir da v2.3.0 vale um segundo contrato: nenhum artefato é gravado sem
proveniência. 'version' é obrigatório em todo save_*, e o bloco de metadados é
removido na leitura para que o round-trip continue devolvendo só os dados.
"""

import hashlib
import pickle
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
    save_parquet,
    save_pickle,
    save_yaml,
)
from mathe_core_mlib.io.provenance import DATA_KEY, META_KEY

VERSION = "9.9.9"


# ---------------------------------------------------------------------------
# Round-trip: o _meta gravado não pode vazar para o chamador
# ---------------------------------------------------------------------------


def test_json_roundtrip_preserves_data_and_accents(tmp_path: Path) -> None:
    data = {"potência": 1.5, "canais": [1, 2, 3], "ativo": True}
    destino = tmp_path / "config.json"

    save_json(data, destino, VERSION)

    assert load_json(destino) == data
    # ensure_ascii=False: acentos gravados literalmente, não como \uXXXX
    assert "potência" in destino.read_text(encoding="utf-8")


def test_yaml_roundtrip_preserves_data(tmp_path: Path) -> None:
    data = {"span_km": 80, "amplificadores": {"tipo": "EDFA", "nf_db": 5.5}}
    destino = tmp_path / "setup.yaml"

    save_yaml(data, destino, VERSION)

    assert load_yaml(destino) == data


def test_pickle_roundtrip_preserves_objects(tmp_path: Path) -> None:
    data = {"matriz": [[1, 2], [3, 4]], "tupla": (1, "a")}
    destino = tmp_path / "estado.pkl"

    save_pickle(data, destino, VERSION)

    assert load_pickle(destino) == data


def test_parquet_roundtrip_preserves_dataframe(tmp_path: Path) -> None:
    df = pl.DataFrame({"gsnr_db": [18.2, 19.4], "banda": ["C", "L"]})
    destino = tmp_path / "resultados.parquet"

    save_parquet(df, destino, VERSION)

    # metadados vão no schema, não em colunas extras
    assert load_parquet(destino).equals(df)


# ---------------------------------------------------------------------------
# Proveniência obrigatória
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("save_func", "payload", "nome"),
    [
        (save_json, {"k": 1}, "dados.json"),
        (save_yaml, {"k": 1}, "dados.yaml"),
        (save_pickle, {"k": 1}, "dados.pkl"),
        (save_parquet, pl.DataFrame({"k": [1]}), "dados.parquet"),
    ],
)
def test_save_requires_version(tmp_path: Path, save_func, payload, nome: str) -> None:
    # Esquecer a versão deve falhar na chamada, não gerar artefato sem proveniência
    with pytest.raises(TypeError):
        save_func(payload, tmp_path / nome)


@pytest.mark.parametrize("version_invalida", ["", "   "])
def test_save_rejects_blank_version(tmp_path: Path, version_invalida: str) -> None:
    with pytest.raises(ValueError):
        save_json({"k": 1}, tmp_path / "dados.json", version_invalida)


def test_save_json_writes_meta_block(tmp_path: Path) -> None:
    destino = tmp_path / "config.json"

    save_json({"k": 1}, destino, VERSION, software="MeuSim", extra_meta={"seed": 42})

    _, meta = load_json(destino, return_meta=True)

    assert meta is not None
    assert meta["software_version"] == VERSION
    assert meta["software"] == "MeuSim"
    assert meta["seed"] == 42
    assert meta["created_at"].endswith("+00:00")  # UTC explícito, ISO 8601


def test_save_parquet_writes_meta_into_schema(tmp_path: Path) -> None:
    destino = tmp_path / "resultados.parquet"

    save_parquet(pl.DataFrame({"k": [1]}), destino, VERSION, software="MeuSim", extra_meta={"seed": 7})

    _, meta = load_parquet(destino, return_meta=True)

    # metadados Arrow são sempre str -> str
    assert meta["software_version"] == VERSION
    assert meta["software"] == "MeuSim"
    assert meta["seed"] == "7"
    # o schema serializado do Polars não é proveniência e não deve vazar
    assert "ARROW:schema" not in meta


def test_save_pickle_writes_envelope(tmp_path: Path) -> None:
    destino = tmp_path / "estado.pkl"

    save_pickle([1, 2, 3], destino, VERSION)

    with open(destino, "rb") as f:
        cru = pickle.load(f)

    assert set(cru) == {META_KEY, DATA_KEY}
    assert cru[DATA_KEY] == [1, 2, 3]


def test_load_pickle_reads_legacy_files_without_envelope(tmp_path: Path) -> None:
    # Arquivos gravados antes do envelope precisam continuar legíveis
    destino = tmp_path / "antigo.pkl"
    with open(destino, "wb") as f:
        pickle.dump({"resultado": 3.14}, f)

    dados, meta = load_pickle(destino, return_meta=True)

    assert dados == {"resultado": 3.14}
    assert meta is None


def test_save_does_not_mutate_caller_dict(tmp_path: Path) -> None:
    data = {"k": 1}

    save_json(data, tmp_path / "a.json", VERSION)
    save_yaml(data, tmp_path / "b.yaml", VERSION)

    assert data == {"k": 1}


def test_load_without_return_meta_hides_provenance(tmp_path: Path) -> None:
    destino = tmp_path / "config.json"

    save_json({"k": 1}, destino, VERSION)

    assert META_KEY not in load_json(destino)


# ---------------------------------------------------------------------------
# Contratos pré-existentes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("save_func", "payload", "nome"),
    [
        (save_json, {"k": 1}, "a/b/c/dados.json"),
        (save_yaml, {"k": 1}, "x/y/dados.yaml"),
        (save_pickle, {"k": 1}, "p/q/dados.pkl"),
        (save_parquet, pl.DataFrame({"k": [1]}), "r/s/dados.parquet"),
    ],
)
def test_save_creates_missing_parent_directories(tmp_path: Path, save_func, payload, nome: str) -> None:
    destino = tmp_path / nome

    save_func(payload, destino, VERSION)

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
