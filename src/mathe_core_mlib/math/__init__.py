from .converters import (
    db2lin,
    db2watt,
    dbm2watt,
    freq_GHz_to_Hz,
    freq_Hz_to_GHz,
    freq_Hz_to_wavelength_m,
    freq_Hz_to_wavelength_nm,
    lin2db,
    watt2db,
    watt2dbm,
    wavelength_m_to_freq_Hz,
    wavelength_nm_to_freq_Hz,
)

# Re-exports deliberados: o pacote é a API pública das conversões
__all__ = [
    "db2lin",
    "db2watt",
    "dbm2watt",
    "freq_GHz_to_Hz",
    "freq_Hz_to_GHz",
    "freq_Hz_to_wavelength_m",
    "freq_Hz_to_wavelength_nm",
    "lin2db",
    "watt2db",
    "watt2dbm",
    "wavelength_m_to_freq_Hz",
    "wavelength_nm_to_freq_Hz",
]
