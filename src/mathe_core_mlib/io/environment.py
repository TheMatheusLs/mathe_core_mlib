import json
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, Union

# Tenta importar colorama, se não existir, define classes dummy para não quebrar
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore: RED = YELLOW = GREEN = ""
    class Style: RESET_ALL = BRIGHT = ""

def _get_git_info(path: Path) -> dict:
    """Extrai informações do git de um diretório."""
    git_info = {
        "path": str(path),
        "git_commit": "Unknown",
        "git_branch": "Unknown",
        "git_tag": None,
        "last_commit_msg": "",
        "is_dirty": False
    }

    if (path / ".git").exists():
        try:
            # 1. Hash Curto
            git_info["git_commit"] = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], 
                cwd=path, stderr=subprocess.DEVNULL
            ).decode().strip()

            # 2. Branch Atual (retorna 'HEAD' se estiver detached)
            git_info["git_branch"] = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                cwd=path, stderr=subprocess.DEVNULL
            ).decode().strip()

            # 3. Título do Último Commit
            git_info["last_commit_msg"] = subprocess.check_output(
                ["git", "log", "-1", "--format=%s"], 
                cwd=path, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="replace").strip()

            # 4. Tag Exata (se houver)
            try:
                git_info["git_tag"] = subprocess.check_output(
                    ["git", "describe", "--tags", "--exact-match"], 
                    cwd=path, stderr=subprocess.DEVNULL
                ).decode().strip()
            except subprocess.CalledProcessError:
                git_info["git_tag"] = None

            # 5. Status Dirty
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=path, stderr=subprocess.DEVNULL
            ).decode().strip()
            
            git_info["is_dirty"] = bool(status)
            if status:
                git_info["dirty_files"] = status.split('\n')

        except Exception as e:
            git_info["git_error"] = str(e)
            
    return git_info

def snapshot_environment(save_path: Union[str, Path]) -> Path:
    """
    Gera um snapshot (JSON) do ambiente atual usando 'uv pip list'.
    Detecta automaticamente bibliotecas editáveis, commits e branches.
    
    Args:
        save_path: Diretório onde o arquivo env_snapshot.json será salvo.
        
    Returns:
        Path do arquivo salvo.
    """
    print(f"{Fore.CYAN}📸 [System] Gerando snapshot do ambiente via UV...{Style.RESET_ALL}")
    
    env_data = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "command_line_args": sys.argv, # Argumentos usados para rodar o script
        "simulator_git": _get_git_info(Path.cwd()), # Assume que o "simulador" é o código que está rodando no CWD
        "local_libraries": {},
        "dependencies": {}
    }

    try:
        # Chama o UV para garantir a fonte da verdade
        uv_output = subprocess.check_output(
            ["uv", "pip", "list", "--format=json"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8")
        packages = json.loads(uv_output)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ Erro: 'uv' não encontrado no PATH.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao executar 'uv pip list': {e}{Style.RESET_ALL}")
        return None

    for pkg in packages:
        name = pkg.get("name")
        version = pkg.get("version")
        editable_path = pkg.get("editable_project_location")

        if editable_path:
            local_path = Path(editable_path).resolve()
            
            git_info = _get_git_info(local_path)
            git_info["version"] = version # Adiciona a versão do pacote ao dict
            
            env_data["local_libraries"][name] = git_info
        else:
            env_data["dependencies"][name] = version

    output_file = Path(save_path) / "env_snapshot.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(env_data, f, indent=4, ensure_ascii=False)
        
    return output_file

def enforce_clean_environment(snapshot_path: Union[str, Path], strict: bool = True):
    """
    Valida o snapshot e bloqueia a execução se houver bibliotecas 'sujas' (dirty).
    
    Args:
        snapshot_path: Diretório contendo o env_snapshot.json
        strict: Se True, lança erro e para o código. Se False, apenas avisa.
    """
    snapshot_file = Path(snapshot_path) / "env_snapshot.json"

    if not snapshot_file.exists():
        error_msg = (
            f"Arquivo de auditoria não encontrado em: {snapshot_file}\n"
            f"Você deve executar 'snapshot_environment()' antes de validar o ambiente."
        )
        print(f"{Fore.RED}❌ ERRO FATAL: {error_msg}{Style.RESET_ALL}")
        # Interrompe tudo, pois sem snapshot não há ciência confiável.
        raise FileNotFoundError(error_msg)
        
    try:
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}❌ ERRO: O snapshot está corrompido ou inválido.{Style.RESET_ALL}")
        raise e

    dirty_libs = []
    for lib_name, lib_info in data.get("local_libraries", {}).items():
        if lib_info.get("is_dirty", False):
            dirty_libs.append((lib_name, lib_info.get("dirty_files", [])))

    if dirty_libs:
        print(f"\n{Fore.RED}{'='*60}")
        print(f"🛑 CRITICAL: AMBIENTE 'SUJO' DETECTADO")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        for lib, files in dirty_libs:
            print(f"{Fore.RED}>> Lib: {Style.BRIGHT}{lib}{Style.RESET_ALL}")
            for f in files:
                print(f"    {f}")
        
        print(f"{Fore.YELLOW}\n>> AÇÃO: Faça commit das alterações antes de rodar simulações científicas.{Style.RESET_ALL}")
        
        if strict:
            raise RuntimeError(f"Execução abortada: {len(dirty_libs)} biblioteca(s) com alterações não salvas.")
    else:
        print(f"{Fore.GREEN}✅ [Gatekeeper] Ambiente limpo. Commit hashes verificados.{Style.RESET_ALL}")