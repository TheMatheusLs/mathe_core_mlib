import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


class ExperimentFolder:
    """
    Gerencia a criação e ciclo de vida de uma pasta de resultados de experimento.
    Gera nomes baseados em Timestamp e Tag.
    """

    def __init__(self, base_path: Union[Path, str], tag: str = "sim", version: str = ""):
        """
        Args:
            base_path: Diretório raiz onde a pasta será criada (ex: './results').
                Aceita str — os chamadores passam o `path_to_save` lido do YAML.
            tag: Identificador curto do experimento (ex: 'GA_Optimization').
            version: Versão opcional para compor o nome (ex: 'v1.0').
        """
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Constrói o nome: "2023-10-27_14-30-00_v1.0_GA_Optimization"
        folder_name_parts = [self.timestamp]
        if version:
            folder_name_parts.append("version_" + version.replace(".", "-"))
        folder_name_parts.append(tag)

        self.base_path = Path(base_path)

        # Cria a pasta imediatamente (com nome único, mesmo sob concorrência)
        self.path = self._create_unique_dir(self.base_path, "_".join(folder_name_parts))
        self.folder_name = self.path.name
        self._finalized = False

    @staticmethod
    def _create_unique_dir(base_path: Union[Path, str], folder_name: str, max_attempts: int = 1000) -> Path:
        """
        Cria a pasta garantindo unicidade mesmo com processos concorrentes.

        O timestamp do nome tem resolução de SEGUNDOS: dois processos disparados juntos
        (ex.: estudos em lote de um .bat) geram o mesmo nome e o segundo falharia com
        FileExistsError (WinError 183). Como `mkdir(exist_ok=False)` é atômico, quem perde
        a corrida apenas tenta o sufixo seguinte (`_2`, `_3`, ...), sem sobrescrever nada.

        Args:
            base_path: Diretório raiz onde a pasta será criada.
            folder_name: Nome desejado; ganha sufixo numérico só em caso de colisão.
            max_attempts: Limite de tentativas antes de desistir.

        Returns:
            O caminho da pasta efetivamente criada.
        """
        base_path = Path(base_path)
        candidate = base_path / folder_name
        for attempt in range(2, max_attempts + 2):
            try:
                candidate.mkdir(parents=True, exist_ok=False)
                return candidate
            except FileExistsError:
                candidate = base_path / f"{folder_name}_{attempt}"

        raise FileExistsError(
            f"Não foi possível criar uma pasta única para '{folder_name}' em {base_path} "
            f"após {max_attempts} tentativas."
        )

    def get_folder_name(self) -> str:
        """Retorna o nome da pasta do experimento."""
        return self.folder_name

    def get_base_path(self) -> Path:
        """Retorna o caminho base da pasta do experimento."""
        return self.path

    def get_path(self, filename: str = "") -> Path:
        """Retorna o caminho completo para um arquivo dentro desta pasta."""
        return self.path / filename

    def copy_file(self, src_path: Path, new_name: Optional[str] = None) -> None:
        """
        Copia um arquivo externo para dentro da pasta do experimento.

        Args:
            src_path: Caminho do arquivo original.
            new_name: (Opcional) Novo nome do arquivo no destino.
        """
        if not src_path.exists():
            raise FileNotFoundError(f"Arquivo fonte não encontrado: {src_path}")

        filename = new_name if new_name else src_path.name
        dst_path = self.get_path(filename)
        shutil.copyfile(src_path, dst_path)

    def save_text(self, filename: str, content: str) -> None:
        """Salva uma string em um arquivo de texto simples."""
        (self.path / filename).write_text(content, encoding="utf-8")

    def finish(self, status: str = "success", info_msg: str = "") -> None:
        """
        Finaliza o experimento renomeando a pasta com um sufixo (_Success, _Fail).

        Args:
            status: 'success' ou 'fail' (ou qualquer string).
            info_msg: Mensagem opcional para salvar em um txt de status.
        """
        if self._finalized:
            return

        suffix = f"_{status.upper()}"  # _SUCESSED / _FAILED
        new_path = self.path.with_name(self.path.name + suffix)

        # Salva log final se houver mensagem
        if info_msg:
            log_name = "Success.txt" if status.lower() == "success" else "Error.txt"
            self.save_text(log_name, info_msg)

        try:
            self.path.replace(new_path)
            self.path = new_path
            self._finalized = True
        except OSError as e:
            print(f"Erro ao renomear pasta de experimento: {e}")

    def __str__(self) -> str:
        return f"ExperimentFolder({self.path})"

    def get_logging_path(self, log_name: str = "simulation.log") -> Path:
        """
        Retorna o caminho para o arquivo de logging

        Args:
            log_name: nome do arquivo de log

        Return:
            Caminho para o arquivo
        """
        return self.path / log_name
