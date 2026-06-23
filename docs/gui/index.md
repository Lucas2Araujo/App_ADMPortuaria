# Interface Gráfica — Visão Geral

O frontend do AdminPort é construído com **[Flet](https://flet.dev/)**, um framework Python que gera aplicações Flutter nativas a partir de código Python.

## Ponto de entrada — `main_gui.py`

O arquivo `src/gui/main_gui.py` é responsável por:

- Configurar a `ft.Page` (título, tema, AppBar)
- Montar o **menu de navegação lateral** (`NavigationRail`) com 6 destinos
- Alternar entre as telas conforme a seleção do usuário
- Disponibilizar o botão de troca de tema (claro ↔ escuro)

### Telas disponíveis no menu lateral

| Índice | Ícone | Tela | Aba / Sub-view | Módulo |
|--------|-------|------|----------------|--------|
| 0 | `PIE_CHART` | Visão Geral | Dashboard | `telas/painel_adm.py` |
| 1 | `VIEW_AGENDA` | Monitor de Berços | Vagas | `telas/painel_adm.py` |
| 2 | `DIRECTIONS_BOAT_FILLED` | Gestão de Navios | Gerenciar | `telas/painel_adm.py` |
| 3 | `FACT_CHECK` | Auditar Solicitações | Auditoria | `telas/painel_adm.py` |
| 4 | `FORMAT_LIST_NUMBERED` | Fila de Atracação | - | `telas/fila_view.py` |
| 5 | `ANCHOR` | Portal da Tripulação | - | `telas/painel_tripulacao.py` |

### Navegação por rotas internas

```python
# Mapeamento de rotas e seleção na barra lateral
def navegar_para(target: str):
    page.overlay.clear()

    if target == "dashboard":
        conteudo_principal.content = view_dashboard(page, "dashboard")
        menu_lateral.selected_index = 0
    elif target == "vagas":
        conteudo_principal.content = view_dashboard(page, "vagas")
        menu_lateral.selected_index = 1
    elif target == "gerenciar":
        conteudo_principal.content = view_dashboard(page, "gerenciar")
        menu_lateral.selected_index = 2
    elif target == "auditoria":
        conteudo_principal.content = view_dashboard(page, "auditoria")
        menu_lateral.selected_index = 3
    elif target == "fila":
        conteudo_principal.content = view_fila(page)
        menu_lateral.selected_index = 4
    elif target == "tripulacao":
        conteudo_principal.content = view_tripulacao(page)
        menu_lateral.selected_index = 5
    page.update()
```

## Estrutura de layout

```
Page
└── AppBar  (barra superior azul-cinza)
└── Row (expand=True)
    ├── NavigationRail  (menu lateral com 6 opções)
    └── Container       (conteúdo principal, expand)
        └── <tela selecionada>
```
