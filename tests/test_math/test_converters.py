import pytest
import numpy as np
from numpy.testing import assert_allclose
from scipy.constants import c as SPEED_OF_LIGHT

from mathe_core_mlib.math.converters import (
    lin2db, db2lin, watt2dbm, dbm2watt, watt2db, db2watt,
    freq_Hz_to_wavelength_m, wavelength_m_to_freq_Hz,
    wavelength_nm_to_freq_Hz, freq_Hz_to_wavelength_nm,
    freq_GHz_to_Hz, freq_Hz_to_GHz, _validate_positive
)

# ==========================================
# Testes da Função Auxiliar (_validate_positive)
# ==========================================

class TestValidatePositive:
    @pytest.mark.parametrize("valid_val", [1.0, np.array([0.1, 100]), [1e-9, 5e12]])
    def test_positive_values_pass_silently(self, valid_val):
        """Arrays com valores estritamente positivos devem passar sem exceções."""
        _validate_positive(np.asanyarray(valid_val, dtype=np.float64), mode="raise", context="test")

    @pytest.mark.parametrize("invalid_val", [
        0.0, -10.0, np.array([10.0, -5.0]), [0, 5], np.nan, np.array([1, np.nan])
    ])
    def test_invalid_values_raise_value_error(self, invalid_val):
        """Valores nulos, negativos ou NaN devem levantar ValueError no modo 'raise'."""
        with pytest.raises(ValueError, match="estritamente positivos"):
            _validate_positive(np.asanyarray(invalid_val, dtype=np.float64), mode="raise", context="test")

    def test_invalid_values_emit_warning(self):
        """Deve emitir um RuntimeWarning se mode='warn'."""
        with pytest.warns(RuntimeWarning, match="estritamente positivos"):
            _validate_positive(np.array([-1.0]), mode="warn", context="test")

    def test_invalid_values_ignored(self):
        """Não deve levantar nada se mode='ignore', mesmo com erro explícito."""
        _validate_positive(np.array([-1.0]), mode="ignore", context="test")


# ==========================================
# Testes de Conversões Adimensionais (lin2db / db2lin)
# ==========================================

class TestGenericConversions:
    @pytest.mark.parametrize("linear, expected_db", [
        (1.0, 0.0),            # Identidade 0 dB
        (10.0, 10.0),          # Ganho na base decimal
        (100.0, 20.0),         # Dois Bels
        (0.5, -3.0102999566),  # Atenuação típica
        (1e6, 60.0),           # Escala absurda 
    ])
    def test_lin2db_happy_path(self, linear, expected_db):
        """Validação escalar exata de linearização acústica."""
        result = lin2db(linear)
        assert isinstance(result, float)
        assert_allclose(result, expected_db, rtol=1e-5)

    def test_lin2db_array_computation(self):
        """Suporte a vetorização cruzada (list e ndarray)."""
        inputs = [1.0, 10.0, 100.0]
        result = lin2db(inputs)
        assert isinstance(result, np.ndarray)
        assert_allclose(result, np.array([0.0, 10.0, 20.0]))

    def test_lin2db_overflow_extreme(self):
        """O logaritmo absorve perfeitamente valores matematicamente colossais."""
        assert_allclose(lin2db(1e200), 2000.0)
        
    @pytest.mark.parametrize("db_val, expected_lin", [
        (0.0, 1.0),
        (10.0, 10.0),
        (-3.0102999566, 0.5),
        (60.0, 1e6)
    ])
    def test_db2lin_happy_path(self, db_val, expected_lin):
        """Recuperação algébrica da transformação em base 10."""
        assert_allclose(db2lin(db_val), expected_lin, rtol=1e-5)


# ==========================================
# Testes de Potência (Watts, dBW, dBm)
# ==========================================

class TestPowerConversions:
    @pytest.mark.parametrize("watt, expected_dbm", [
        (1e-3, 0.0),        # 1 miliwatt = 0 dBm
        (1.0, 30.0),        # 1 watt = 30 dBm
        (10.0, 40.0),       # 10 watt = 40 dBm
        (1e-6, -30.0)       # 1 microwatt
    ])
    def test_watt_to_dbm(self, watt, expected_dbm):
        assert_allclose(watt2dbm(watt), expected_dbm)

    @pytest.mark.parametrize("dbm, expected_watt", [
        (0.0, 1e-3),
        (30.0, 1.0),
        (-30.0, 1e-6)
    ])
    def test_dbm_to_watt(self, dbm, expected_watt):
        assert_allclose(dbm2watt(dbm), expected_watt)

    def test_watt_dbw_conversions(self):
        """Garante que a semântica watt2db/db2watt espelhe as conversões genéricas de potência referida a 1W."""
        power_w = np.array([1.0, 10.0, 100.0])
        dbw_result = watt2db(power_w)
        assert_allclose(dbw_result, [0.0, 10.0, 20.0])
        assert_allclose(db2watt(dbw_result), power_w)


# ==========================================
# Conversões de Óptica e Espectro (Wavelength/Hz)
# ==========================================

class TestSpectrumConversions:
    # Banda C Típica: 193.1 THz ~= 1552.52... nm
    C_BAND_HZ = 193.1e12
    C_BAND_M = SPEED_OF_LIGHT / C_BAND_HZ
    C_BAND_NM = C_BAND_M * 1e9

    def test_freq_Hz_to_wavelength_m(self):
        result = freq_Hz_to_wavelength_m(self.C_BAND_HZ)
        assert_allclose(result, self.C_BAND_M)
        
    def test_wavelength_m_to_freq_Hz(self):
        result = wavelength_m_to_freq_Hz(self.C_BAND_M)
        assert_allclose(result, self.C_BAND_HZ)

    def test_wavelength_nm_to_freq_Hz(self):
        result = wavelength_nm_to_freq_Hz(self.C_BAND_NM)
        assert_allclose(result, self.C_BAND_HZ)

    def test_freq_Hz_to_wavelength_nm(self):
        result = freq_Hz_to_wavelength_nm(self.C_BAND_HZ)
        assert_allclose(result, self.C_BAND_NM)

    def test_spectral_array_handling(self):
        """Conversão ótica deve injetar precisão de arrays de volta com underflow resiliente."""
        freqs = np.array([193.1e12, 193.2e12])
        wls_nm = freq_Hz_to_wavelength_nm(freqs)
        # O caminho inverso deve produzir os exatos Hz.
        reverted_freqs = wavelength_nm_to_freq_Hz(wls_nm)
        assert_allclose(reverted_freqs, freqs)

    def test_zero_frequency_raise(self):
        """Comprimentos de onda ou frequências nulas não existem, causam singularidade c/0"""
        with pytest.raises(ValueError):
            freq_Hz_to_wavelength_m(0.0)


# ==========================================
# Escalonamento Lógico de Banda (GHz / Hz)
# ==========================================

class TestGHzScaling:
    @pytest.mark.parametrize("ghz, hz", [
        (1.0, 1e9),
        (50.0, 50e9),
        (193100.0, 193.1e12)
    ])
    def test_ghz_hz_bidirectional(self, ghz, hz):
        assert_allclose(freq_GHz_to_Hz(ghz), hz)
        assert_allclose(freq_Hz_to_GHz(hz), ghz)

    def test_hz_ghz_arrays(self):
        hz_array = np.array([1e9, 50e9])
        assert_allclose(freq_Hz_to_GHz(hz_array), np.array([1.0, 50.0]))
