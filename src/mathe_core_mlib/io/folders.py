import os
import shutil
from datetime import datetime
from typing import Optional

class ExperimentFolder:
    """
    Gerencia a criação e ciclo de vida de uma pasta de resultados de experimento.
    Gera nomes baseados em Timestamp e Tag.
    """
    def __init__(self, base_path: str, tag: str = "sim", version: str = ""):
        """
        Args:
            base_path: Diretório raiz onde a pasta será criada (ex: './results').
            tag: Identificador curto do experimento (ex: 'GA_Optimization').
            version: Versão opcional para compor o nome (ex: 'v1.0').
        """
        self.timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Constrói o nome: "2023-10-27_14-30-00_v1.0_GA_Optimization"
        folder_name_parts = [self.timestamp]
        if version:
            folder_name_parts.append(version)
        folder_name_parts.append(tag)
        
        self.folder_name = "_".join(folder_name_parts)
        self.path = os.path.join(base_path, self.folder_name)
        
        # Cria a pasta imediatamente
        os.makedirs(self.path, exist_ok=False)
        self._finalized = False


    def get_folder_name(self) -> str:
        """Retorna o nome da pasta do experimento."""
        return self.folder_name


    def get_path(self, filename: str = "") -> str:
        """Retorna o caminho completo para um arquivo dentro desta pasta."""
        return os.path.join(self.path, filename)


    def copy_file(self, src_path: str, new_name: Optional[str] = None) -> None:
        """
        Copia um arquivo externo para dentro da pasta do experimento.
        
        Args:
            src_path: Caminho do arquivo original.
            new_name: (Opcional) Novo nome do arquivo no destino.
        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Arquivo fonte não encontrado: {src_path}")
            
        filename = new_name if new_name else os.path.basename(src_path)
        dst_path = self.get_path(filename)
        shutil.copyfile(src_path, dst_path)


    def save_text(self, filename: str, content: str) -> None:
        """Salva uma string em um arquivo de texto simples."""
        with open(self.get_path(filename), 'w', encoding='utf-8') as f:
            f.write(content)


    def finish(self, status: str = "success", info_msg: str = "") -> None:
        """
        Finaliza o experimento renomeando a pasta com um sufixo (_Success, _Fail).
        
        Args:
            status: 'success' ou 'fail' (ou qualquer string).
            info_msg: Mensagem opcional para salvar em um txt de status.
        """
        if self._finalized:
            return

        suffix = f"_{status.capitalize()}" # _Success ou _Fail
        new_path = self.path + suffix
        
        # Salva log final se houver mensagem
        if info_msg:
            log_name = "Success.txt" if status.lower() == "success" else "Error.txt"
            self.save_text(log_name, info_msg)

        try:
            os.rename(self.path, new_path)
            self.path = new_path
            self._finalized = True
        except OSError as e:
            print(f"Erro ao renomear pasta de experimento: {e}")

    def __str__(self):
        return f"ExperimentFolder({self.path})"