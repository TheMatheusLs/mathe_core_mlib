# Mathe Core MLIB (m-core-mlib)

Biblioteca base de utilitários matemáticos, físicos e ferramentas científicas desenvolvida para auxiliar simulações de redes ópticas (GNPy) e algoritmos de otimização durante o doutorado.

Desenvolvido por: **Matheus Lôbo dos Santos** (matheus.lobo@ufpe.br)

## Funcionalidades Principais

Esta biblioteca foca em conversões robustas e "fail-fast" (falha rápida) para evitar erros silenciosos em simulações longas.

### 1. Conversão de Potência (Segura)
Módulo: `mathe_core_mlib.math.converters`

Diferente de scripts comuns, estas funções aceitam um parâmetro `mode` para tratar valores inválidos (≤ 0):
- `mode='raise'` (Padrão): Interrompe a simulação imediatamente (Erro).
- `mode='warn'`: Emite um aviso e retorna `-inf`.
- `mode='ignore'`: Retorna `-inf` silenciosamente.

| Função | Entrada | Saída | Descrição |
| :--- | :--- | :--- | :--- |
| `watt2dbm` | Watts (W) | dBm | Converte potência linear para logarítmica. |
| `dbm2watt` | dBm | Watts (W) | Converte dBm para potência linear. |
| `watt2db` | Linear/Watts | dB | Conversão genérica linear para dB. |
| `db2watt` | dB | Linear/Watts | Conversão genérica dB para linear. |

### 2. Conversão de Espectro
Utiliza a constante `c` (velocidade da luz) do `scipy.constants` para máxima precisão.

- `freq_Hz_to_wavelength_m` / `wavelength_m_to_freq_Hz`
- `wavelength_nm_to_freq_Hz` / `freq_Hz_to_wavelength_nm`
- `freq_GHz_to_Hz` / `freq_Hz_to_GHz`

### 2. Conversão de Espectro
Utiliza a constante `c` (velocidade da luz) do `scipy.constants` para máxima precisão.

- `freq_Hz_to_wavelength_m` / `wavelength_m_to_freq_Hz`
- `wavelength_nm_to_freq_Hz` / `freq_Hz_to_wavelength_nm`
- `freq_GHz_to_Hz` / `freq_Hz_to_GHz`

## Instalação

```bash
python -3.11 -m venv PhDGNPyVenv
python -m pip install --upgrade pip setuptools wheel
```

Esta biblioteca deve ser instalada em **modo editável** para que alterações no código reflitam instantaneamente nos seus projetos de simulação.

```bash
pip install -e .
```

## Exemplos de Uso
### Conversões de Potência
```python
import numpy as np
from mathe_core_mlib.math import converters as cv

# --- Exemplo 1: Conversão de Potência ---
potencia_w = 0.001  # 1 mW = 1e-3 Watts
dbm = cv.watt2dbm(potencia_w)
print(f"{potencia_w} W = {dbm} dBm")
# Saída: 0.0 dBm

# --- Exemplo 2: Segurança de Dados (Erro proposital) ---
try:
    # Tenta converter 0 Watts (impossível em dBm)
    cv.watt2dbm(0, mode='raise')
except ValueError as e:
    print(f"Erro capturado com sucesso: {e}")

# --- Exemplo 3: Conversão Espectral ---
c_band_start_nm = 1530
freq_hz = cv.wavelength_nm_to_freq_Hz(c_band_start_nm)
print(f"{c_band_start_nm} nm equivalem a {freq_hz/1e12:.2f} THz")
```

## Requisitos
- Python >= 3.9
- Numpy
- Scipy
