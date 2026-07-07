# Sistema de Administração Portuária — AdminPort

Bem-vindo à documentação oficial do **AdminPort**, o sistema de administração portuária desenvolvido como projeto acadêmico na UFMA.

## O que é o AdminPort?

O AdminPort é uma aplicação desktop construída com **Python + [Flet](https://flet.dev/)** que centraliza o gerenciamento de um porto: cadastro de navios, controle de vagas de atracação e gerenciamento da fila de espera com priorização inteligente de cargas perecíveis.

## Visão geral da arquitetura

O AdminPort possui **dois pontos de entrada distintos**, compartilhando exatamente o mesmo backend (controladores e banco de dados):

```
App_ADMPortuaria/
├── src/
│   ├── app.py                  # ① Ponto de entrada CLI (Interface de Linha de Comando)
│   ├── app_gui.py              # ② Ponto de entrada GUI (Interface Gráfica — Flet)
│   ├── gui/                    # Pacote da interface gráfica (Flet)
│   │   ├── main_gui.py         # Raiz da aplicação Flet (carregada por app_gui.py)
│   │   └── telas/
│   │       ├── painel_adm.py   # Painel do Administrador (tela principal)
│   │       ├── fila_view.py    # Visualização da fila de atracação
│   │       └── painel_tripulacao.py  # Painel de registros da tripulação
│   ├── cad.py                  # Modelos do banco de dados (SQLAlchemy)
│   ├── controller_cadastros.py # Lógica de pré-cadastro e aprovação (async)
│   ├── controller_operacao.py  # Lógica de atracação e desatracação (async)
│   └── ord_propriety.py        # Algoritmo de priorização da fila
├── docs/                       # Esta documentação
└── mkdocs.yml
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