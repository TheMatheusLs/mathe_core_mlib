from typing import Final

#: Mapeamento de nome de experimento → estilo visual.
#: Chaves sem ``label_prefix`` têm rótulo fixo; chaves com ``label_prefix``
#: recebem o sufixo ``_<rho>`` em tempo de plotagem.
PLOT_STYLES: Final[dict[str, dict[str, str]]] = {
    "FALL": {"color": "#7f7f7f", "marker": "s", "linestyle": ":", "label": "Fallback"},
    "MB-LOGO": {"color": "#0072B2", "marker": "s", "linestyle": ":", "label": "MB-LOGO"},
    "Linear": {"color": "#ff7f0e", "marker": "o", "linestyle": "--", "label": "TPE Linear"},
    "Parabola": {"color": "#009E73", "marker": "^", "linestyle": "-", "label": "TPE Parabólico"},
}

# Cores discretas e perceptualmente distintas para categorias ordinais
_PALETTE_BASE = [
    "#4C72B0",
    "#DD8452",
    "#55A868",
    "#C44E52",
    "#937860",
    "#DA8BC3",
    "#8C8C8C",
    "#CCB974",
    "#64B5CD",
]

_PALETTE_BAND = {"L": "mediumseagreen", "C": "steelblue", "S": "coral"}
