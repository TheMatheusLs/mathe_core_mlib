import numpy as np
import warnings
from typing import Union, List, Literal
from scipy.constants import c as SPEED_OF_LIGHT


# Define tipos para Type Hinting
ArrayLike = Union[float, int, List[float], np.ndarray]
ErrorMode = Literal['raise', 'warn', 'ignore']


# ==========================================
# Funções Auxiliares de Segurança
# ==========================================

def _validate_positive(value: np.ndarray, mode: ErrorMode, context: str):
    """
    Valida se os valores são estritamente positivos.
    """
    if mode == 'ignore':
        return

    if np.any(value <= 0):
        msg = (f"Entrada inválida em '{context}': valores devem ser estritamente positivos (> 0). "
               f"Encontrados valores <= 0 ou NaN.")
        
        if mode == 'raise':
            raise ValueError(msg)
        elif mode == 'warn':
            warnings.warn(msg, RuntimeWarning)


# ==========================================
# Conversões Genéricas (Adimensionais: Ganho, SNR)
# ==========================================

def lin2db(value: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """
    Converte valor linear (adimensional) para dB.
    Útil para Ganho, OSNR, GSNR.
    Fórmula: 10 * log10(value)

    Args:
        value: Valor linear ou array.
        mode: 'raise', 'warn', 'ignore'.
    """
    value = np.asanyarray(value, dtype=float)
    _validate_positive(value, mode, context='lin2db')

    with np.errstate(divide='ignore', invalid='ignore'):
        result = 10 * np.log10(value)

    return result.item() if result.ndim == 0 else result


def db2lin(value_db: ArrayLike) -> Union[float, np.ndarray]:
    """
    Converte valor em dB para escala linear (adimensional).
    Fórmula: 10^(value_db / 10)
    """
    value_db = np.asanyarray(value_db, dtype=float)
    result = 10 ** (value_db / 10.0)
    return result.item() if result.ndim == 0 else result


# ==========================================
# Conversões de Potência (Watts, dBm)
# ==========================================

def watt2dbm(power_watt: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """
    Converte potência em Watts para dBm.
    Fórmula: 10 * log10(power_watt) + 30
    """
    value = np.asanyarray(power_watt, dtype=float)
    _validate_positive(value, mode, context='watt2dbm')

    with np.errstate(divide='ignore', invalid='ignore'):
        result = 10 * np.log10(value) + 30.0

    return result.item() if result.ndim == 0 else result


def dbm2watt(power_dbm: ArrayLike) -> Union[float, np.ndarray]:
    """
    Converte potência em dBm para Watts.
    Fórmula: 10 ** ((dBm - 30) / 10)
    """
    value_db = np.asanyarray(power_dbm, dtype=float)
    result = 10 ** ((value_db - 30.0) / 10.0)
    return result.item() if result.ndim == 0 else result


def watt2db(power_watt: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """
    Converte valor watt para dB (dBW).
    Fórmula: 10 * log10(power_watt)
    
    Nota: Matematicamente idêntico a lin2db, mas semanticamente usado para Potência.
    """
    return lin2db(power_watt, mode=mode)


def db2watt(value_db: ArrayLike) -> Union[float, np.ndarray]:
    """
    Converte valor em dB (dBW) para watt.
    Fórmula: 10^(value_db / 10)
    """
    return db2lin(value_db)


# ==========================================
# Conversões de Frequência e Comprimento de Onda
# ==========================================

def freq_Hz_to_wavelength_m(freq_Hz: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """Converte Frequência (Hz) -> Comprimento de onda (m)."""
    freq = np.asanyarray(freq_Hz, dtype=float)
    _validate_positive(freq, mode, context='freq_Hz_to_wavelength_m')
    
    with np.errstate(divide='ignore'):
        result = SPEED_OF_LIGHT / freq
        
    return result.item() if result.ndim == 0 else result


def wavelength_m_to_freq_Hz(wavelength_m: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """Converte Comprimento de onda (m) -> Frequência (Hz)."""
    wl = np.asanyarray(wavelength_m, dtype=float)
    _validate_positive(wl, mode, context='wavelength_m_to_freq_Hz')
    
    with np.errstate(divide='ignore'):
        result = SPEED_OF_LIGHT / wl
        
    return result.item() if result.ndim == 0 else result


def wavelength_nm_to_freq_Hz(wavelength_nm: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """Converte Comprimento de onda (nm) -> Frequência (Hz)."""
    wl_nm = np.asanyarray(wavelength_nm, dtype=float)
    _validate_positive(wl_nm, mode, context='wavelength_nm_to_freq_Hz')
    
    with np.errstate(divide='ignore'):
        # nm para m: * 1e-9
        result = SPEED_OF_LIGHT / (wl_nm * 1e-9)
        
    return result.item() if result.ndim == 0 else result


def freq_Hz_to_wavelength_nm(freq_Hz: ArrayLike, mode: ErrorMode = 'raise') -> Union[float, np.ndarray]:
    """Converte Frequência (Hz) -> Comprimento de onda (nm)."""
    freq = np.asanyarray(freq_Hz, dtype=float)
    _validate_positive(freq, mode, context='freq_Hz_to_wavelength_nm')
    
    with np.errstate(divide='ignore'):
        # m para nm: * 1e9
        result = (SPEED_OF_LIGHT / freq) * 1e9
        
    return result.item() if result.ndim == 0 else result


def freq_GHz_to_Hz(freq_GHz: ArrayLike) -> Union[float, np.ndarray]:
    """Converte GHz -> Hz."""
    return np.asanyarray(freq_GHz, dtype=float) * 1e9


def freq_Hz_to_GHz(freq_Hz: ArrayLike) -> Union[float, np.ndarray]:
    """Converte Hz -> GHz."""
    return np.asanyarray(freq_Hz, dtype=float) / 1e9