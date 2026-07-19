"""Testes do ExperimentFolder — foco em unicidade da pasta sob concorrência.

O nome da pasta usa timestamp com resolução de SEGUNDOS. Processos disparados
juntos (estudos em lote) colidiam com FileExistsError (WinError 183) e o
experimento morria antes de começar. Estes testes fixam o contrato: nunca falhar
por colisão e NUNCA compartilhar a mesma pasta entre dois experimentos.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mathe_core_mlib.io.folders import ExperimentFolder


def test_creates_folder_with_timestamp_tag_and_version(tmp_path: Path) -> None:
    exp = ExperimentFolder(base_path=tmp_path, tag="PSD_otm", version="1.0.3")

    assert exp.path.is_dir()
    assert exp.path.parent == tmp_path
    assert exp.get_folder_name().endswith("_version_1-0-3_PSD_otm")
    assert exp.get_folder_name() == exp.path.name


def test_two_experiments_in_same_second_get_distinct_folders(tmp_path: Path) -> None:
    # Mesmo segundo ⇒ mesmo nome-base: o segundo deve ganhar sufixo, não estourar.
    first = ExperimentFolder(base_path=tmp_path, tag="sim")
    second = ExperimentFolder(base_path=tmp_path, tag="sim")

    assert first.path != second.path
    assert first.path.is_dir() and second.path.is_dir()
    assert second.path.name.startswith(first.path.name)
    assert second.path.name.endswith("_2")


def test_many_concurrent_experiments_never_share_a_folder(tmp_path: Path) -> None:
    # Reproduz o cenário do .bat: N processos criando a pasta ao mesmo tempo.
    n = 12
    with ThreadPoolExecutor(max_workers=n) as pool:
        exps = list(pool.map(lambda _: ExperimentFolder(base_path=tmp_path, tag="lote"), range(n)))

    paths = [e.path for e in exps]
    assert len(set(paths)) == n, "duas execuções compartilharam a mesma pasta"
    assert all(p.is_dir() for p in paths)
    # folder_name reflete a pasta REAL criada (não o nome pretendido).
    assert all(e.get_folder_name() == e.path.name for e in exps)


def test_finish_renames_with_status_and_keeps_suffixed_folders_distinct(tmp_path: Path) -> None:
    first = ExperimentFolder(base_path=tmp_path, tag="sim")
    second = ExperimentFolder(base_path=tmp_path, tag="sim")

    first.finish(status="success", info_msg="ok")
    second.finish(status="error", info_msg="falhou")

    assert first.path.name.endswith("_SUCCESS")
    assert second.path.name.endswith("_ERROR")
    assert first.path != second.path
    assert (first.path / "Success.txt").read_text(encoding="utf-8") == "ok"
    assert (second.path / "Error.txt").read_text(encoding="utf-8") == "falhou"


def test_finish_is_idempotent(tmp_path: Path) -> None:
    exp = ExperimentFolder(base_path=tmp_path, tag="sim")
    exp.finish(status="success")
    path_after_first = exp.path

    exp.finish(status="success")  # segunda chamada não deve renomear de novo

    assert exp.path == path_after_first
    assert not exp.path.name.endswith("_SUCCESS_SUCCESS")


def test_create_unique_dir_gives_up_after_max_attempts(tmp_path: Path) -> None:
    (tmp_path / "x").mkdir()
    (tmp_path / "x_2").mkdir()

    with pytest.raises(FileExistsError, match="tentativas"):
        ExperimentFolder._create_unique_dir(tmp_path, "x", max_attempts=1)


def test_copy_file_and_save_text(tmp_path: Path) -> None:
    src = tmp_path / "config.yaml"
    src.write_text("a: 1", encoding="utf-8")
    exp = ExperimentFolder(base_path=tmp_path / "out", tag="sim")

    exp.copy_file(src)
    exp.copy_file(src, new_name="config_copia.yaml")
    exp.save_text("nota.txt", "conteudo")

    assert (exp.path / "config.yaml").read_text(encoding="utf-8") == "a: 1"
    assert (exp.path / "config_copia.yaml").is_file()
    assert (exp.path / "nota.txt").read_text(encoding="utf-8") == "conteudo"

    with pytest.raises(FileNotFoundError):
        exp.copy_file(tmp_path / "nao_existe.yaml")
