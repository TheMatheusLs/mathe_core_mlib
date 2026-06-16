"""
Funções para análise e comparação de resultados de simulações GNPy.

Este módulo fornece utilitários para:
- Comparação de configurações de simulação (sim_config.yaml)
- Comparação de ambientes de execução (env_snapshot.json)
- Validação de consistência entre execuções

Desenvolvido para suportar anál científicas reprodutíveis em estudos de
redes ópticas e algoritmos de otimização.

Autor: Matheus Lôbo dos Santos (matheus.lobo@ufpe.br)
"""

import json
from pathlib import Path

import pandas as pd
import yaml


def compare_yaml_files(
    folders: list[Path], ignore_path_to_scenarios: bool = False, ignore_is_debug: bool = False, ignore_parameters: bool = False
) -> tuple[bool, str, dict | None]:
    """
    Compara os arquivos sim_config.yaml entre as pastas, com opções de ignorar campos.

    Args:
        folders: Lista de pastas a comparar
        ignore_path_to_scenarios: Se True, ignora o campo 'path_to_scenarios'
        ignore_is_debug: Se True, ignora o campo 'is_debug'
        ignore_parameters: Se True, ignora todo o bloco 'parameters'

    Returns:
        Tuple[bool, str, dict]: (são_iguais, mensagem, config_referência_filtrada)

    Example:
        >>> from pathlib import Path
        >>> folders = [Path("sim_v1"), Path("sim_v2")]
        >>> match, msg, config = compare_yaml_files(folders)
        >>> if match:
        ...     print("✅ Configurações idênticas")
    """
    # Convert strings to Path objects if necessary
    folders = [Path(f) if isinstance(f, str) else f for f in folders]

    configs = []

    # Campos que SEMPRE devem ser ignorados
    always_ignore = ["path_to_save", "max_workers"]

    for folder in folders:
        config_file = folder / "sim_config.yaml"
        if not config_file.exists():
            return False, f"❌ Arquivo não encontrado: {config_file}", None

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

            # Remover campos obrigatórios
            for key in always_ignore:
                data.pop(key, None)

            # Remover campos opcionais se solicitado
            if ignore_path_to_scenarios:
                data.pop("path_to_scenarios", None)

            if ignore_is_debug:
                data.pop("is_debug", None)

            if ignore_parameters:
                data.pop("parameters", None)

            configs.append(data)

    # Comparar os configs
    reference = configs[0]
    for i, config in enumerate(configs[1:], 1):
        if config != reference:
            # Identificar a diferença específica para melhorar a mensagem
            ref_keys = set(reference.keys())
            curr_keys = set(config.keys())
            diff_msg = ""

            # 1. Verificar chaves diferentes
            if ref_keys != curr_keys:
                missing = ref_keys - curr_keys
                extra = curr_keys - ref_keys
                parts = []
                if missing:
                    parts.append(f"faltando {missing}")
                if extra:
                    parts.append(f"extras {extra}")
                diff_msg = "Chaves estruturais diferentes: " + ", ".join(parts)

            # 2. Verificar valores diferentes (para chaves comuns)
            else:
                diffs = []
                for k in reference:
                    if reference[k] != config[k]:
                        if isinstance(reference[k], dict) and isinstance(config[k], dict):
                            diffs.append(f"bloco '{k}' difere")
                        else:
                            diffs.append(f"campo '{k}': {reference[k]} != {config[k]}")
                diff_msg = "Valores diferentes: " + ", ".join(diffs)

            return False, f"❌ Diferença na pasta {i} ({folders[i].name}): {diff_msg}", None

    return True, "✅ Todos os arquivos sim_config.yaml são idênticos (nos campos verificados)", reference


def compare_env_snapshots(
    folders: list[str | Path], folder_labels: dict[str, str], ignore_gnpy_commit: bool = True
) -> tuple[bool, str, pd.DataFrame]:
    """
    Compara os arquivos env_snapshot.json entre as pastas.

    Args:
        folders: Lista de pastas a comparar
        folder_labels: Dicionário mapeando nome da pasta para rótulo
        ignore_gnpy_commit: Se True, ignora diferenças no commit do GNPy

    Returns:
        Tuple[bool, str, pd.DataFrame]: (são_iguais, mensagem, dataframe_comparativo)

    Example:
        >>> from pathlib import Path
        >>> folders = [Path("sim_v1"), Path("sim_v2")]
        >>> labels = {"sim_v1": "Original", "sim_v2": "Optimized"}
        >>> match, msg, df = compare_env_snapshots(folders, labels)
        >>> print(df[df['Diferente'] == '⚠️'])  # Mostrar apenas diferenças
    """
    # Convert strings to Path objects if necessary
    folders = [Path(f) if isinstance(f, str) else f for f in folders]

    envs = []

    for folder in folders:
        env_file = folder / "env_snapshot.json"
        if not env_file.exists():
            return False, f"❌ Arquivo não encontrado: {env_file}", pd.DataFrame()

        with open(env_file, "r", encoding="utf-8") as f:
            env_data = json.load(f)
            combined = {}
            # Adicionar bibliotecas locais
            for name, info in env_data.get("local_libraries", {}).items():
                combined[name] = f"{info.get('version', 'N/A')} (commit: {info.get('git_commit', 'N/A')})"
            # Adicionar dependências
            for name, version in env_data.get("dependencies", {}).items():
                combined[name] = version
            envs.append(combined)

    # Criar DataFrame para comparação
    comparison_data = []
    all_keys = set()
    for env in envs:
        all_keys.update(env.keys())

    differences = []

    for key in sorted(all_keys):
        values = [env.get(key, "N/A") for env in envs]
        unique_values = set(values)
        has_diff = len(unique_values) > 1

        # Permitir diferença no commit do GNPy
        if ignore_gnpy_commit and key in ["gnpy", "oopt-gnpy"]:
            has_diff = False

        if has_diff:
            differences.append(key)

        row = {"Package": key}
        for i, folder in enumerate(folders):
            row[folder_labels[folder.name]] = values[i]
        row["Diferente"] = "⚠️" if has_diff else "✅"
        comparison_data.append(row)

    df = pd.DataFrame(comparison_data)

    if differences:
        msg = f"⚠️ Diferenças encontradas nos pacotes: {', '.join(differences)}"
        return False, msg, df
    else:
        msg = "✅ Todos os ambientes são compatíveis (ignorando diferenças no GNPy)"
        return True, msg, df
