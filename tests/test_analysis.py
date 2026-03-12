import yaml
from pathlib import Path
from mathe_core_mlib.analysis import compare_yaml_files

def test_compare_yaml_files_identical(tmp_path: Path):
    """Garante que dois arquivos YAML idênticos são validados corretamente."""
    
    # tmp_path é uma fixture do pytest que cria pastas temporárias automáticas
    dir_v1 = tmp_path / "sim_v1"
    dir_v2 = tmp_path / "sim_v2"
    dir_v1.mkdir()
    dir_v2.mkdir()

    config_base = {
        "is_debug": False,
        "path_to_scenarios": "/dev/null",
        "parameters": {"power_dbm": 0.0, "baud_rate": 32e9}
    }

    # Gera os arquivos de simulação temporários
    for directory in [dir_v1, dir_v2]:
        with open(directory / "sim_config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_base, f)

    match, msg, config_filtrada = compare_yaml_files([dir_v1, dir_v2])

    assert match is True, f"Esperava True, falhou com mensagem: {msg}"
    assert config_filtrada == config_base


def test_compare_yaml_files_ignore_debug_flag(tmp_path: Path):
    """Garante que a flag ignore_is_debug impede falsos negativos na comparação."""
    
    dir_v1 = tmp_path / "sim_v1"
    dir_v2 = tmp_path / "sim_v2"
    dir_v1.mkdir()
    dir_v2.mkdir()

    # Cenários diferem APENAS na flag is_debug
    config_v1 = {"is_debug": False, "param_x": 100}
    config_v2 = {"is_debug": True,  "param_x": 100}

    with open(dir_v1 / "sim_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_v1, f)
    with open(dir_v2 / "sim_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_v2, f)

    folders = [dir_v1, dir_v2]

    # Teste 1: Sem ignorar a flag, a comparação DEVE falhar
    match_falso, _, _ = compare_yaml_files(folders, ignore_is_debug=False)
    assert match_falso is False

    # Teste 2: Ignorando a flag, a comparação DEVE passar
    match_verdadeiro, _, _ = compare_yaml_files(folders, ignore_is_debug=True)
    assert match_verdadeiro is True