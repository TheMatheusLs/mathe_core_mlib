"""
Construção dos metadados de proveniência gravados em todo artefato salvo em disco.

Este módulo centraliza a política de rastreabilidade da lib: qualquer função
``save_*`` monta seu bloco de metadados aqui, de modo que todos os formatos
(JSON, YAML, Pickle, Parquet, figuras) carreguem exatamente os mesmos campos.

A versão do software é sempre um argumento **explícito** do chamador — a lib não
tenta adivinhá-la, porque quem sabe a versão do experimento é o simulador, não a
biblioteca. Já o estado do git é inferido do repositório que contém o diretório
de trabalho atual, e fica em cache para que salvar milhares de arquivos em laço
não dispare um subprocesso por chamada.

Routines
--------
build_metadata : Monta o dicionário de proveniência de um artefato.
as_string_mapping : Achata os metadados em ``dict[str, str]`` (Parquet/Arrow).
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

#: Chave que carrega o bloco de metadados dentro de JSON, YAML e Pickle.
META_KEY = "_meta"

#: Chave que carrega o objeto original dentro do envelope de Pickle.
DATA_KEY = "_data"

#: Definir como "1" omite o ``hostname`` dos metadados.
#:
#: O nome da máquina é útil para saber onde um resultado foi produzido — em
#: especial quando duas máquinas divergem numericamente. Mas ele costuma conter
#: o nome da pessoa (``Yoga7iMatheus``, ``DESKTOP-JOAO``), o que o torna um dado
#: identificável ao publicar arquivos como material suplementar, sobretudo em
#: revisão duplo-cega. Este opt-out existe para essas ocasiões.
NO_HOSTNAME_ENV_VAR = "MATHE_META_NO_HOSTNAME"

#: Timeout curto: git é local, se travar não vale bloquear a simulação.
_GIT_TIMEOUT_S = 5


@lru_cache(maxsize=8)
def _git_state(start_path: str) -> tuple[str | None, bool | None]:
    """
    Descobre commit curto e estado sujo do repositório que contém ``start_path``.

    O resultado é memoizado por caminho: o estado do git não muda no meio de uma
    execução, e cada consulta custa dois subprocessos.

    Parameters
    ----------
    start_path : str
        Diretório a partir do qual procurar o repositório. É ``str`` (e não
        ``Path``) porque ``lru_cache`` exige argumentos hasheáveis e estáveis.

    Returns
    -------
    tuple[str | None, bool | None]
        Par ``(commit_curto, esta_sujo)``. Ambos são ``None`` quando o caminho
        não pertence a um repositório git ou o binário ``git`` não está no PATH.

    Examples
    --------
    >>> commit, dirty = _git_state(".")
    >>> commit is None or isinstance(commit, str)
    True
    """
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=start_path,
            stderr=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_S,
        ).decode()

        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=start_path,
            stderr=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_S,
        ).decode()
    except (OSError, subprocess.SubprocessError):
        # Sem git, fora de repositório ou timeout: proveniência segue sem o commit
        return None, None

    return commit.strip(), bool(status.strip())


def build_metadata(
    version: str,
    *,
    software: str | None = None,
    extra: dict[str, Any] | None = None,
    include_git: bool = True,
) -> dict[str, Any]:
    """
    Monta o bloco de proveniência que acompanha um artefato salvo em disco.

    Parameters
    ----------
    version : str
        Versão do software que gerou o artefato (ex.: ``"3.15.1"``). Obrigatório
        e explícito: é o chamador quem conhece a própria versão.
    software : str or None, optional
        Nome do projeto gerador (ex.: ``"MGNPyEONv3"``). Omitido do resultado
        quando ``None``.
    extra : dict[str, Any] or None, optional
        Campos adicionais específicos do artefato (ex.: ``{"seed": 42}``). São
        mesclados por último e podem sobrescrever os campos padrão.
    include_git : bool, optional
        Quando ``True`` (padrão), anexa ``git_commit`` e ``git_dirty`` do
        repositório que contém o diretório de trabalho atual.

    Returns
    -------
    dict[str, Any]
        Dicionário de proveniência com, no mínimo, ``created_at`` (UTC, ISO 8601),
        ``software_version``, ``python_version`` e ``platform``. Inclui também
        ``hostname``, salvo se :data:`NO_HOSTNAME_ENV_VAR` estiver definido — ver
        a constante para as implicações de privacidade ao publicar dados.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for uma string vazia.

    Examples
    --------
    >>> meta = build_metadata("1.0.0", software="MeuSim", include_git=False)
    >>> meta["software"], meta["software_version"]
    ('MeuSim', '1.0.0')
    >>> sorted(k for k in meta if k.startswith("git"))
    []
    """
    if not isinstance(version, str):
        raise TypeError(f"'version' deve ser str, recebido {type(version).__name__}.")
    if not version.strip():
        raise ValueError("'version' não pode ser vazio: todo artefato deve registrar a versão que o gerou.")

    metadata: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "software_version": version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }

    # Nome da maquina: identifica onde o resultado foi produzido. Omitido quando
    # MATHE_META_NO_HOSTNAME=1, ver a constante para o motivo.
    if os.environ.get(NO_HOSTNAME_ENV_VAR, "") != "1":
        hostname = platform.node()
        if hostname:
            metadata["hostname"] = hostname

    if software:
        metadata["software"] = software

    if include_git:
        commit, is_dirty = _git_state(str(Path.cwd()))
        if commit is not None:
            metadata["git_commit"] = commit
            metadata["git_dirty"] = is_dirty

    if extra:
        metadata.update(extra)

    return metadata


def as_string_mapping(metadata: dict[str, Any]) -> dict[str, str]:
    """
    Achata os metadados em pares ``str -> str``, formato exigido pelo Arrow/Parquet.

    Strings passam intactas (para continuarem legíveis em qualquer leitor de
    Parquet); os demais tipos são serializados em JSON.

    Parameters
    ----------
    metadata : dict[str, Any]
        Bloco de proveniência produzido por :func:`build_metadata`.

    Returns
    -------
    dict[str, str]
        Mesmo conteúdo, com todos os valores convertidos para ``str``.

    Examples
    --------
    >>> as_string_mapping({"software": "Sim", "git_dirty": False, "seed": 42})
    {'software': 'Sim', 'git_dirty': 'false', 'seed': '42'}
    """
    # str fica crua para não virar '"texto"' com aspas dentro do arquivo
    return {key: value if isinstance(value, str) else json.dumps(value) for key, value in metadata.items()}


def command_line() -> str:
    """
    Retorna a linha de comando que originou o processo atual.

    Útil como campo ``extra`` quando se quer reproduzir a invocação exata.

    Returns
    -------
    str
        Argumentos de ``sys.argv`` unidos por espaço.

    Examples
    --------
    >>> isinstance(command_line(), str)
    True
    """
    return " ".join(sys.argv)
