#!/usr/bin/env python
"""
Diagnostica os submódulos git de um ou mais projetos.

Roda direto deste repositório, sem exigir que a `mathe_core_mlib` esteja
instalada no ambiente do projeto alvo — útil para inspecionar simuladores que
ainda não foram migrados, ou cujo venv está quebrado.

Exemplos
--------
Diagnosticar um simulador::

    python scripts/check_modules.py ../MGNPyEONv3

Varrer vários de uma vez, consultando os remotos::

    python scripts/check_modules.py --fetch ../MGNPyEONv3 ../OpticalSimMBEON ../GA_with_GNPy_classes

Sem argumentos, diagnostica o diretório atual::

    python scripts/check_modules.py

Código de saída 0 se todos os projetos estão em estado reproduzível, 1 caso
contrário — dá para encadear em pre-commit ou CI.
"""

import sys
from pathlib import Path

# Permite executar a partir do repositório, sem instalação prévia
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mathe_core_mlib.io.submodules import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
