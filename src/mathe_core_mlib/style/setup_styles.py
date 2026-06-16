import matplotlib.pyplot as plt


def setup_academic_style() -> None:
    """Configura o Matplotlib com padrões visuais IEEE/OSA.

    Aplica via :func:`matplotlib.pyplot.rcParams.update` as seguintes
    definições globais:

    - Fonte serifada (``"serif"``), tamanho 11 pt.
    - Grade habilitada com traço ``"--"`` e opacidade 0.6.

    Notes
    -----
    Deve ser chamada uma única vez no início do notebook ou script antes
    de qualquer chamada de plotagem. Chamadas repetidas são idempotentes.

    Examples
    --------
    >>> configurar_estilo_academico()
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots()  # já com estilo aplicado
    """
    plt.rcParams.update(
        {
            "text.usetex": True,  # LaTeX real (requer TeX instalado)
            "text.latex.preamble": r"\usepackage{mathptmx} \usepackage{amsmath}",
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 16,  # IEEE/OSA: 8–9 pt em figuras
            "axes.labelsize": 16,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "legend.fontsize": 13,
            # Ajustes de Legenda para não ficar "lavada"
            "legend.framealpha": 1.0,
            "legend.edgecolor": "0.8",
            "legend.fancybox": False,
            # Força as linhas e marcadores a serem mais pesados por padrão
            "lines.linewidth": 2.0,
            "lines.markersize": 4.5,
            "axes.grid": True,
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
            "grid.alpha": 0.5,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            # Spines mais grossos para dar contraste com o texto preto
            "axes.linewidth": 1.0,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.minor.visible": True,
            "ytick.minor.visible": True,
            "xtick.major.size": 4.5,
            "ytick.major.size": 4.5,
            "xtick.minor.size": 2.5,
            "ytick.minor.size": 2.5,
        }
    )
