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

import pandas as pd
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union


def compare_yaml_files(folders: List[Union[str, Path]]) -> Tuple[bool, str, Optional[dict]]:
    """
    Compara os arquivos sim_config.yaml entre as pastas.
    
    Args:
        folders: Lista de pastas a comparar
    
    Returns:
        Tuple[bool, str, dict]: (são_iguais, mensagem, config_referência)
    
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
    
    for folder in folders:
        config_file = folder / 'sim_config.yaml'
        if not config_file.exists():
            return False, f"❌ Arquivo não encontrado: {config_file}", None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            configs.append(yaml.safe_load(f))
    
    # Comparar os configs
    reference = configs[0]
    for i, config in enumerate(configs[1:], 1):
        if config != reference:
            return False, f"❌ Arquivo sim_config.yaml diferente entre pasta 0 e {i}", None
    
    return True, "✅ Todos os arquivos sim_config.yaml são idênticos", reference


def compare_env_snapshots(folders: List[Union[str, Path]], folder_labels: Dict[str, str], 
                          ignore_gnpy_commit: bool = True) -> Tuple[bool, str, pd.DataFrame]:
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
        env_file = folder / 'env_snapshot.json'
        if not env_file.exists():
            return False, f"❌ Arquivo não encontrado: {env_file}", pd.DataFrame()
        
        with open(env_file, 'r', encoding='utf-8') as f:
            env_data = json.load(f)
            combined = {}
            # Adicionar bibliotecas locais
            for name, info in env_data.get('local_libraries', {}).items():
                combined[name] = f"{info.get('version', 'N/A')} (commit: {info.get('git_commit', 'N/A')})"
            # Adicionar dependências
            for name, version in env_data.get('dependencies', {}).items():
                combined[name] = version
            envs.append(combined)
    
    # Criar DataFrame para comparação
    comparison_data = []
    all_keys = set()
    for env in envs:
        all_keys.update(env.keys())
    
    differences = []
    
    for key in sorted(all_keys):
        values = [env.get(key, 'N/A') for env in envs]
        unique_values = set(values)
        has_diff = len(unique_values) > 1
        
        # Permitir diferença no commit do GNPy
        if ignore_gnpy_commit and key in ['gnpy', 'oopt-gnpy']:
            has_diff = False
        
        if has_diff:
            differences.append(key)
        
        row = {'Package': key}
        for i, folder in enumerate(folders):
            row[folder_labels[folder.name]] = values[i]
        row['Diferente'] = '⚠️' if has_diff else '✅'
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    
    if differences:
        msg = f"⚠️ Diferenças encontradas nos pacotes: {', '.join(differences)}"
        return False, msg, df
    else:
        msg = "✅ Todos os ambientes são compatíveis (ignorando diferenças no GNPy)"
        return True, msg, df
