# mathe_core_mlib

## O que é
Biblioteca base compartilhada entre os projetos de simulação de redes ópticas.
Reúne I/O de arquivos com proveniência, conversões físicas (dB/Watt/Hz/nm),
gerência de pastas de experimento e o estilo acadêmico das figuras.

## Para que serve
Evitar que cada simulador reimplemente leitura/escrita, conversão de unidades e
padrão visual das figuras — e garantir que todo artefato gerado para a tese
carregue registro de quem o produziu.

## Quem consome
- Consumido por: `MGNPyEONv3`, `GA_with_GNPy_classes`, `OpticalSimMBEON`,
  `modulesGNPy_mlib` (todos via path dependency do Poetry).
- Depende de: nada local. Só bibliotecas de terceiros (Polars, NumPy, SciPy,
  Matplotlib, PyYAML).

## Importante
- **Proveniência é obrigatória.** Desde a v3.0.0, todo `save_*` exige o argumento
  `version` e grava um bloco de metadados (`_meta` em JSON/YAML/Pickle, schema
  Arrow em Parquet, sidecar `.meta.json` em figuras). Esquecer a versão levanta
  `TypeError` — é intencional.
- Os `load_*` removem o `_meta` antes de devolver os dados; use `return_meta=True`
  para acessá-lo.
- **Esta lib existe em dois checkouts no disco** (`project/mathe_core_mlib` e o
  submódulo `MGNPyEONv3/modules/mathe_core_mlib`), que costumam ficar em commits
  diferentes. Editar sempre o que estiver à frente e propagar para o submódulo.
- `snapshot_environment()` depende do binário **`uv`** no PATH, apesar de o
  projeto ser gerenciado por Poetry; sem `uv`, retorna `None`.
- `setup_academic_style()` liga `text.usetex=True`: exige LaTeX instalado
  (`mathptmx`, `amsmath`) e a fonte Times New Roman.
