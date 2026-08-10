import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from mathe_core_mlib.io.provenance import build_metadata
from mathe_core_mlib.style.custom_palletes import _PALETTE_BASE

# Logger de biblioteca: sem handler próprio, quem configura é a aplicação.
# Mensagens vão sem emoji — o handler pode escrever em console cp1252 ou em
# arquivo de log, e caracteres fora do charmap derrubariam a gravação.
logger = logging.getLogger(__name__)

#: O backend PDF do Matplotlib só aceita este conjunto fechado de chaves; qualquer
#: outra emite UserWarning e é descartada. Por isso a proveniência completa vai
#: para o arquivo .meta.json companheiro, e aqui gravamos só um resumo.
_PDF_INFO_KEYS = frozenset({"Title", "Author", "Subject", "Keywords", "Creator", "Producer", "CreationDate", "ModDate", "Trapped"})


def _pdf_info_dict(metadata: dict[str, Any], title: str) -> dict[str, Any]:
    """
    Traduz o bloco de proveniência para as chaves padrão do dicionário Info do PDF.

    Parameters
    ----------
    metadata : dict[str, Any]
        Bloco produzido por :func:`~mathe_core_mlib.io.provenance.build_metadata`.
    title : str
        Título da figura (normalmente o nome do arquivo).

    Returns
    -------
    dict[str, Any]
        Dicionário restrito a :data:`_PDF_INFO_KEYS`, pronto para ``savefig(metadata=...)``.

    Examples
    --------
    >>> meta = {"created_at": "2026-08-10T12:00:00+00:00", "software_version": "1.0.0"}
    >>> info = _pdf_info_dict(meta, "figura")
    >>> set(info) <= _PDF_INFO_KEYS
    True
    """
    software = metadata.get("software", "mathe_core_mlib")
    version = metadata.get("software_version", "")
    commit = metadata.get("git_commit")

    subject_parts = [f"{software} {version}".strip()]
    if commit:
        subject_parts.append(f"commit {commit}{' (dirty)' if metadata.get('git_dirty') else ''}")

    info: dict[str, Any] = {
        "Title": title,
        "Creator": f"{software} {version}".strip(),
        "Subject": " | ".join(subject_parts),
        "Keywords": " ".join(f"{k}={v}" for k, v in metadata.items() if not isinstance(v, (dict, list))),
    }

    # CreationDate precisa ser datetime; created_at vem como string ISO 8601
    created_at = metadata.get("created_at")
    if isinstance(created_at, str):
        try:
            info["CreationDate"] = datetime.fromisoformat(created_at)
        except ValueError:
            pass

    return info


def save_figure(
    fig: Figure,
    path: Path,
    version: str,
    *,
    software: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    pgf: bool = False,
) -> None:
    """
    Salva a figura como PDF vetorial (e opcionalmente .pgf), com proveniência.

    São gravados dois canais de metadados: o dicionário Info do próprio PDF, que
    aceita apenas chaves padronizadas, e um arquivo companheiro
    ``<nome>.meta.json`` com o registro estruturado completo — este último cobre
    também o ``.pgf``, que não tem onde guardar metadados.

    Parameters
    ----------
    fig : Figure
        Figura a salvar.
    path : Path
        Caminho base **sem extensão** (ex.: ``'outputs/traffic_profile'``).
    version : str
        Versão do software que gerou a figura. Obrigatório.
    software : str or None, optional
        Nome do projeto gerador (ex.: ``"MGNPyEONv3"``).
    extra_meta : dict[str, Any] or None, optional
        Campos extras de proveniência (ex.: ``{"scenario": "parabolic"}``).
    pgf : bool, optional
        Se ``True``, salva também o ``.pgf`` para inclusão direta em LaTeX.

    Raises
    ------
    TypeError
        Se ``version`` não for uma string.
    ValueError
        Se ``version`` for vazio.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from pathlib import Path
    >>> fig, ax = plt.subplots()
    >>> save_figure(fig, Path("outputs/perfil"), version="1.0.0")  # doctest: +SKIP
    """
    metadata = build_metadata(version, software=software, extra=extra_meta)

    path.parent.mkdir(parents=True, exist_ok=True)

    pdf_path = path.with_suffix(".pdf")
    fig.savefig(pdf_path, bbox_inches="tight", backend="pdf", metadata=_pdf_info_dict(metadata, path.name))

    written = [pdf_path.name]

    if pgf:
        # pgf requer LaTeX instalado; fallback silencioso se não disponível
        try:
            fig.savefig(path.with_suffix(".pgf"), bbox_inches="tight", backend="pgf")
            written.append(path.with_suffix(".pgf").name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("pgf indisponivel (%s), apenas .pdf salvo para %s", exc, path)

    # Sidecar: registro completo, e único canal de proveniência do .pgf
    sidecar = path.with_suffix(".meta.json")
    sidecar.write_text(json.dumps({**metadata, "files": written}, indent=4, ensure_ascii=False), encoding="utf-8")
    written.append(sidecar.name)

    logger.info("Figura salva em %s (%s)", path.parent, ", ".join(written))


def set_axes_decimal_separator(ax: Axes, separator: str = ",") -> None:
    """
    Força o separador decimal dos eixos X e Y independentemente do Sistema Operacional.

    Parameters
    ----------
    ax : plt.Axes
        O objeto de eixos do Matplotlib a ser formatado.
    separator : str, optional
        O caractere desejado para separar os decimais (ex: ',' para PT-BR, '.' para EN).
    """

    def format_tick(x, pos):
        # O '%g' garante que números inteiros fiquem limpos (ex: 24.0 vira 24)
        s = f"{x:g}"
        if separator == ",":
            s = s.replace(".", ",")
        return s

    formatter = FuncFormatter(format_tick)
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(formatter)


def _categorical_palette(n: int) -> list[str]:
    """Retorna n cores ciclando pela paleta base."""
    return [_PALETTE_BASE[i % len(_PALETTE_BASE)] for i in range(n)]


def _annotate_bars(ax: Axes, fmt: str = "{:.0f}") -> None:
    """Escreve o valor de cada barra logo acima dela."""
    for patch in ax.patches:
        if isinstance(patch, Rectangle):
            h = patch.get_height()
            if np.isnan(h) or h == 0:
                continue
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                h,
                fmt.format(h),
                ha="center",
                va="bottom",
                fontsize=12,
                color="dimgray",
            )
