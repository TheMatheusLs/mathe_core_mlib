"""
Módulo Fundamental de Conversões Matemáticas e Físicas.

Este módulo centraliza operações numéricas universais de conversão de grandezas
frequentes no domínio de telecomunicações, sistemas fotônicos e processamento de sinais. 
Implementado com suporte unificado a escalares em ponto flutuante, iteráveis base
do Python e tensores de álgebra vetorial (`numpy.ndarray`).

A conversão segue estritas políticas de invalidação de fronteiras nulas
(`NaN`, logaritmos matemáticos de números não-positivos), provendo modos 
declarativos para tratamento do comportamento divergente (`strict`, `warn`, `ignore`).

Routines
--------
Conversões Adimensionais
    lin2db : Converte um fator linear para a escala logarítmica (dB).
    db2lin : Retorna o fator logarítmico (dB) para sua escala linear real.

Conversões de Potência
    watt2dbm : Transfere potência dissipada de Watts (W) para decibel-miliwatt (dBm).
    dbm2watt : Desfaz a medida logarítmica (dBm) convertendo-a para Watts explícitos.
    watt2db : Deduz o ganho logarítmico com piso referencial em 1 Watt (dBW).
    db2watt : Restaura a potência em Watts (W) a partir da referência dBW.

Conversões Espectrais
    freq_Hz_to_wavelength_m : Deduz comprimento de onda (m) a partir da frequência de pulso (Hz).
    wavelength_m_to_freq_Hz : Identifica o oscilador em Hertz equivalente a um passo espacial (m).
    wavelength_nm_to_freq_Hz : Transforma medições macro (nm) de luz livre para largura em Hertz.
    freq_Hz_to_wavelength_nm : Extrai o limite de onda nanométrico padrão de indústria da banda (Hz).
    freq_GHz_to_Hz : Expande gigahertz computacionais restritos de volta aos hertz puros.
    freq_Hz_to_GHz : Empacota escalas da banda larga do espectro oscilatório em prefixo giga (GHz).
"""

import warnings
from typing import Literal
import numpy as np
import numpy.typing as npt
from scipy.constants import c as SPEED_OF_LIGHT

ArrayLike = float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64] | npt.NDArray[np.int_]
ErrorMode = Literal['raise', 'warn', 'ignore']


# ==========================================
# Funções Auxiliares de Segurança
# ==========================================

def _validate_positive(value: npt.NDArray[np.float64], mode: ErrorMode, context: str) -> None:
    r"""
    Valida se os array fornecidos são compostos apenas por valores estritamente positivos.

    Parameters
    ----------
    value : npt.NDArray[np.float64]
        O array numpy contendo os valores a serem validados.
    mode : Literal['raise', 'warn', 'ignore']
        O comportamento que a função deve assumir caso encontre valores <= 0 ou NaN.
        - 'raise': Levanta um `ValueError`.
        - 'warn': Emite um `RuntimeWarning`.
        - 'ignore': Silencia o erro e retorna silenciosamente.
    context : str
        Nome do contexto/função que invocou essa validação, útil para compor a mensagem de erro.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        Se `mode == 'raise'` e algum elemento no array for menor ou igual a zero, ou for `NaN`.

    Notes
    -----
    Esta função foi projetada para atuar em domínios físicos (ex: distâncias e frequências físicas) 
    onde valores negativos não possuem sentido matemático ou físico para a computação.
    """
    if mode == 'ignore':
        return

    if np.any(value <= 0) or np.any(np.isnan(value)):
        msg = (f"Entrada inválida em '{context}': valores devem ser estritamente positivos (> 0). "
               f"Encontrados valores <= 0 ou NaN.")
        
        if mode == 'raise':
            raise ValueError(msg)
        elif mode == 'warn':
            warnings.warn(msg, RuntimeWarning)


# ==========================================
# Conversões Genéricas (Adimensionais: Ganho, SNR)
# ==========================================

def lin2db(value: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Converte um valor linear (adimensional) para a escala decibel (dB).

    Aplicável para medidas de ganho, Razão Sinal-Ruído Óptica (OSNR), Razão Sinal-Ruído Generalizada (GSNR), 
    ou qualquer outra variável de razão de potências.

    Parameters
    ----------
    value : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Valor numérico (ou coleção de valores numéricos) em escala linear linear que se 
        deseja converter. Deve ser um valor positivo.
    mode : Literal['raise', 'warn', 'ignore'], optional
        Ação a tomar os valores não forem estritamente positivos (> 0). Padrão é `'raise'`.

    Returns
    -------
    float | npt.NDArray[np.float64]
        Se `value` for um escalar, retorna um primitivo `float` em dB. Se `value` 
        for um iterável ou array, retorna um novo `npt.NDArray[np.float64]` com as conversões aplicadas em dB.

    Raises
    ------
    ValueError
        Se `mode == 'raise'` e os valores não forem positivos.

    Notes
    -----
    A fórmula para converter um ratio/fator linear para decibéis (dB) é dada por:

    $$ dB = 10 \log_{10}(value) $$

    Examples
    --------
    >>> import numpy as np
    >>> lin2db(10)
    10.0
    >>> lin2db([1, 10, 100])
    array([ 0., 10., 20.])
    """
    value_arr = np.asanyarray(value, dtype=np.float64)
    _validate_positive(value_arr, mode, context='lin2db')

    with np.errstate(divide='ignore', invalid='ignore'):
        result = 10.0 * np.log10(value_arr)

    return float(result.item()) if result.ndim == 0 else result


def db2lin(value_db: ArrayLike) -> float | npt.NDArray[np.float64]:
    r"""
    Converte um fator da escala logarítmica (dB) para escala linear (adimensional).

    Parameters
    ----------
    value_db : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        O valor na escala de decibéis (dB) a ser revertido para número linear.

    Returns
    -------
    float | npt.NDArray[np.float64]
        O fator convertido em escala linear. Retorna um primitivo `float` escalar, 
        ou array multi-dimensional a depender de `value_db`.

    Notes
    -----
    Matematicamente, desfaz-se a lógica da base 10 atenuada/amplificada:
    
    $$ Linear = 10^{\frac{value_{dB}}{10}} $$

    Examples
    --------
    >>> import numpy as np
    >>> db2lin(10.0)
    10.0
    >>> db2lin(np.array([0, 10, 20]))
    array([  1.,  10., 100.])
    """
    value_db_arr = np.asanyarray(value_db, dtype=np.float64)
    result = 10.0 ** (value_db_arr / 10.0)
    return float(result.item()) if result.ndim == 0 else result


# ==========================================
# Conversões de Potência (Watts, dBm)
# ==========================================

def watt2dbm(power_watt: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Converte potência explícita de Watts (W) para decibel-miliwatt (dBm).

    Parameters
    ----------
    power_watt : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        A potência bruta dissipada em unidades Watts (W). Deve ser $> 0$.
    mode : Literal['raise', 'warn', 'ignore'], optional
        Comportamento para tratamento de entradas não estritamente positivas. O padrão é `'raise'`.

    Returns
    -------
    float | npt.NDArray[np.float64]
        A potência calculada na escala logarítmica em referência a 1 miliwatt (dBm).

    Raises
    ------
    ValueError
        Se for alimentada uma potência $\\leq 0$ sob `mode='raise'`.

    Notes
    -----
    A fórmula da conversão de Watts para a escala em dBm exige o shift originário do milésimo 
    (fator de $+30$ dB):

    $$ P_{dBm} = 10 \log_{10}(P_W) + 30 $$

    Examples
    --------
    >>> watt2dbm(1e-3) # 1 mW exato  
    0.0
    >>> watt2dbm(1) # 1 Watt
    30.0
    """
    value_arr = np.asanyarray(power_watt, dtype=np.float64)
    _validate_positive(value_arr, mode, context='watt2dbm')

    with np.errstate(divide='ignore', invalid='ignore'):
        result = 10.0 * np.log10(value_arr) + 30.0

    return float(result.item()) if result.ndim == 0 else result


def dbm2watt(power_dbm: ArrayLike) -> float | npt.NDArray[np.float64]:
    r"""
    Converte sinal de potência da escala logarítmica (dBm) para escala linear real em Watts (W).

    Parameters
    ----------
    power_dbm : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Potência a ser mapeada de volta da escala dBm.

    Returns
    -------
    float | npt.NDArray[np.float64]
        Potência recuperada no domínio linear explícito (Watts).

    Notes
    -----
    Cálculo exato de regressão da amplificação decibel miliwatt de volta ao Watt (linear):
    
    $$ P_{W} = 10^{\\frac{P_{dBm} - 30}{10}} $$

    Examples
    --------
    >>> round(dbm2watt(0.0), 4) # 0 dBm
    0.001
    """
    value_db_arr = np.asanyarray(power_dbm, dtype=np.float64)
    result = 10.0 ** ((value_db_arr - 30.0) / 10.0)
    return float(result.item()) if result.ndim == 0 else result


def watt2db(power_watt: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Converte grandeza de potência base (Watts) para decibel referido a 1 Watt (dBW).

    Parameters
    ----------
    power_watt : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        O sinal bruto de energia do sistema fotônico ou elétrico em Watt ($> 0$).
    mode : Literal['raise', 'warn', 'ignore'], optional
        Como lidar com dados faltantes ($<=0$ ou `NaN`). Padrão `'raise'`.

    Returns
    -------
    float | npt.NDArray[np.float64]
        Medida extraída em decibéis por Watt.

    Raises
    ------
    ValueError
        Com o `mode='raise'`, falha em vetores com zeros reais, impedindo $-\\infty$ no logaritmo.

    Notes
    -----
    Matematicamente análogo à função genérica `lin2db`. Seu uso existe puramente 
    por clareza e separação semântica das varíaveis de estado e medição:

    $$ P_{dBW} = 10 \log_{10}(P_W) $$

    Examples
    --------
    >>> watt2db(1.0)
    0.0
    >>> watt2db(10)
    10.0
    """
    return lin2db(power_watt, mode=mode)


def db2watt(value_db: ArrayLike) -> float | npt.NDArray[np.float64]:
    r"""
    Converte medição em dB (decibel watt, ou dBW) para Watts explícitos no sistema internacional (W).

    Parameters
    ----------
    value_db : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Nível do sinal aferido com piso relacional à 1 W (0 dB).

    Returns
    -------
    float | npt.NDArray[np.float64]
        O respectivo valor linear explícito desimpedido de piso logarítmico.

    Notes
    -----
    Matematicamente análogo à função genérica `db2lin`. Seu uso existe puramente 
    por clareza e separação semântica das varíaveis de estado e medição:

    Examples
    --------
    >>> db2watt(0.0)
    1.0
    """
    return db2lin(value_db)


# ==========================================
# Conversões de Frequência e Comprimento de Onda
# ==========================================

def freq_Hz_to_wavelength_m(freq_Hz: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Converte a frequência f (em Hertz) de um espectro luminoso para o seu comprimento de onda $\\lambda$ equivalente em metros (m).

    Parameters
    ----------
    freq_Hz : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        A frequência portadora ou base do sinal em unidades de Hz.
    mode : Literal['raise', 'warn', 'ignore'], optional
        Estratégia usada pela filtragem interna em caso de anomalias (Frequência nula ou negativa levam à singularidade no comprimento).

    Returns
    -------
    float | npt.NDArray[np.float64]
        O comprimento do trajeto de onda eletromagnética quantificado perfeitamente em metros (m).

    Raises
    ------
    ValueError
        Se for solicitada uma conversão baseada em zeros ou valores negativos (`mode='raise'`).

    Notes
    -----
    A ligação termodinâmica de frequências de pulsos e comprimento linear no vácuo obedece:

    $$ \\lambda_m = \\frac{c}{f_{Hz}} $$

    Sendo `c` a velocidade da luz constante definida em $299\\,792\\,458$ m/s via módulo Scipy.

    Examples
    --------
    >>> round(freq_Hz_to_wavelength_m(193.1e12), 9)
    1.55252e-06
    """
    freq_arr = np.asanyarray(freq_Hz, dtype=np.float64)
    _validate_positive(freq_arr, mode, context='freq_Hz_to_wavelength_m')
    
    with np.errstate(divide='ignore'):
        result = SPEED_OF_LIGHT / freq_arr
        
    return float(result.item()) if result.ndim == 0 else result


def wavelength_m_to_freq_Hz(wavelength_m: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Converte um determinado comprimento de onda da luz do espaço livre, denotado em metros, para o seu sinal oscilatório correspondente em Hertz.

    Parameters
    ----------
    wavelength_m : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        A métrica física e geométrica da oscilação de pico, extraída em metros no sistema métrico.
    mode : Literal['raise', 'warn', 'ignore'], optional
        Como prevenir a singularidade ou distorção real que a ausência do sinal (0 m), ou um comprimento negativo, carrega ao cálculo físico. Padrão: `'raise'`.

    Returns
    -------
    float | npt.NDArray[np.float64]
        A frequência deduzida na ordem do pulso espectral.

    Raises
    ------
    ValueError
        Lançado primariamente se o comprimento linear for fisicamente proibitivo ($<0$).

    Notes
    -----
    Transformação algébrica trivial extraída da luz `c`:
    $$ f_{Hz} = \\frac{c}{\\lambda_m} $$

    Examples
    --------
    >>> res = wavelength_m_to_freq_Hz(1.55e-6)
    >>> round(res / 1e12, 1) # Imprime Terahertz
    193.4
    """
    wl_arr = np.asanyarray(wavelength_m, dtype=np.float64)
    _validate_positive(wl_arr, mode, context='wavelength_m_to_freq_Hz')
    
    with np.errstate(divide='ignore'):
        result = SPEED_OF_LIGHT / wl_arr
        
    return float(result.item()) if result.ndim == 0 else result


def wavelength_nm_to_freq_Hz(wavelength_nm: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Identifica a frequência analógica equivalente de rede em Hertz, através base em nanômetros.

    Parameters
    ----------
    wavelength_nm : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Magnitude analítica da onda em precisão macro ou nano sub-atômica dependendo dos sistemas. No caso específico em fator fixo do Nanômetro ($10^{-9}$ m).
    mode : Literal['raise', 'warn', 'ignore'], optional
        Lida ativamente com divisões sobre elementos de comprimento igual a zero.

    Returns
    -------
    float | npt.NDArray[np.float64]
        As frequências calculadas referenciando o mesmo sinal em Hz absolutos.

    Notes
    -----
    É aplicada uma substituição relacional da unidade base convertida dinamicamente durante operação:
    
    $$ f_{Hz} = \\frac{c}{\\lambda_{nm} \\times 10^{-9}} $$

    Examples
    --------
    >>> round(wavelength_nm_to_freq_Hz(1550) / 1e12, 2)
    193.41
    """
    wl_nm_arr = np.asanyarray(wavelength_nm, dtype=np.float64)
    _validate_positive(wl_nm_arr, mode, context='wavelength_nm_to_freq_Hz')
    
    with np.errstate(divide='ignore'):
        # nm para m: * 1e-9
        result = SPEED_OF_LIGHT / (wl_nm_arr * 1e-9)
        
    return float(result.item()) if result.ndim == 0 else result


def freq_Hz_to_wavelength_nm(freq_Hz: ArrayLike, mode: ErrorMode = 'raise') -> float | npt.NDArray[np.float64]:
    r"""
    Expressa as amplitudes da frequência (Hz) na métrica padrão consolidada da indústria ótica de nanômetros (nm).

    Parameters
    ----------
    freq_Hz : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Escala original do oscilador eletromagnético.
    mode : Literal['raise', 'warn', 'ignore'], optional
        Verificação semântica do intervalo numérico no mapeamento.

    Returns
    -------
    float | npt.NDArray[np.float64]
        Os comprimentos dimensionais do sinal subavaliados na faixa da macro unidade fixa 10^-9.

    Notes
    -----
    Cálculo linear de manipulação numérica a base da conversão central para metros e extração multiplicativa do fator 9:
    
    $$ \\lambda_{nm} = \\left( \\frac{c}{f_{Hz}} \\right) \\times 10^{9} $$

    Examples
    --------
    >>> res_nm = freq_Hz_to_wavelength_nm(193.1e12)
    >>> round(res_nm, 2)
    1552.52
    """
    freq_arr = np.asanyarray(freq_Hz, dtype=np.float64)
    _validate_positive(freq_arr, mode, context='freq_Hz_to_wavelength_nm')
    
    with np.errstate(divide='ignore'):
        # mt para nm: * 1e9
        result = (SPEED_OF_LIGHT / freq_arr) * 1e9
        
    return float(result.item()) if result.ndim == 0 else result


def freq_GHz_to_Hz(freq_GHz: ArrayLike) -> float | npt.NDArray[np.float64]:
    r"""
    Desempacota medições macro representadas nos Gigahertz computacionais de volta aos Hertz primitivos físicos.

    Parameters
    ----------
    freq_GHz : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Unidade na escala dos Giga métricos (GHz).

    Returns
    -------
    float | npt.NDArray[np.float64]
        O número linear que retrata a unidade bruta Hz.

    Notes
    -----
    Expansão direta multiplicativa: $Hz = GHz \\times 10^{9}$.
    
    Examples
    --------
    >>> freq_GHz_to_Hz(50.0)
    50000000000.0
    """
    freq_GHz_arr = np.asanyarray(freq_GHz, dtype=np.float64)
    result = freq_GHz_arr * 1e9
    return float(result.item()) if result.ndim == 0 else result


def freq_Hz_to_GHz(freq_Hz: ArrayLike) -> float | npt.NDArray[np.float64]:
    r"""
    Empacota grandes matrizes de Hertz no seu prefixo correspondente Gigahertz.

    Parameters
    ----------
    freq_Hz : float | int | list[float] | tuple[float, ...] | npt.NDArray[np.float64]
        Sinais com unidades reais (Hz).

    Returns
    -------
    float | npt.NDArray[np.float64]
        Resultante normalizado com escala dos $10^{-9}$ da computação física teórica diária (GHz).

    Notes
    -----
    Contrações de log direto: $GHz = \\frac{Hz}{10^{9}}$.

    Examples
    --------
    >>> freq_Hz_to_GHz(193100000000000.0)
    193100.0
    """
    freq_Hz_arr = np.asanyarray(freq_Hz, dtype=np.float64)
    result = freq_Hz_arr / 1e9
    return float(result.item()) if result.ndim == 0 else result