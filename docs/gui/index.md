# Interface Gráfica — Visão Geral

O frontend do AdminPort é construído com **[Flet](https://flet.dev/)**, um framework Python que gera aplicações Flutter nativas a partir de código Python.

## Ponto de entrada — `main_gui.py`

O arquivo `src/gui/main_gui.py` é responsável por:

- Configurar a `ft.Page` (título, tema, AppBar)
- Montar o **menu de navegação lateral** (`NavigationRail`) com 3 destinos
- Alternar entre as telas conforme a seleção do usuário
- Disponibilizar o botão de troca de tema (claro ↔ escuro)

### Telas disponíveis

| Índice | Ícone | Tela | Módulo |
|--------|-------|------|--------|
| 0 | `DASHBOARD` | Painel ADM | `telas/painel_adm.py` |
| 1 | `FORMAT_LIST_NUMBERED` | Fila de Atracação | `telas/fila_view.py` |
| 2 | `ADD_CIRCLE` | Tripulação | `telas/painel_tripulacao.py` |

### Navegação

```python
# Troca de tela por índice (NavigationRail)
def mudar_tela(e):
    index = e.control.selected_index
    if index == 0:
        conteudo_principal.content = view_dashboard(page)
    elif index == 1:
        conteudo_principal.content = view_fila(page)
    elif index == 2:
        conteudo_principal.content = view_tripulacao(page)
    page.update()
```

## Estrutura de layout

```
Page
└── AppBar  (barra superior azul-cinza)
└── Row (expand=True)
    ├── NavigationRail  (menu lateral)
    └── Container       (conteúdo principal, expand)
        └── <tela selecionada>
```
