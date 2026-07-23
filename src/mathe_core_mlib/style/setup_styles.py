import matplotlib.pyplot as plt
from cycler import cycler


def setup_academic_style(columns: int = 1) -> None:
    """Configura o Matplotlib com o padrão ouro para revistas (IEEE/OSA)."""

    # Define a largura exata baseada na coluna da revista
    figsize = (3.5, 2.5) if columns == 1 else (7.16, 3.0)

    # Paleta de cores elegante e amigável para daltônicos (Okabe-Ito)
    # Substitui aquele azul/laranja padrão por tons mais profissionais.
    academic_colors = [
        "#E69F00",  # Dourado/Laranja
        "#56B4E9",  # Azul claro
        "#009E73",  # Verde esmeralda
        "#F0E442",  # Amarelo
        "#0072B2",  # Azul escuro
        "#D55E00",  # Vermelho/Laranja escuro
        "#CC79A7",  # Rosa/Púrpura
        "#000000",  # Preto
    ]

    plt.rcParams.update(
        {
            # --- LATEX E FONTES ---
            "text.usetex": True,
            "text.latex.preamble": r"\usepackage{mathptmx} \usepackage{amsmath}",
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 9,
            # --- EIXOS E LABELS ---
            "axes.labelsize": 9,
            "axes.labelpad": 4.0,  # Respiro entre o número e o nome do eixo
            "axes.linewidth": 0.8,  # Espessura da caixa do gráfico
            "axes.spines.top": False,  # Remove borda superior
            "axes.spines.right": False,  # Remove borda direita
            "axes.prop_cycle": cycler(color=academic_colors),  # Paleta global
            # --- TICKS (Números dos eixos) ---
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.major.size": 3.5,
            "xtick.major.width": 0.8,
            "ytick.major.size": 3.5,
            "ytick.major.width": 0.8,
            "xtick.minor.visible": True,
            "ytick.minor.visible": True,
            "xtick.minor.size": 2.0,
            "ytick.minor.size": 2.0,
            "xtick.major.pad": 3.0,  # Afasta o número levemente do eixo
            "ytick.major.pad": 3.0,
            # --- LINHAS E MARCADORES ---
            "lines.linewidth": 1.5,
            "lines.markersize": 3.5,  # Tamanho global dos marcadores
            "lines.markeredgewidth": 0.8,  # Espessura da borda do marcador
            "lines.solid_capstyle": "round",  # Deixa o fim das linhas arredondado
            # --- LEGENDA (Design minimalista) ---
            "legend.fontsize": 8,
            "legend.title_fontsize": 8,
            "legend.frameon": True,  # Manter a caixa...
            "legend.framealpha": 0.9,  # ...mas levemente transparente
            "legend.edgecolor": "#CCCCCC",  # Borda cinza bem sutil
            "legend.fancybox": False,  # Cantos quadrados (mais sério)
            "legend.handlelength": 1.5,  # Linha de exemplo mais curta
            "legend.handletextpad": 0.5,  # Espaço entre a linha e o texto
            "legend.borderpad": 0.4,  # Respiro interno da legenda
            "legend.borderaxespad": 0.5,  # Distância da legenda para a borda do gráfico
            # --- GRID ---
            "axes.grid": True,
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
            "grid.alpha": 0.3,  # Grid bem suave para não poluir
            "axes.axisbelow": True,  # Garante que o grid fique SEMPRE atrás dos dados
            # --- DIMENSÕES E EXPORTAÇÃO ---
            "figure.figsize": figsize,
            "figure.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,  # Margem mínima ao salvar
            "savefig.transparent": False,  # Fundo branco para garantir contraste
        }
    )
