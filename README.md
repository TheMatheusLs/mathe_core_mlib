# Mathe Core MLIB (`mathe-core-mlib`)

![Status](https://img.shields.io/badge/status-finalizado-brightgreen)
![Versão](https://img.shields.io/badge/vers%C3%A3o-2.1.3-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.12-blue)
![Testes](https://img.shields.io/badge/testes-76%20passing-brightgreen)
![Licença](https://img.shields.io/badge/licen%C3%A7a-acad%C3%AAmica-lightgrey)

Biblioteca modular de alta performance e utilitários científicos desenvolvida para suportar simulações de redes ópticas (foco em GNPy), algoritmos de otimização e gestão de dados experimentais.

**Desenvolvido por:** Matheus Lôbo dos Santos (matheus.lobo@ufpe.br)

A `mathe-core-mlib` foi construída sob o princípio de **Fail-Fast (Falha Rápida)**. Em simulações científicas de longa duração, erros silenciosos podem invalidar dias de processamento. Esta biblioteca garante a integridade dos dados através de validações rigorosas, automação de IO e isolamento de dependências.

---

## 📦 Módulos

| Módulo | Conteúdo |
| --- | --- |
| `mathe_core_mlib.math` | Conversores vetorizados (dB/linear, W/dBm, frequência ↔ comprimento de onda) sobre NumPy/SciPy. |
| `mathe_core_mlib.io` | IO de JSON/YAML/Pickle/CSV/Parquet, hash de arquivos, `ExperimentFolder` (pastas de experimento à prova de concorrência) e o *gatekeeper* de ambiente limpo. |
| `mathe_core_mlib.analysis` | Comparação de configurações YAML entre execuções para auditar reprodutibilidade. |
| `mathe_core_mlib.style` | Estilo Matplotlib acadêmico e paletas customizadas. |

---

## 📚 Documentação Oficial

A documentação completa da API, arquitetura de módulos e diagramas de dependência é gerada automaticamente a partir do código-fonte utilizando **MkDocs**.

Para visualizar a documentação localmente em seu navegador:

1. Certifique-se de ter o ambiente configurado (veja a seção de Desenvolvimento abaixo).
2. Execute o servidor de documentação:
   ```bash
   poetry run mkdocs serve
    ```

3. Acesse `http://127.0.0.1:8000/` no seu navegador.

---

## 🚀 Instalação e Uso em Outros Projetos

Este projeto utiliza o **Poetry** como gerenciador de dependências. Não utilize `pip` ou `requirements.txt` para integrar esta biblioteca.

Para utilizar o `mathe_core_mlib` como base matemática no seu simulador principal, navegue até a pasta do seu projeto de simulação e adicione a biblioteca de uma das seguintes formas:

**Opção A: Instalação em Modo Editável (Recomendado para Desenvolvimento Local)**
Permite que você altere o código do *core* e a simulação enxergue as mudanças em tempo real, sem precisar reinstalar.

```bash
poetry add --editable ../caminho/para/mathe_core_mlib

```

**Opção B: Instalação Direta via Git (Recomendado para Servidores/Deploy)**
Congela a versão diretamente do repositório remoto para garantir reprodutibilidade.

```bash
poetry add git+[https://github.com/thematheusls/mathe-core-mlib.git](https://github.com/thematheusls/mathe-core-mlib.git)

```

---

## 🛠️ Configuração para Desenvolvimento (Contribuição)

Se você deseja modificar o código interno do `mathe-core-mlib`, configurar a suíte de testes ou alterar a documentação, siga os passos abaixo para preparar o ambiente:

**1. Clone o repositório:**

```bash
git clone git@github.com:thematheusls/mathe-core-mlib.git
cd mathe-core-mlib

```

**2. Instale o ambiente virtual e as dependências (Core + Dev):**

```bash
poetry install

```

**3. Ative os Hooks de Qualidade (Obrigatório):**
Garante que o código passe pelos padrões do linter (NumPy docstrings) antes de qualquer commit.

```bash
poetry run pre-commit install

```

---

## 🧪 Executando os Testes

A biblioteca possui uma suíte de testes unitários automatizados cobrindo os limites matemáticos e funções de I/O. Para rodar as validações e gerar o relatório de cobertura de código:

```bash
poetry run pytest --cov=src/mathe_core_mlib --cov-report=term-missing

```

Estado atual: **76 testes passando**, cobertura global de **74%** (módulos `math` e `io.files` em 100%).

---

## 📝 Exemplo Rápido de Uso

Como a biblioteca lida nativamente com matrizes NumPy e primitivos, a importação é direta:

```python
import numpy as np
from mathe_core_mlib.math import converters as cv

# Conversão vetorizada de frequências
frequencias_ghz = np.array([193100, 193200, 193300])
lambdas_nm = cv.freq_Hz_to_wavelength_nm(cv.freq_GHz_to_Hz(frequencias_ghz))

print(lambdas_nm)
# Saída esperada: [1552.52... 1551.72... 1550.92...]

```

*(Para guias avançados sobre a classe `ExperimentFolder` e `compare_yaml_files`, consulte a documentação via MkDocs).*

---

## 📄 Licença

Uso acadêmico.