# Mathe Core MLIB (`mathe-core-mlib`)

Biblioteca modular de alta performance e utilitários científicos desenvolvida para suportar simulações de redes ópticas (foco em GNPy), algoritmos de otimização e gestão de dados experimentais.

Desenvolvido por: **Matheus Lôbo dos Santos** (matheus.lobo@ufpe.br)

## Funcionalidades Principais
A `mathe-core-mlib` foi construída sob o princípio de **Fail-Fast (Falha Rápida)**. Em simulações científicas de longa duração, erros silenciosos (como um valor logarítmico de zero ou um diretório não criado) podem invalidar dias de processamento. Esta biblioteca garante a integridade dos dados através de validações rigorosas e automação de IO.

---

## Estrutura do Pacote

A biblioteca está organizada em subcomponentes lógicos:
- `mathe_core_mlib.math`: Conversões físicas e matemáticas (vetorizadas com NumPy).
- `mathe_core_mlib.io`: Persistência de arquivos e gestão de ciclo de vida de experimentos.

---

## 1. Conversões de Telecomunicações e Física
Módulo: `mathe_core_mlib.math.converters`

Diferente de scripts comuns, estas funções aceitam um parâmetro `mode` para tratar valores inválidos (≤ 0):
- `mode='raise'` (Padrão): Interrompe a simulação imediatamente (Erro).
- `mode='warn'`: Emite um aviso e retorna `-inf`.
- `mode='ignore'`: Retorna `-inf` silenciosamente.

### Potência e Ganho
| Função | Unidade Entrada | Unidade Saída | Descrição |
| :--- | :--- | :--- | :--- |
| `lin2db` | Linear | dB | Conversão genérica (10 log10). |
| `db2lin` | dB | Linear | Conversão genérica (10^(x/10)). |
| `watt2dbm` | Watts (W) | dBm | Escala de potência óptica. |
| `dbm2watt` | dBm | Watts (W) | Escala de potência óptica. |
| `watt2db` | Watts (W) | dB | Idêntico ao `lin2db`. |
| `db2watt` | dB | Watts (W) | Idêntico ao `db2lin`. |

### Espectro e Comprimento de Onda
Utiliza a constante física `SPEED_OF_LIGHT` da `scipy.constants`.

| Função | De | Para |
| :--- | :--- | :--- |
| `freq_Hz_to_wavelength_nm` | Hertz (Hz) | Nanômetros (nm) |
| `freq_Hz_to_wavelength_m` | Hertz (Hz) | Metros (m) |
| `wavelength_nm_to_freq_Hz` | Nanômetros (nm) | Hertz (Hz) |
| `wavelength_m_to_freq_Hz` | Metros (m) | Hertz (Hz) |
| `freq_GHz_to_Hz` | Gigahertz (GHz) | Hertz (Hz) |
| `freq_Hz_to_GHz` | Hertz (Hz) | Gigahertz (GHz) |

---

## 2. Gestão de Experimentos
Módulo: `mathe_core_mlib.io.folders`

A classe `ExperimentFolder` automatiza a organização de resultados, garantindo que cada execução seja única e rastreável.

**Recursos:**
- Criação automática de pastas com timestamp: `YYYY-MM-DD_HH-MM-SS_v1_Tag`.
- Renomeação automática ao final do processo (`_Success` ou `_Fail`).
- Snapshot de logs e arquivos de configuração integrados.

---

## 3. Persistência de Dados (IO)
Módulo: `mathe_core_mlib.io.files`

Wrappers robustos para leitura e escrita que garantem codificação `UTF-8` e criação automática de diretórios pais (`parent directories`) para evitar `FileNotFoundError`.

- **Formatos suportados:** JSON, YAML, Pickle (.pkl) e CSV (via Pandas).

---

## Instalação

### Requisitos de Ambiente
- Python >= 3.9
- Dependências: `numpy`, `scipy`, `pandas`, `pyyaml`

### Construção de Ambiente Virtual

```bash
python -3.11 -m venv PhDGNPyVenv
python -m pip install --upgrade pip setuptools wheel
```

### Modo de Desenvolvimento (Recomendado)
Para garantir que suas melhorias na biblioteca sejam aplicadas imediatamente às simulações:

```bash
git clone git@github.com:seu-usuario/mathe-core-mlib.git
cd mathe-core-mlib
pip install -e .
```

---

## Exemplos de Uso Profissional

### Organizando uma Simulação de Doutorado
```python
from mathe_core_mlib.io.folders import ExperimentFolder
from mathe_core_mlib.math import converters as cv

# 1. Setup do Experimento
exp = ExperimentFolder(base_path="./results", tag="GA_Optimization", version="v2")

try:
    # 2. Lógica de Simulação
    power_dbm = 3.0
    power_watt = cv.dbm2watt(power_dbm)
    
    # 3. Salvar Resultados
    log_path = exp.get_logging_path("metrics.txt")
    exp.save_text("summary.txt", f"Potência utilizada: {power_watt} W")
    
    exp.finish(status="success")
except Exception as e:
    exp.finish(status="fail", info_msg=str(e))
```

### Conversão Vetorizada (NumPy)
```python
import numpy as np
from mathe_core_mlib.math import converters as cv

frequencias_ghz = np.array([193100, 193200, 193300])
lambdas_nm = cv.freq_Hz_to_wavelength_nm(cv.freq_GHz_to_Hz(frequencias_ghz))
# Retorna array: [1552.52, 1551.72, 1550.92]
```

## Licença
Uso acadêmico
