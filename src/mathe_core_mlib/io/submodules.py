"""
Diagnóstico de submódulos git: onde cada um está e se está atualizado.

Existe porque "o submódulo está atualizado?" são três perguntas distintas, e
``git submodule status`` só responde a primeira:

1. **O ponteiro bate com a pasta?** O superprojeto grava um SHA fixo por
   submódulo; mexer na pasta sem commitar o ponteiro faz os dois divergirem.
2. **O commit fixado é o mais recente do remoto?** Um ponteiro consistente pode
   apontar para um commit de meses atrás e ainda assim parecer "em sincronia".
3. **O commit fixado foi publicado?** Apontar para um commit que só existe na
   máquina local quebra qualquer clone novo do projeto.

Uso como biblioteca::

    from mathe_core_mlib.io.submodules import collect_submodule_states
    states = collect_submodule_states(fetch=True)

Uso como CLI, de dentro de qualquer simulador::

    python -m mathe_core_mlib.io.submodules --fetch

Routines
--------
collect_submodule_states : Coleta o estado de todos os submódulos do repositório.
format_report : Formata os estados em um relatório legível.
main : Ponto de entrada da CLI.
"""

import argparse
import subprocess
import sys
import tomllib
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from dataclasses import dataclass
from pathlib import Path

#: Largura do rótulo nas linhas do relatório.
_LABEL_WIDTH = 22

#: Timeout de cada chamada ao git; local, não deve travar.
_GIT_TIMEOUT_S = 60


@dataclass
class ModuleState:
    """
    Estado de um submódulo em relação ao superprojeto e ao remoto.

    Attributes
    ----------
    name : str
        Nome da pasta do submódulo.
    path : Path
        Caminho absoluto do submódulo.
    recorded_commit : str
        SHA que o superprojeto registra no HEAD.
    checkout_commit : str
        SHA efetivamente presente no disco.
    branch : str
        Branch atual, ou ``"HEAD"`` quando em estado detached.
    describe : str
        Saída de ``git describe --tags --always``.
    version : str
        Versão declarada pelo módulo, ou ``"?"``.
    ahead, behind : int or None
        Commits à frente/atrás do upstream; ``None`` sem upstream configurado.
    is_dirty : bool
        Se há alterações não commitadas.
    is_published : bool or None
        Se o commit existe em algum branch remoto; ``None`` se indeterminado.
    """

    name: str
    path: Path
    recorded_commit: str
    checkout_commit: str
    branch: str
    describe: str
    version: str
    ahead: int | None
    behind: int | None
    is_dirty: bool
    is_published: bool | None

    @property
    def pointer_matches(self) -> bool:
        """Indica se o checkout corresponde ao commit registrado no superprojeto."""
        return self.recorded_commit == self.checkout_commit

    @property
    def is_healthy(self) -> bool:
        """
        Indica se o módulo está em estado reproduzível.

        Reproduzível significa: inicializado, ponteiro consistente, sem
        alterações locais, commit publicado e nada a puxar do remoto.

        O teste de ``checkout_commit`` não é redundante: um submódulo declarado
        mas nunca inicializado tem checkout e registro ambos vazios, o que faria
        ``pointer_matches`` passar por coincidência.
        """
        return (
            bool(self.checkout_commit) and self.pointer_matches and not self.is_dirty and self.is_published is not False and not self.behind
        )


def _git(repo: Path, *args: str) -> str:
    """
    Executa um comando git e devolve a saída limpa.

    Parameters
    ----------
    repo : Path
        Repositório onde rodar o comando.
    *args : str
        Argumentos do git.

    Returns
    -------
    str
        Saída padrão sem espaços nas pontas; string vazia em caso de falha.
    """
    try:
        completed = subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL, timeout=_GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return ""

    return completed.decode("utf-8", "replace").strip()


def find_repo_root(start: Path | None = None) -> Path | None:
    """
    Localiza a raiz do repositório git que contém ``start``.

    Parameters
    ----------
    start : Path or None, optional
        Diretório de partida. ``None`` usa o diretório de trabalho atual.

    Returns
    -------
    Path or None
        Raiz do repositório, ou ``None`` se ``start`` não estiver em um.

    Examples
    --------
    >>> root = find_repo_root()
    >>> root is None or root.is_dir()
    True
    """
    base = Path(start) if start is not None else Path.cwd()
    top = _git(base, "rev-parse", "--show-toplevel")

    return Path(top) if top else None


def _read_version(repo: Path) -> str:
    """
    Lê a versão declarada por um módulo.

    Procura, nesta ordem: ``pyproject.toml`` no layout PEP 621 (``[project]``),
    no layout Poetry (``[tool.poetry]``) e, por fim, ``setup.cfg`` — os módulos
    seguem convenções diferentes, e forks antigos ainda usam setuptools clássico.

    Parameters
    ----------
    repo : Path
        Raiz do módulo.

    Returns
    -------
    str
        Versão declarada, ou ``"?"`` se não for possível determinar.
    """
    pyproject = repo / "pyproject.toml"

    if pyproject.is_file():
        try:
            with pyproject.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            data = {}

        for section in (("project",), ("tool", "poetry")):
            node: object = data
            for key in section:
                node = node.get(key, {}) if isinstance(node, dict) else {}
            if isinstance(node, dict) and "version" in node:
                return str(node["version"])

    setup_cfg = repo / "setup.cfg"
    if setup_cfg.is_file():
        parser = ConfigParser()
        try:
            parser.read(setup_cfg, encoding="utf-8")
            return parser.get("metadata", "version", fallback="?")
        except (OSError, ConfigParserError):
            return "?"

    return "?"


def _submodule_paths(repo_root: Path) -> list[str]:
    """
    Lê os caminhos dos submódulos declarados em ``.gitmodules``.

    Usa o próprio git para interpretar o arquivo, em vez de fazer parsing manual:
    o layout dos submódulos varia entre projetos e não deve ser presumido.

    Parameters
    ----------
    repo_root : Path
        Raiz do superprojeto.

    Returns
    -------
    list[str]
        Caminhos relativos dos submódulos, ordenados.
    """
    if not (repo_root / ".gitmodules").is_file():
        return []

    saida = _git(repo_root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")

    # cada linha vem como "submodule.<nome>.path <caminho>"
    return sorted(line.split(maxsplit=1)[1] for line in saida.splitlines() if len(line.split(maxsplit=1)) == 2)


def _recorded_commits(repo_root: Path, paths: list[str]) -> dict[str, str]:
    """
    Lê os commits que o superprojeto registra para cada submódulo.

    Parameters
    ----------
    repo_root : Path
        Raiz do superprojeto.
    paths : list[str]
        Caminhos relativos dos submódulos.

    Returns
    -------
    dict[str, str]
        Caminho relativo para o SHA registrado no HEAD.
    """
    recorded: dict[str, str] = {}

    for line in _git(repo_root, "ls-tree", "HEAD", *paths).splitlines():
        # formato: "160000 commit <sha>\t<caminho>"
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "commit":
            recorded[path] = parts[2]

    return recorded


def collect_submodule_states(repo_root: Path | None = None, fetch: bool = False) -> list[ModuleState]:
    """
    Coleta o estado de todos os submódulos de um repositório.

    Parameters
    ----------
    repo_root : Path or None, optional
        Raiz do superprojeto. ``None`` detecta a partir do diretório atual.
    fetch : bool, optional
        Quando ``True``, consulta os remotos antes de comparar. Sem isso, a
        contagem de "atrás" reflete apenas o que já está no cache local e pode
        estar desatualizada.

    Returns
    -------
    list[ModuleState]
        Um registro por submódulo, ordenado por caminho. Vazio se o repositório
        não declarar submódulos.

    Raises
    ------
    FileNotFoundError
        Se ``repo_root`` não for (nem estiver dentro de) um repositório git.
    """
    root = find_repo_root(repo_root)
    if root is None:
        alvo = repo_root if repo_root is not None else Path.cwd()
        raise FileNotFoundError(f"Nao e um repositorio git: {alvo}")

    paths = _submodule_paths(root)
    if not paths:
        return []

    recorded = _recorded_commits(root, paths)
    states: list[ModuleState] = []

    for rel_path in paths:
        module_path = root / rel_path
        if not (module_path / ".git").exists():
            # declarado no .gitmodules mas nunca inicializado
            states.append(
                ModuleState(
                    name=Path(rel_path).name,
                    path=module_path,
                    recorded_commit=recorded.get(rel_path, ""),
                    checkout_commit="",
                    branch="",
                    describe="nao inicializado",
                    version="?",
                    ahead=None,
                    behind=None,
                    is_dirty=False,
                    is_published=None,
                )
            )
            continue

        if fetch:
            _git(module_path, "fetch", "--tags", "origin")

        checkout = _git(module_path, "rev-parse", "HEAD")
        upstream = _git(module_path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")

        ahead = behind = None
        if upstream:
            counts = _git(module_path, "rev-list", "--left-right", "--count", f"HEAD...{upstream}").split()
            if len(counts) == 2:
                ahead, behind = int(counts[0]), int(counts[1])

        # Um commit só é recuperável por outra máquina se estiver em algum branch remoto
        published = bool(_git(module_path, "branch", "-r", "--contains", checkout)) if checkout else None

        states.append(
            ModuleState(
                name=Path(rel_path).name,
                path=module_path,
                recorded_commit=recorded.get(rel_path, ""),
                checkout_commit=checkout,
                branch=_git(module_path, "rev-parse", "--abbrev-ref", "HEAD"),
                describe=_git(module_path, "describe", "--tags", "--always") or "sem tag",
                version=_read_version(module_path),
                ahead=ahead,
                behind=behind,
                is_dirty=bool(_git(module_path, "status", "--porcelain")),
                is_published=published,
            )
        )

    return states


def _render(state: ModuleState) -> str:
    """
    Monta o bloco de relatório de um módulo.

    Parameters
    ----------
    state : ModuleState
        Estado coletado.

    Returns
    -------
    str
        Texto formatado, sem quebra de linha final.
    """
    mark = "OK " if state.is_healthy else "!! "
    lines = [f"{mark}{state.name}  (v{state.version})"]

    def add(label: str, value: str) -> None:
        lines.append(f"     {label:<{_LABEL_WIDTH}}{value}")

    if not state.checkout_commit:
        add("estado", "NAO INICIALIZADO -- rode 'git submodule update --init --recursive'")
        return "\n".join(lines)

    add("commit no disco", f"{state.checkout_commit[:9]}  ({state.describe})")

    if state.pointer_matches:
        add("ponteiro do projeto", "em sincronia")
    else:
        add("ponteiro do projeto", f"{state.recorded_commit[:9]}  <-- DIVERGENTE do disco")

    add("branch", state.branch if state.branch != "HEAD" else "(detached HEAD)")

    if state.ahead is None:
        add("vs remoto", "sem upstream configurado")
    elif state.ahead or state.behind:
        add("vs remoto", f"{state.ahead} a frente / {state.behind} atras")
    else:
        add("vs remoto", "atualizado")

    if state.is_published is False:
        add("publicado", "NAO -- commit so existe nesta maquina")

    if state.is_dirty:
        add("alteracoes locais", "SIM -- enforce_clean_environment vai abortar a simulacao")

    return "\n".join(lines)


def format_report(states: list[ModuleState], repo_root: Path, fetched: bool = False) -> str:
    """
    Formata os estados coletados em um relatório legível.

    Parameters
    ----------
    states : list[ModuleState]
        Estados devolvidos por :func:`collect_submodule_states`.
    repo_root : Path
        Raiz do superprojeto, usada no cabeçalho.
    fetched : bool, optional
        Se os remotos foram consultados; apenas informativo no cabeçalho.

    Returns
    -------
    str
        Relatório completo, pronto para impressão.
    """
    linhas = ["", f"MODULOS DE {repo_root.name}"]

    if not fetched:
        linhas.append("(comparacao com o remoto usa o cache local; rode com --fetch para atualizar)")

    linhas.append("=" * 72)

    if not states:
        linhas.append("Nenhum submodulo declarado neste repositorio.")
        return "\n".join(linhas)

    for state in states:
        linhas.append(_render(state))
        linhas.append("")

    problemas = [s.name for s in states if not s.is_healthy]

    if problemas:
        linhas.append(f"ATENCAO: {len(problemas)} modulo(s) fora de estado reproduzivel: {', '.join(problemas)}")
    else:
        linhas.append("Todos os modulos estao em estado reproduzivel.")

    return "\n".join(linhas)


def diagnose(project: Path | None = None, fetch: bool = False) -> tuple[str, bool]:
    """
    Diagnostica um projeto e devolve o relatório pronto e o veredito.

    Parameters
    ----------
    project : Path or None, optional
        Raiz do projeto. ``None`` usa o diretório atual.
    fetch : bool, optional
        Se deve consultar os remotos antes de comparar.

    Returns
    -------
    tuple[str, bool]
        Par ``(relatorio, esta_ok)``. Um projeto que não é repositório git
        devolve a mensagem de erro e ``False``, em vez de levantar exceção —
        assim um projeto problemático não interrompe a varredura dos demais.
    """
    try:
        root = find_repo_root(project)
        states = collect_submodule_states(project, fetch=fetch)
    except FileNotFoundError as exc:
        return f"ERRO: {exc}", False

    if root is None:  # pragma: no cover - collect ja teria levantado
        return f"ERRO: nao e um repositorio git: {project}", False

    return format_report(states, root, fetched=fetch), all(s.is_healthy for s in states)


def main(argv: list[str] | None = None) -> int:
    """
    Ponto de entrada da CLI de diagnóstico.

    Aceita vários projetos de uma vez, para varrer todos os simuladores em uma
    chamada só. Cada projeto é avaliado de forma independente: um que falhe não
    impede o diagnóstico dos outros.

    Parameters
    ----------
    argv : list[str] or None, optional
        Argumentos de linha de comando. ``None`` usa ``sys.argv[1:]``.

    Returns
    -------
    int
        ``0`` se todos os projetos estão em estado reproduzível, ``1`` caso
        contrário.

    Examples
    --------
    Diagnosticar o diretório atual::

        python -m mathe_core_mlib.io.submodules

    Varrer vários simuladores a partir de qualquer lugar::

        python scripts/check_modules.py --fetch ../MGNPyEONv3 ../OpticalSimMBEON
    """
    parser = argparse.ArgumentParser(prog="check-modules", description="Diagnostica os submodulos git de um ou mais projetos.")
    parser.add_argument("paths", type=Path, nargs="*", help="raizes dos projetos (padrao: diretorio atual)")
    parser.add_argument("--fetch", action="store_true", help="consulta os remotos antes de comparar")
    args = parser.parse_args(argv)

    projetos: list[Path | None] = list(args.paths) if args.paths else [None]
    tudo_ok = True

    for projeto in projetos:
        relatorio, esta_ok = diagnose(projeto, fetch=args.fetch)
        print(relatorio)
        tudo_ok = tudo_ok and esta_ok

    return 0 if tudo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
