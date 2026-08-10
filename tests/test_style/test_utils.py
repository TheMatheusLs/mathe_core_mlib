"""Testes da gravação de figuras com proveniência.

Além do contrato de metadados, há uma guarda de encoding: as mensagens emitidas
por esta lib precisam ser ASCII puro. Um emoji na mensagem derrubava o
save_figure inteiro quando o console do Windows estava em cp1252.
"""

import json
import logging
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from mathe_core_mlib.style.utils import _PDF_INFO_KEYS, _pdf_info_dict, save_figure  # noqa: E402

VERSION = "9.9.9"


@pytest.fixture
def fig():
    figura, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    yield figura
    plt.close(figura)


def test_save_figure_writes_pdf_and_sidecar(tmp_path: Path, fig) -> None:
    destino = tmp_path / "perfil"

    save_figure(fig, destino, VERSION, software="MeuSim")

    assert (tmp_path / "perfil.pdf").is_file()
    assert (tmp_path / "perfil.meta.json").is_file()


def test_sidecar_carries_full_provenance(tmp_path: Path, fig) -> None:
    destino = tmp_path / "perfil"

    save_figure(fig, destino, VERSION, software="MeuSim", extra_meta={"scenario": "parabolic"})

    meta = json.loads((tmp_path / "perfil.meta.json").read_text(encoding="utf-8"))

    assert meta["software_version"] == VERSION
    assert meta["software"] == "MeuSim"
    assert meta["scenario"] == "parabolic"
    assert meta["files"] == ["perfil.pdf"]


def test_save_figure_requires_version(tmp_path: Path, fig) -> None:
    with pytest.raises(TypeError):
        save_figure(fig, tmp_path / "perfil")


@pytest.mark.parametrize("dpi", [None, 300])
def test_save_figure_accepts_optional_dpi(tmp_path: Path, fig, dpi) -> None:
    # dpi=None nao pode ser repassado ao matplotlib; so o valor explicito vai adiante
    save_figure(fig, tmp_path / "perfil", VERSION, dpi=dpi)

    assert (tmp_path / "perfil.pdf").is_file()


def test_save_figure_creates_missing_parent_directories(tmp_path: Path, fig) -> None:
    destino = tmp_path / "a" / "b" / "perfil"

    save_figure(fig, destino, VERSION)

    assert destino.with_suffix(".pdf").is_file()


def test_pdf_info_dict_uses_only_keys_matplotlib_accepts() -> None:
    # Chave fora do conjunto padrão faz o backend PDF emitir UserWarning e descartar
    meta = {
        "created_at": "2026-08-10T12:00:00+00:00",
        "software": "MeuSim",
        "software_version": VERSION,
        "git_commit": "abc1234",
        "git_dirty": True,
    }

    info = _pdf_info_dict(meta, "perfil")

    assert set(info) <= _PDF_INFO_KEYS
    assert VERSION in info["Subject"]
    assert "abc1234" in info["Subject"]


def test_save_figure_emits_no_warning_from_pdf_backend(tmp_path: Path, fig, recwarn) -> None:
    save_figure(fig, tmp_path / "perfil", VERSION, software="MeuSim")

    assert not [w for w in recwarn if "infodict" in str(w.message)]


def test_log_messages_are_ascii_only(tmp_path: Path, fig, caplog) -> None:
    # Regressao: emoji na mensagem estourava UnicodeEncodeError em console cp1252
    with caplog.at_level(logging.INFO, logger="mathe_core_mlib.style.utils"):
        save_figure(fig, tmp_path / "perfil", VERSION)

    assert caplog.records
    for record in caplog.records:
        record.getMessage().encode("cp1252")


def test_save_figure_does_not_print(tmp_path: Path, fig, capsys) -> None:
    save_figure(fig, tmp_path / "perfil", VERSION)

    assert capsys.readouterr().out == ""
