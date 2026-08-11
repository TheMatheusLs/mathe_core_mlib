# Changelog

Todas as mudanças relevantes desta biblioteca. Os artefatos gravados em disco
carregam a versão do software que os gerou, então cada entrada aqui corresponde
a um conjunto de arquivos rastreável.

## [3.3.0] - 2026-08-10

### Adicionado

- Módulo `io/submodules.py`: diagnóstico de submódulos git, reutilizável por
  qualquer simulador. Nasceu como script local do `MGNPyEONv3` e foi generalizado
  — o layout dos submódulos vem do `.gitmodules` (via `git config`), não de uma
  pasta `modules/` presumida, e a raiz do repositório é detectada sozinha.
  Responde as três perguntas que `git submodule status` confunde: se o ponteiro
  bate com a pasta, se o commit fixado é o mais recente do remoto, e se esse
  commit chegou a ser publicado.
- **`scripts/check_modules.py`**: script executável direto deste repositório,
  sem exigir que a lib esteja instalada no ambiente do projeto alvo — serve para
  inspecionar simuladores ainda não migrados ou com venv quebrado.
- A CLI aceita **vários projetos numa chamada só**
  (`python scripts/check_modules.py --fetch ../MGNPyEONv3 ../OpticalSimMBEON`).
  Cada projeto é avaliado de forma independente: um que falhe não interrompe a
  varredura dos demais, e o código de saída (0/1) permite encadear em CI.
- Também disponível como `python -m mathe_core_mlib.io.submodules` e como
  console script `check-modules`, para os projetos que instalam a lib.

### Notas

- `ModuleState.is_healthy` exige `checkout_commit` não vazio. Sem isso, um
  submódulo declarado mas nunca inicializado passava como saudável, porque o
  commit registrado e o do disco ficam ambos vazios e "coincidem". Encontrado
  por teste.
- Repositórios sem submódulos são tratados explicitamente, não como erro.

## [3.1.0] - 2026-08-10

### Adicionado

- `save_figure` aceita `dpi: int | None`. O valor só é repassado ao Matplotlib
  quando explícito; `None` mantém `rcParams["savefig.dpi"]`. Existe para que
  chamadores que já fixavam um DPI (como o `plot_scenario_allocation` do
  `gnpy_mlab`) possam migrar para o `save_figure` sem alterar a saída.

## [3.0.0] - 2026-08-10

### BREAKING

- **Proveniência obrigatória em todo `save_*`.** As funções `save_json`,
  `save_yaml`, `save_pickle`, `save_parquet` e `save_figure` passam a exigir o
  argumento posicional `version`. Omiti-lo levanta `TypeError` na chamada — não
  é mais possível gravar um artefato sem registrar quem o gerou.
- **`save_pickle` grava um envelope** `{"_meta": ..., "_data": <objeto>}`.
  `load_pickle` desfaz o envelope automaticamente e continua lendo arquivos
  antigos (sem envelope) sem alteração no chamador.
- **`save_figure` mudou de assinatura**: `save_figure(fig, path, version, *, software=None, extra_meta=None, pgf=False)`.

### Adicionado

- Módulo `io/provenance.py`: monta o bloco de metadados comum a todos os
  formatos (`created_at` em UTC ISO 8601, `software_version`, `software`,
  `git_commit`, `git_dirty`, `python_version`, `platform` + campos extras).
  O estado do git é consultado uma única vez por processo (`lru_cache`), para
  que salvar em laço não dispare subprocessos por arquivo.
- `save_parquet`: persistência de `pl.DataFrame` com compressão `zstd` e
  proveniência no key-value store do schema Arrow — sem colunas extras.
- `load_parquet(..., return_meta=True)`: devolve os metadados de schema,
  omitindo a chave interna `ARROW:schema` do Polars.
- `load_json`/`load_yaml`/`load_pickle` aceitam `return_meta=True` para acessar
  o bloco de proveniência.
- `save_figure` grava um arquivo companheiro `<nome>.meta.json` com o registro
  estruturado completo, além de preencher o dicionário Info do PDF. O sidecar é
  o único canal de proveniência do `.pgf`, que não tem onde guardar metadados.
- Testes do novo contrato (obrigatoriedade da versão, round-trip sem vazamento
  do `_meta`, cache do git, compatibilidade com pickles antigos): a suíte passou
  de 90 para 113 casos, com `tests/test_io/test_provenance.py` e
  `tests/test_style/test_utils.py` novos — este último dá a primeira cobertura
  que o `save_figure` já teve.

### Corrigido

- `save_figure` não derruba mais a execução em console Windows cp1252. A
  mensagem usava emoji (`💾`) e estourava `UnicodeEncodeError` no meio da
  gravação; agora vai por `logging` (logger de módulo, sem handler próprio) e
  em ASCII puro. Coberto por teste de regressão.
- Doctest de `freq_Hz_to_wavelength_m`: `round(x, 9)` produz `1.553e-06`, não
  `1.55252e-06` como a docstring afirmava. Corrigido para `round(x, 11)`.
- Exemplos de `compare_yaml_files` e `compare_env_snapshots` marcados com
  `# doctest: +SKIP`: dependem de pastas reais em disco e o segundo falhava com
  `KeyError: 'Diferente'` ao rodar `pytest --doctest-modules`.
- Lint zerado no repositório: `__all__` explícito em `math/__init__.py` (os 12
  `F401` eram re-exports intencionais), três docstrings acima de 140 colunas
  quebradas em `converters.py`, e `folders.py`/`test_analysis.py` formatados.

### Alterado

- `load_json`/`load_yaml`/`load_pickle` removem o bloco `_meta` antes de
  devolver os dados, de modo que `load_x(save_x(d)) == d` continua valendo.
- `compare_yaml_files` ignora `_meta` por padrão: o bloco carrega timestamp e
  commit, que diferem entre execuções por construção e fariam toda comparação
  de configuração falhar.
- `save_yaml` passa a usar `allow_unicode=True` (acentos gravados literalmente,
  como já ocorria no JSON).
- `save_pickle` usa `pickle.HIGHEST_PROTOCOL`.

## [2.2.0]

- Correção do `__str__` de `ExperimentFolder`.
- `ExperimentFolder` cria pastas com nome único sob concorrência (`mkdir`
  atômico com sufixo numérico em caso de colisão de timestamp).
