import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import polars as pl
import yaml


def load_json(file_path: Path) -> dict[str, Any]:
    """
    Carrega um arquivo JSON e retorna um dicionário.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict[str, Any], file_path: Path, indent: int = 4) -> None:
    """
    Salva um dicionário em um arquivo JSON.
    """
    # Cria os diretórios pai automaticamente
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_yaml(file_path: Path) -> dict[str, Any]:
    """
    Carrega um arquivo YAML e retorna um dicionário.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo YAML não encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_yaml(data: dict[str, Any], file_path: Path) -> None:
    """
    Salva um dicionário em arquivo YAML.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_pickle(file_path: Path) -> Any:
    """Carrega um objeto de um arquivo .pkl."""
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo Pickle não encontrado: {file_path}")

    with open(file_path, "rb") as f:
        return pickle.load(f)


def save_pickle(data: Any, file_path: Path) -> None:
    """Salva qualquer objeto Python em um arquivo .pkl."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        pickle.dump(data, f)


def load_csv(file_path: Path, **kwargs) -> pl.DataFrame:
    """
    Carrega um arquivo CSV em um DataFrame do Polars.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")

    return pl.read_csv(file_path, **kwargs)


def load_parquet(file_path: Path, **kwargs) -> pl.DataFrame:
    """
    Carrega um arquivo Parquet em um DataFrame do Polars.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo Parquet não encontrado: {file_path}")

    return pl.read_parquet(file_path, **kwargs)


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
