from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

from mathe_core_mlib.style.custom_palletes import _PALETTE_BASE


def save_figure(fig: Figure, path: Path, *, pgf: bool = False) -> None:
    """
    Salva a figura como PDF vetorial e opcionalmente como .pgf.

    Parameters
    ----------
    fig  : Figure a salvar.
    path : Caminho base sem extensão (ex: 'outputs/traffic_profile').
    pgf  : Se True, salva também o .pgf para inclusão direta em LaTeX.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", backend="pdf")
    print(f"💾 Salvos em: {path}\n")

    if pgf:
        # pgf requer LaTeX instalado; fallback silencioso se não disponível
        try:
            fig.savefig(path.with_suffix(".pgf"), bbox_inches="tight", backend="pgf")
        except Exception as exc:  # noqa: BLE001
            print(f"[save_figure] pgf indisponível ({exc}), apenas .pdf salvo.")


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
