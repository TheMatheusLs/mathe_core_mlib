import json
import pickle
import os
import yaml
from typing import Any, Dict
import hashlib
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Union


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Carrega um arquivo JSON e retorna um dicionário.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: str, indent: int = 4) -> None:
    """
    Salva um dicionário em um arquivo JSON.
    """
    # Garante que o diretório pai existe
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Carrega um arquivo YAML e retorna um dicionário.
    """
    with open(file_path, "r", encoding='utf-8') as file:
        return yaml.safe_load(file)


def save_yaml(data: Dict[str, Any], file_path: str) -> None:
    """
    Salva um dicionário em arquivo YAML.
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_pickle(file_path: str) -> Any:
    """Carrega um objeto de um arquivo .pkl."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo Pickle não encontrado: {file_path}")
        
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def save_pickle(data: Any, file_path: str) -> None:
    """Salva qualquer objeto Python em um arquivo .pkl."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)


def load_csv(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Carrega um arquivo CSV em um DataFrame do Pandas.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")
    
    return pd.read_csv(file_path, **kwargs)


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """
    Calcula o hash de um arquivo de forma eficiente (em chunks).
    
    Args:
        file_path: Caminho para o arquivo.
        algorithm: Algoritmo de hash (padrão: "sha256").
        chunk_size: Tamanho do chunk em bytes (padrão: 8192).
        
    Returns:
        String hexadecimal do hash.
    """
    file_path = str(file_path) # Garante que seja string
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado para hash: {file_path}")

    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)
            
    return hash_obj.hexdigest()