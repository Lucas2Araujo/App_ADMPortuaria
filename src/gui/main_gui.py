import flet as ft
import os
import sys
import gui.compat

diretorio_src = os.path.dirname(os.path.abspath(__file__))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from gui.telas.login import obter_view as view_login


def _gerar_dados_bd(page):
    """Injeta 40 navios fake no banco e exibe feedback via SnackBar."""
    try:
        import pop_bd
        from cad import obter_sessao

        with obter_sessao() as session:
            pop_bd.gerar_navios_fake(session, 40)

        page.snack_bar = ft.SnackBar(
            ft.Text("40 navios injetados com sucesso! Atualize a tabela."),
            bgcolor=ft.Colors.GREEN_700,
        )
    except Exception as err:
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Erro ao gerar dados: {err}"),
            bgcolor=ft.Colors.RED_700,
        )
    page.snack_bar.open = True
    page.update()


def _alternar_tema(page, btn_tema, menu_lateral):
    import flet as ft

    if page.theme_mode == ft.ThemeMode.LIGHT:
        page.theme_mode = ft.ThemeMode.DARK
        btn_tema.icon = ft.Icons.WB_SUNNY
        menu_lateral.bgcolor = ft.Colors.BLUE_GREY_900
    else:
        page.theme_mode = ft.ThemeMode.LIGHT
        btn_tema.icon = ft.Icons.NIGHTS_STAY
        menu_lateral.bgcolor = ft.Colors.BLUE_GREY_50
    page.update()


def _obter_destinos_e_mapa(role):
    import flet as ft

    if role == "admin":
        destinos = [
            ft.NavigationRailDestination(icon=ft.Icons.PIE_CHART, label="Visão Geral"),
            ft.NavigationRailDestination(
                icon=ft.Icons.VIEW_AGENDA, label="Monitor de Berços"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DIRECTIONS_BOAT, label="Gestão de Navios"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FACT_CHECK, label="Auditar Solicitações"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FORMAT_LIST_NUMBERED, label="Fila de Atracação"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HISTORY, label="Histórico de Operações"
            ),
        ]
        mapa = {
            0: "dashboard",
            1: "vagas",
            2: "gerenciar",
            3: "auditoria",
            4: "fila",
            5: "historico",
        }
    else:
        destinos = [
            ft.NavigationRailDestination(icon=ft.Icons.PIE_CHART, label="Visão Geral"),
            ft.NavigationRailDestination(
                icon=ft.Icons.FORMAT_LIST_NUMBERED, label="Fila de Atracação"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ANCHOR, label="Portal da Tripulação"
            ),
        ]
        mapa = {0: "dashboard", 1: "fila", 2: "tripulacao"}

    return destinos, mapa


def mostrar_login(page):
    from gui.telas.login import obter_view as view_login

    page.controls.clear()
    page.appbar = None
    login_view = view_login(page, on_login_success=lambda role: iniciar_app(page, role))
    page.add(login_view)
    page.update()


def iniciar_app(page, role):
    import flet as ft

    page.controls.clear()

    eh_escuro = page.theme_mode == ft.ThemeMode.DARK

    btn_sair = ft.IconButton(
        icon=ft.Icons.LOGOUT,
        icon_color=ft.Colors.RED_300,
        on_click=lambda e: mostrar_login(page),
    )

    btn_tema = ft.IconButton(
        icon=ft.Icons.WB_SUNNY if eh_escuro else ft.Icons.NIGHTS_STAY,
        icon_color=ft.Colors.WHITE,
    )

    page.appbar = ft.AppBar(
        title=ft.Text(
            f"Terminal Portuário S/A - {'[Admin]' if role == 'admin' else 'Tripulação'}"
        ),
        bgcolor=ft.Colors.BLUE_GREY_900,
        color=ft.Colors.WHITE,
        actions=[
            ft.IconButton(
                ft.Icons.ACCOUNT_CIRCLE,
                icon_color=ft.Colors.WHITE,
                tooltip="Gerar Dados",
                on_click=lambda e: _gerar_dados_bd(page),
            ),
            btn_tema,
            btn_sair,
        ],
    )

    destinos_menu, mapa_rotas = _obter_destinos_e_mapa(role)

    cache_telas = {}

    from gui.telas.adm.dashboard import obter_view as view_dashboard
    from gui.telas.adm.vagas import obter_view as view_vagas
    from gui.telas.adm.gerenciar import obter_view as view_gerenciar
    from gui.telas.adm.auditoria import obter_view as view_auditoria
    from gui.telas.adm.historico import obter_view as view_historico
    from gui.telas.fila_view import obter_view as view_fila
    from gui.telas.painel_tripulacao import obter_view as view_tripulacao

    view_factory = {
        "dashboard": view_dashboard,
        "vagas": view_vagas,
        "gerenciar": view_gerenciar,
        "auditoria": view_auditoria,
        "fila": view_fila,
        "historico": view_historico,
        "tripulacao": view_tripulacao,
    }

    def navegar_para(target: str):
        page.active_tab = target

        if target not in cache_telas and target in view_factory:
            cache_telas[target] = view_factory[target](page)

        active_view = cache_telas.get(target)
        if active_view:
            conteudo_principal.content = active_view

            if hasattr(active_view, "atualizar"):
                page.run_task(active_view.atualizar)

        menu_lateral.selected_index = next(
            (k for k, v in mapa_rotas.items() if v == target), 0
        )
        page.update()

    menu_lateral = ft.NavigationRail(
        selected_index=0,
        extended=True,
        destinations=destinos_menu,
        bgcolor=ft.Colors.BLUE_GREY_900 if eh_escuro else ft.Colors.BLUE_GREY_50,
        on_change=lambda e: navegar_para(mapa_rotas[e.control.selected_index]),
    )

    btn_tema.on_click = lambda e: _alternar_tema(page, btn_tema, menu_lateral)

    conteudo_principal = ft.Container(expand=True)
    page.add(ft.Row([menu_lateral, conteudo_principal], expand=True))
    navegar_para("dashboard")


def main(page):
    import flet as ft
    import os
    from cad import inicializar_banco, obter_sessao
    from pop_bd import gerar_vagas_iniciais

    diretorio_src = os.path.dirname(os.path.abspath(__file__))
    pasta_src = os.path.dirname(diretorio_src)
    db_path = os.path.join(pasta_src, "porto.db")
    inicializar_banco(db_path)
    with obter_sessao() as session:
        gerar_vagas_iniciais(session, quantidade=5)

    page.title = "AdminPort - Sistema Portuário"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY)

    mostrar_login(page)
