# Sistema de Administração Portuária — AdminPort

Bem-vindo à documentação oficial do **AdminPort**, o sistema de administração portuária desenvolvido como projeto acadêmico na UFMA.

## O que é o AdminPort?

O AdminPort é uma aplicação desktop construída com **Python + [Flet](https://flet.dev/)** que centraliza o gerenciamento de um porto: cadastro de navios, controle de vagas de atracação e gerenciamento da fila de espera com priorização inteligente de cargas perecíveis.

## Visão geral da arquitetura

O AdminPort possui **dois pontos de entrada distintos**, compartilhando exatamente o mesmo backend (controladores e banco de dados):

```
📦 app_admportuaria
├── 📁 .github/
│   └── 📁 workflows/              # Pipelines de CI/CD (GitHub Actions para deploy e testes)
├── 📁 .vscode/                    # Configurações de ambiente e debug para o VS Code
├── 📁 docs/                       # Documentação do projeto (Arquivos fonte do MkDocs)
│   ├── 📁 api/                    # Documentação dos módulos e classes do backend
│   ├── 📁 Diagramas/              # Modelagem do sistema
│   │   ├── 📁 Código dos diagramas/ # Arquivos fonte .puml (PlantUML)
│   │   └── 📁 Imagens/            # Imagens renderizadas (.png) dos diagramas
│   ├── 📁 gui/                    # Documentação referente à Interface Gráfica
│   ├── 📁 stylesheets/            # Estilos customizados da documentação (CSS)
│   ├── 📄 index.md                # Página inicial da documentação
│   ├── 📄 requisitos.md           # Levantamento de Requisitos
│   ├── 📄 diagramas.md            # Visão geral dos diagramas
│   ├── 📄 contexto_projeto.md     # Contextualização do domínio do problema
│   ├── 📄 testes.md               # Plano e documentação de testes
│   └── 📄 *.pdf                   # Modelos exportados (DiagramaDB, Protótipo)
├── 📁 site/                       # Build estático gerado pelo MkDocs (não versionado/editado manualmente)
├── 📁 src/                        # Código-fonte principal da aplicação
│   ├── 📁 gui/                    # Interface Gráfica da aplicação
│   │   ├── 📁 telas/              # Telas específicas do sistema
│   │   │   ├── 📁 adm/            # Telas do painel administrativo (dashboard, vagas, etc.)
│   │   │   ├── 📄 login.py        # Tela de login
│   │   │   ├── 📄 fila_view.py    # Tela de visualização da fila
│   │   │   └── 📄 painel_tripulacao.py
│   │   ├── 📄 main_gui.py         # Arquivo principal para inicialização da interface
│   │   └── 📄 compat.py           
│   ├── 📁 testes/                 # Suíte de testes automatizados (Pytest)
│   │   ├── 📁 backend/            # Testes de integração e lógica de negócios
│   │   ├── 📁 cli/                # Testes da interface de linha de comando
│   │   ├── 📁 gui/                # Testes de componentes visuais
│   │   └── 📄 conftest.py         # Configurações globais dos testes
│   ├── 📄 app.py                  # Ponto de entrada CLI/Geral
│   ├── 📄 app_gui.py              # Ponto de entrada da GUI
│   ├── 📄 controller_*.py         # Controladores da lógica de negócio
│   ├── 📄 dto.py                  # Objetos de Transferência de Dados
│   ├── 📄 ord_propriety.py        # Algoritmos/lógica de prioridade/ordenação
│   ├── 📄 pop_bd.py               # Script para popular o banco de dados
│   └── 📄 requirements.txt        # Dependências do projeto Python
├── 📄 .gitignore                  # Arquivos e pastas ignorados pelo Git
├── 📄 LICENSE                     # Licença do projeto
├── 📄 mkdocs.yml                  # Arquivo de configuração e estrutura do MkDocs
└── 📄 README.md                   # Apresentação do repositório
```

> **`app.py`** — Versão CLI totalmente funcional. Usa `asyncio` e expõe todos os fluxos (cadastro, auditoria, atracação, desatracação) via menus de texto interativos no terminal.
>
> **`app_gui.py`** — Wrapper mínimo que inicializa o Flet e delega para `gui/main_gui.py`. Lança a interface gráfica desktop.

## Como executar

### Pré-requisito: instalar as dependências

```bash
pip install -r src/requirements.txt
```

### Versão GUI (Interface Gráfica — Flet)

```bash
# Inicia a janela desktop com a interface visual completa
python src/app_gui.py
```

### Versão CLI (Interface de Linha de Comando)

```bash
# Inicia o sistema interativo no terminal
python src/app.py
```

Ao executar a versão CLI, o menu principal será exibido:

```
========================================
  SISTEMA DE ADMINISTRAÇÃO PORTUÁRIA
========================================
[1] Portal da Tripulação
[2] Painel do Administrador
[0] Sair
```

Consulte a página [**Interface CLI**](cli_view.md) para o tutorial completo de uso.

## Como rodar os testes

```bash
# Todos os testes (backend + frontend)
pytest src/

# Apenas os testes da interface
pytest src/test_gui.py -v
```

## Navegação

Utilize o menu superior para explorar:

- **Material de Referência (Diagramas)** — UML e diagramas de modelagem
- **Requisitos do Projeto** — Especificação funcional e não-funcional
- **Interface Gráfica (GUI)** — Documentação dos módulos Flet
- **Referência da API (Backend)** — Documentação automática do código Python