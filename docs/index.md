# Sistema de Administração Portuária — AdminPort

Bem-vindo à documentação oficial do **AdminPort**, o sistema de administração portuária desenvolvido como projeto acadêmico na UFMA.

## O que é o AdminPort?

O AdminPort é uma aplicação desktop construída com **Python + [Flet](https://flet.dev/)** que centraliza o gerenciamento de um porto: cadastro de navios, controle de vagas de atracação e gerenciamento da fila de espera com priorização inteligente de cargas perecíveis.

## Visão geral da arquitetura

```
App_ADMPortuaria/
├── src/
│   ├── gui/                    # Interface gráfica (Flet)
│   │   ├── main_gui.py         # Ponto de entrada da aplicação
│   │   └── telas/
│   │       ├── painel_adm.py   # Painel do Administrador (tela principal)
│   │       ├── fila_view.py    # Visualização da fila de atracação
│   │       └── painel_tripulacao.py  # Painel de registros da tripulação
│   ├── cad.py                  # Modelos do banco de dados (SQLAlchemy)
│   ├── controller_cadastros.py # Lógica de pré-cadastro e aprovação
│   ├── controller_operacao.py  # Lógica de atracação e desatracação
│   └── ord_propriety.py        # Algoritmo de priorização da fila
├── docs/                       # Esta documentação
└── mkdocs.yml
```

## Como executar

```bash
# 1. Instale as dependências
pip install -r src/requirements.txt

# 2. Inicie a interface gráfica
python src/gui/main_gui.py
```

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