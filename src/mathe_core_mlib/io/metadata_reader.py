"""
Leitura **somente-leitura** dos metadados de proveniência de artefatos em disco.

Cada formato guarda a proveniência num lugar diferente — chave ``_meta`` em
JSON/YAML, envelope em Pickle, key-value store do schema em Parquet, dicionário
Info em PDF, arquivo companheiro em PGF. Este módulo unifica o acesso a todos
eles atrás de uma função só.

Nenhuma função aqui abre arquivo para escrita, renomeia ou remove nada: o pior
que pode acontecer é devolver ``None`` para um artefato sem proveniência — o que,
aliás, é o uso principal em auditoria (descobrir o que foi gerado antes de a
proveniência virar obrigatória).

.. warning::
   Ler um ``.pkl`` exige desserializar o arquivo, e ``pickle`` executa código
   arbitrário durante esse processo. Por isso Pickle só é lido com
   ``allow_pickle=True`` explícito, e apenas em arquivos de origem confiável.

Routines
--------
read_metadata : Lê o bloco de proveniência de um artefato.
iter_artifacts : Percorre uma pasta listando artefatos inspecionáveis.
find_identifying_fields : Aponta campos que identificam pessoa ou máquina.
"""

import json
import pickle
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from mathe_core_mlib.io.provenance import DATA_KEY, META_KEY

#: Sufixo dos arquivos companheiros de figura, que já são metadados por inteiro.
SIDECAR_SUFFIX = ".meta.json"

#: Extensões que este módulo sabe inspecionar.
SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".json", ".yaml", ".yml", ".pkl", ".parquet", ".pdf"})

#: Chave interna que o Polars grava sozinho; não é proveniência.
_ARROW_SCHEMA_KEY = "ARROW:schema"

#: Campos padronizados do dicionário Info de um PDF.
_PDF_INFO_PATTERN = re.compile(rb"/(Title|Author|Subject|Keywords|Creator|Producer|CreationDate)\s*\(((?:[^()\\]|\\.)*)\)")

#: Sequências de escape do PDF a desfazer na exibição.
_PDF_UNESCAPE = ((rb"\(", b"("), (rb"\)", b")"), (rb"\\", b"\\"))


def _read_json_like(file_path: Path) -> dict[str, Any] | None:
    """
    Lê o bloco ``_meta`` de um JSON ou YAML.

    Um arquivo ``*.meta.json`` é o próprio registro de proveniência (companheiro
    de figura), então seu conteúdo é devolvido inteiro.

    Parameters
    ----------
    file_path : Path
        Arquivo a inspecionar.

    Returns
    -------
    dict[str, Any] or None
        Bloco de proveniência, ou ``None`` se o arquivo não tiver um.
    """
    texto = file_path.read_text(encoding="utf-8")

    if file_path.suffix == ".json":
        conteudo = json.loads(texto)
    else:
        conteudo = yaml.safe_load(texto)

    if not isinstance(conteudo, dict):
        return None

    if file_path.name.endswith(SIDECAR_SUFFIX):
        return conteudo

    bloco = conteudo.get(META_KEY)

    return bloco if isinstance(bloco, dict) else None


def _read_pdf(file_path: Path) -> dict[str, Any] | None:
    """
    Extrai o dicionário Info de um PDF, lendo apenas os bytes do arquivo.

    Parameters
    ----------
    file_path : Path
        Arquivo PDF.

    Returns
    -------
    dict[str, Any] or None
        Campos padronizados encontrados, ou ``None`` se nenhum.
    """
    bruto = file_path.read_bytes()
    info: dict[str, Any] = {}

    for campo, valor in _PDF_INFO_PATTERN.findall(bruto):
        texto = valor
        for escapado, literal in _PDF_UNESCAPE:
            texto = texto.replace(escapado, literal)
        info[campo.decode("ascii")] = texto.decode("utf-8", "replace")

    return info or None


def read_metadata(file_path: Path, allow_pickle: bool = False) -> dict[str, Any] | None:
    """
    Lê o bloco de proveniência de um artefato, sem modificá-lo.

    Parameters
    ----------
    file_path : Path
        Artefato a inspecionar.
    allow_pickle : bool, optional
        Autoriza desserializar arquivos ``.pkl``. Desligado por padrão porque
        ``pickle`` executa código arbitrário ao carregar; ligue apenas para
        arquivos de origem confiável.

    Returns
    -------
    dict[str, Any] or None
        Bloco de proveniência, ou ``None`` se o artefato não tiver metadados
        (o caso típico de arquivos anteriores à adoção da proveniência).

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    ValueError
        Se a extensão não for suportada, ou se for ``.pkl`` sem ``allow_pickle``.

    Examples
    --------
    >>> from pathlib import Path
    >>> read_metadata(Path("resultados.parquet"))  # doctest: +SKIP
    {'software': 'MGNPyEONv3', 'software_version': '3.17.0', ...}
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

    sufixo = file_path.suffix.lower()

    if sufixo in (".json", ".yaml", ".yml"):
        return _read_json_like(file_path)

    if sufixo == ".parquet":
        # read_parquet_metadata le so o rodape do arquivo: nao carrega os dados
        bloco = {k: v for k, v in pl.read_parquet_metadata(file_path).items() if k != _ARROW_SCHEMA_KEY}
        return bloco or None

    if sufixo == ".pdf":
        return _read_pdf(file_path)

    if sufixo == ".pkl":
        if not allow_pickle:
            raise ValueError(f"Leitura de {file_path.name} exige allow_pickle=True: desserializar um pickle executa codigo arbitrario.")

        with file_path.open("rb") as handle:
            cru = pickle.load(handle)

        if isinstance(cru, dict) and set(cru) == {META_KEY, DATA_KEY}:
            bloco = cru[META_KEY]
            return bloco if isinstance(bloco, dict) else None

        return None

    raise ValueError(f"Extensao nao suportada para inspecao: {file_path.suffix!r}")


#: Campos cujo valor identifica a máquina ou a pessoa por natureza.
_IDENTIFYING_KEYS = frozenset({"hostname"})

#: Detecta caminhos absolutos embutidos em valores (Windows e POSIX).
_ABSOLUTE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:[\\/]|/home/|/Users/)")


def find_identifying_fields(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Aponta os campos que podem identificar a máquina ou a pessoa.

    Serve para revisar um artefato **antes** de publicá-lo como material
    suplementar — em especial sob revisão duplo-cega, onde o nome da máquina ou
    um caminho absoluto podem revelar a autoria.

    Parameters
    ----------
    metadata : dict[str, Any]
        Bloco de proveniência lido de um artefato.

    Returns
    -------
    dict[str, str]
        Campo para o motivo pelo qual ele identifica. Vazio se nada foi detectado.

    Examples
    --------
    >>> find_identifying_fields({"hostname": "Yoga7iMatheus", "software": "Sim"})
    {'hostname': 'nome da maquina'}
    >>> find_identifying_fields({"entrada": "C:/Users/joao/dados.parquet"})
    {'entrada': 'caminho absoluto'}
    >>> find_identifying_fields({"software_version": "1.0.0"})
    {}
    """
    achados: dict[str, str] = {}

    for chave, valor in metadata.items():
        if chave in _IDENTIFYING_KEYS:
            achados[chave] = "nome da maquina"
        elif isinstance(valor, str) and _ABSOLUTE_PATH_PATTERN.search(valor):
            achados[chave] = "caminho absoluto"

    return achados


def iter_artifacts(root: Path, recursive: bool = True) -> Iterator[Path]:
    """
    Percorre uma pasta listando os artefatos que este módulo sabe inspecionar.

    Parameters
    ----------
    root : Path
        Pasta raiz, ou o próprio arquivo (devolvido como item único).
    recursive : bool, optional
        Se ``True`` (padrão), desce nas subpastas.

    Yields
    ------
    Path
        Artefatos encontrados, em ordem alfabética estável.

    Raises
    ------
    FileNotFoundError
        Se ``root`` não existir.
    """
    if not root.exists():
        raise FileNotFoundError(f"Caminho nao encontrado: {root}")

    if root.is_file():
        yield root
        return

    padrao = "**/*" if recursive else "*"

    for caminho in sorted(root.glob(padrao)):
        if caminho.is_file() and caminho.suffix.lower() in SUPPORTED_SUFFIXES:
            yield caminho
