#!/usr/bin/env python
"""
Mostra os metadados de proveniência de artefatos em disco. Somente leitura.

Percorre um arquivo ou uma pasta e imprime, para cada artefato, o bloco de
proveniência gravado — em JSON, YAML, Parquet, PDF e (com autorização explícita)
Pickle. Nada é escrito, renomeado ou removido.

Exemplos
--------
Uma pasta de resultado inteira::

    python scripts/show_metadata.py "C:/simulation_results/MGNPyEON/2026-08-10_18-43-23_..."

Um arquivo só::

    python scripts/show_metadata.py resultados.parquet

Auditar o que NÃO tem proveniência (arquivos anteriores à adoção)::

    python scripts/show_metadata.py --only-missing "C:/simulation_results/MGNPyEON"

Resumo de uma linha por arquivo, para varreduras grandes::

    python scripts/show_metadata.py --summary "C:/simulation_results/MGNPyEON"

Código de saída 0 se todos os artefatos inspecionados têm proveniência, 1 se
algum não tem.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Permite executar a partir do repositório, sem instalação prévia
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mathe_core_mlib.io.metadata_reader import find_identifying_fields, iter_artifacts, read_metadata  # noqa: E402

#: Campos mostrados no modo --summary, na ordem de interesse.
_SUMMARY_FIELDS = ("software", "software_version", "created_at", "git_commit")


def _format_block(metadata: dict[str, Any]) -> str:
    """
    Formata um bloco de proveniência de forma legível.

    Parameters
    ----------
    metadata : dict[str, Any]
        Bloco lido do artefato.

    Returns
    -------
    str
        Texto indentado, com valores compostos serializados em JSON.
    """
    largura = max(len(chave) for chave in metadata)
    linhas = []

    for chave in sorted(metadata):
        valor = metadata[chave]
        if isinstance(valor, (dict, list)):
            valor = json.dumps(valor, ensure_ascii=False)
        linhas.append(f"     {chave:<{largura}}  {valor}")

    return "\n".join(linhas)


def _format_summary(metadata: dict[str, Any]) -> str:
    """
    Monta o resumo de uma linha de um bloco de proveniência.

    Parameters
    ----------
    metadata : dict[str, Any]
        Bloco lido do artefato.

    Returns
    -------
    str
        Campos principais separados por barra vertical.
    """
    partes = [str(metadata[campo]) for campo in _SUMMARY_FIELDS if campo in metadata]

    # PDFs nao usam os nomes padronizados: cai no dicionario Info
    if not partes and "Creator" in metadata:
        partes = [str(metadata["Creator"]), str(metadata.get("CreationDate", ""))]

    return " | ".join(partes) if partes else "(bloco sem campos conhecidos)"


def main(argv: list[str] | None = None) -> int:
    """
    Ponto de entrada da CLI de visualização.

    Parameters
    ----------
    argv : list[str] or None, optional
        Argumentos de linha de comando. ``None`` usa ``sys.argv[1:]``.

    Returns
    -------
    int
        ``0`` se todo artefato inspecionado tem proveniência, ``1`` caso
        contrário ou se o caminho não existir.
    """
    parser = argparse.ArgumentParser(
        prog="show-metadata", description="Mostra os metadados de proveniencia de artefatos (somente leitura)."
    )
    parser.add_argument("paths", type=Path, nargs="*", help="arquivos ou pastas a inspecionar (padrao: diretorio atual)")
    parser.add_argument("--summary", action="store_true", help="uma linha por arquivo, em vez do bloco completo")
    parser.add_argument("--only-missing", action="store_true", help="lista apenas os artefatos SEM proveniencia")
    parser.add_argument("--privacy", action="store_true", help="lista apenas os campos que identificam pessoa/maquina")
    parser.add_argument("--no-recursive", action="store_true", help="nao desce nas subpastas")
    parser.add_argument("--allow-pickle", action="store_true", help="autoriza ler .pkl (desserializar executa codigo)")
    args = parser.parse_args(argv)

    alvos = args.paths or [Path.cwd()]
    total = com_meta = identificaveis = 0

    for alvo in alvos:
        try:
            artefatos = list(iter_artifacts(alvo, recursive=not args.no_recursive))
        except FileNotFoundError as exc:
            print(f"ERRO: {exc}")
            return 1

        print(f"\n{'=' * 72}\n{alvo}\n{'=' * 72}")

        if not artefatos:
            print("Nenhum artefato inspecionavel encontrado.")
            continue

        for artefato in artefatos:
            total += 1
            rotulo = artefato.relative_to(alvo) if alvo.is_dir() else artefato.name

            try:
                metadata = read_metadata(artefato, allow_pickle=args.allow_pickle)
            except ValueError as exc:
                # .pkl sem autorizacao: informa e segue, nao interrompe a varredura
                print(f"-- {rotulo}\n     {exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - arquivo corrompido nao pode parar a auditoria
                print(f"-- {rotulo}\n     ilegivel: {exc}")
                continue

            if metadata:
                com_meta += 1

                if args.privacy:
                    achados = find_identifying_fields(metadata)
                    identificaveis += len(achados)
                    if achados:
                        detalhe = "\n".join(f"     {chave}  ({motivo}): {metadata[chave]}" for chave, motivo in achados.items())
                        print(f"!! {rotulo}\n{detalhe}")
                    continue

                if args.only_missing:
                    continue

                cabecalho = f"OK {rotulo}"
                print(f"{cabecalho}\n     {_format_summary(metadata)}" if args.summary else f"{cabecalho}\n{_format_block(metadata)}")
            elif not args.privacy:
                # em modo privacidade, artefato sem metadados nao expoe nada: e ruido
                print(f"-- {rotulo}\n     SEM PROVENIENCIA")

    faltando = total - com_meta
    print(f"\n{'-' * 72}")

    if args.privacy:
        print(f"{total} artefato(s) inspecionado(s): {identificaveis} campo(s) identificavel(is) encontrado(s).")
        print("Para gerar dados sem o nome da maquina, defina MATHE_META_NO_HOSTNAME=1 antes de rodar a simulacao.")
        return 0 if identificaveis == 0 else 1

    print(f"{total} artefato(s) inspecionado(s): {com_meta} com proveniencia, {faltando} sem.")

    return 0 if faltando == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
