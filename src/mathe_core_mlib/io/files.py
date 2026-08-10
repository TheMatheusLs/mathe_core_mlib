"""
Leitura e escrita de arquivos com proveniência obrigatória.

Toda função ``save_*`` deste módulo exige o argumento ``version`` e grava um
bloco de metadados junto ao artefato — não há forma de salvar sem proveniência.
Onde o formato tem um lugar natural para isso (JSON, YAML, Pickle, Parquet), o
bloco vai dentro do próprio arquivo; ele é removido de volta na leitura, de modo
que ``load_x(save_x(d)) == d`` continua valendo para o chamador.

Ver :mod:`mathe_core_mlib.io.provenance` para o conteúdo do bloco.
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from mathe_core_mlib.io.provenance import DATA_KEY, META_KEY, as_string_mapping, build_metadata


def load_json(file_path: Path, *, return_meta: bool = False) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Carrega um arquivo JSON e retorna um dicionário, sem o bloco de proveniência.

    Parameters
    ----------
    file_path : Path
        Caminho do arquivo JSON.
    return_meta : bool, optional
        Quando ``True``, retorna também o bloco ``_meta`` gravado pelo
        :func:`save_json` (``None`` se o arquivo não tiver um).

    Returns
    -------
    dict[str, Any] or tuple[dict[str, Any], dict[str, Any] | None]
        Os dados sem a chave ``_meta``; com ``return_meta=True``, o par
        ``(dados, metadados)``.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.

    Examples
    --------
    >>> from pathlib import Path
    >>> save_json({"span_km": 80}, Path("cfg.json"), version="1.0.0")  # doctest: +SKIP
    >>> load_json(Path("cfg.json"))  # doctest: +SKIP
    {'span_km': 80}
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Remove a proveniência para o chamador enxergar só os dados que ele gravou
    metadata = data.pop(META_KEY, None) if isinstance(data, dict) else None

    return (data, metadata) if return_meta else data


def save_json(
    data: dict[str, Any],
    file_path: Path,
    version: str,
    *,
    software: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    indent: int = 4,
) -> None:
    """
    Salva um dicionário em um arquivo JSON, com proveniência na chave ``_meta``.

    Parameters
    ----------
    data : dict[str, Any]
        Dados a persistir. Não é modificado (o ``_meta`` entra em uma cópia).
    file_path : Path
        Caminho de destino; diretórios pai são criados automaticamente.
    version : str
        Versão do software que gerou o artefato. Obrigatório.
    software : str or None, optional
        Nome do projeto gerador (ex.: ``"MGNPyEONv3"``).
    extra_meta : dict[str, Any] or None, optional
        Campos extras de proveniência (ex.: ``{"seed": 42}``).
    indent : int, optional
        Indentação do JSON. Padrão 4.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for vazio.

    Examples
    --------
    >>> from pathlib import Path
    >>> save_json({"span_km": 80}, Path("cfg.json"), version="1.0.0")  # doctest: +SKIP
    """
    metadata = build_metadata(version, software=software, extra=extra_meta)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # _meta primeiro para ficar visível ao abrir o arquivo; cópia rasa preserva o dict do chamador
    payload = {META_KEY: metadata, **data}

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent, ensure_ascii=False)


def load_yaml(file_path: Path, *, return_meta: bool = False) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Carrega um arquivo YAML e retorna um dicionário, sem o bloco de proveniência.

    Parameters
    ----------
    file_path : Path
        Caminho do arquivo YAML.
    return_meta : bool, optional
        Quando ``True``, retorna também o bloco ``_meta`` (``None`` se ausente).

    Returns
    -------
    dict[str, Any] or tuple[dict[str, Any], dict[str, Any] | None]
        Os dados sem a chave ``_meta``; com ``return_meta=True``, o par
        ``(dados, metadados)``.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo YAML não encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    metadata = data.pop(META_KEY, None) if isinstance(data, dict) else None

    return (data, metadata) if return_meta else data


def save_yaml(
    data: dict[str, Any],
    file_path: Path,
    version: str,
    *,
    software: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """
    Salva um dicionário em arquivo YAML, com proveniência na chave ``_meta``.

    Parameters
    ----------
    data : dict[str, Any]
        Dados a persistir. Não é modificado.
    file_path : Path
        Caminho de destino; diretórios pai são criados automaticamente.
    version : str
        Versão do software que gerou o artefato. Obrigatório.
    software : str or None, optional
        Nome do projeto gerador.
    extra_meta : dict[str, Any] or None, optional
        Campos extras de proveniência.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for vazio.
    """
    metadata = build_metadata(version, software=software, extra=extra_meta)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {META_KEY: metadata, **data}

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def load_pickle(file_path: Path, *, return_meta: bool = False) -> Any:
    """
    Carrega um objeto de um arquivo .pkl, desembrulhando o envelope de proveniência.

    Arquivos gravados antes da adoção do envelope (sem ``_meta``/``_data``) são
    devolvidos como estão, com metadados ``None``.

    Parameters
    ----------
    file_path : Path
        Caminho do arquivo ``.pkl``.
    return_meta : bool, optional
        Quando ``True``, retorna o par ``(objeto, metadados)``.

    Returns
    -------
    Any
        O objeto original; com ``return_meta=True``, a tupla
        ``(objeto, metadados | None)``.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo Pickle não encontrado: {file_path}")

    with open(file_path, "rb") as f:
        raw = pickle.load(f)

    # Envelope reconhecido só quando tem exatamente as duas chaves reservadas,
    # para não confundir com um dict de dados que por acaso use '_data'
    if isinstance(raw, dict) and set(raw) == {META_KEY, DATA_KEY}:
        data, metadata = raw[DATA_KEY], raw[META_KEY]
    else:
        data, metadata = raw, None

    return (data, metadata) if return_meta else data


def save_pickle(
    data: Any,
    file_path: Path,
    version: str,
    *,
    software: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """
    Salva qualquer objeto Python em um arquivo .pkl, dentro de um envelope com proveniência.

    O arquivo contém ``{"_meta": ..., "_data": <objeto>}``; :func:`load_pickle`
    desfaz o envelope automaticamente.

    Parameters
    ----------
    data : Any
        Objeto a serializar.
    file_path : Path
        Caminho de destino; diretórios pai são criados automaticamente.
    version : str
        Versão do software que gerou o artefato. Obrigatório.
    software : str or None, optional
        Nome do projeto gerador.
    extra_meta : dict[str, Any] or None, optional
        Campos extras de proveniência.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for vazio.
    """
    metadata = build_metadata(version, software=software, extra=extra_meta)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        pickle.dump({META_KEY: metadata, DATA_KEY: data}, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_csv(file_path: Path, **kwargs) -> pl.DataFrame:
    """
    Carrega um arquivo CSV em um DataFrame do Polars.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")

    return pl.read_csv(file_path, **kwargs)


def load_parquet(file_path: Path, *, return_meta: bool = False, **kwargs) -> pl.DataFrame | tuple[pl.DataFrame, dict[str, str]]:
    """
    Carrega um arquivo Parquet em um DataFrame do Polars.

    A proveniência vive no schema do arquivo (metadados Arrow), não em colunas,
    então o DataFrame retornado já contém apenas os dados.

    Parameters
    ----------
    file_path : Path
        Caminho do arquivo Parquet.
    return_meta : bool, optional
        Quando ``True``, retorna também os metadados de schema como
        ``dict[str, str]`` (vazio se o arquivo não tiver nenhum).
    **kwargs
        Repassados a :func:`polars.read_parquet`.

    Returns
    -------
    pl.DataFrame or tuple[pl.DataFrame, dict[str, str]]
        O DataFrame; com ``return_meta=True``, o par ``(df, metadados)``.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo Parquet não encontrado: {file_path}")

    df = pl.read_parquet(file_path, **kwargs)

    if not return_meta:
        return df

    # 'ARROW:schema' é o schema serializado que o Polars grava sozinho; não é
    # proveniência e só polui o retorno para o chamador
    metadata = {key: value for key, value in pl.read_parquet_metadata(file_path).items() if key != "ARROW:schema"}

    return df, metadata


def save_parquet(
    df: pl.DataFrame,
    file_path: Path,
    version: str,
    *,
    software: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    compression: str = "zstd",
    compression_level: int | None = None,
    **kwargs,
) -> None:
    """
    Persiste um DataFrame em Parquet comprimido, com proveniência no schema.

    Os metadados vão para o key-value store do arquivo Parquet (schema Arrow) e
    **não** viram colunas extras, de modo que não afetam agregações nem o tamanho
    por linha.

    Parameters
    ----------
    df : pl.DataFrame
        Dados a persistir.
    file_path : Path
        Caminho de destino; diretórios pai são criados automaticamente.
    version : str
        Versão do software que gerou o artefato. Obrigatório.
    software : str or None, optional
        Nome do projeto gerador.
    extra_meta : dict[str, Any] or None, optional
        Campos extras de proveniência (ex.: ``{"scenario": "parabolic", "seed": 7}``).
        Valores não-string são serializados em JSON.
    compression : str, optional
        Codec de compressão. Padrão ``"zstd"`` (melhor razão/velocidade para os
        resultados numéricos destas simulações).
    compression_level : int or None, optional
        Nível do codec; ``None`` usa o padrão do Polars.
    **kwargs
        Repassados a :meth:`polars.DataFrame.write_parquet`.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for vazio.

    Examples
    --------
    >>> import polars as pl
    >>> from pathlib import Path
    >>> df = pl.DataFrame({"gsnr_db": [18.2, 19.4]})
    >>> save_parquet(df, Path("res.parquet"), version="1.0.0")  # doctest: +SKIP
    """
    metadata = build_metadata(version, software=software, extra=extra_meta)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    df.write_parquet(
        file_path,
        compression=compression,
        compression_level=compression_level,
        metadata=as_string_mapping(metadata),
        **kwargs,
    )


def calculate_file_hash(file_path: Path, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """
    Calcula o hash de um arquivo de forma eficiente (em chunks).

    Args:
        file_path: Caminho para o arquivo.
        algorithm: Algoritmo de hash (padrão: "sha256").
        chunk_size: Tamanho do chunk em bytes (padrão: 8192).

    Returns:
        String hexadecimal do hash.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado para hash: {file_path}")

    hash_obj = hashlib.new(algorithm)

    # A função built-in open() do Python já aceita objetos Path nativamente!
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()
