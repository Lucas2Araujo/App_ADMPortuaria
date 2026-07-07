import flet as ft
import os
import sys
import gui.compat

diretorio_src = os.path.dirname(os.path.abspath(__file__))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from telas.adm.dashboard import obter_view as view_dashboard
from telas.adm.vagas import obter_view as view_vagas
from telas.adm.gerenciar import obter_view as view_gerenciar
from telas.adm.auditoria import obter_view as view_auditoria
from telas.adm.historico import obter_view as view_historico
from telas.fila_view import obter_view as view_fila
from telas.painel_tripulacao import obter_view as view_tripulacao
from telas.login import obter_view as view_login


def main(page: ft.Page):
    # Inicialização do Banco de Dados
    from cad import inicializar_banco, obter_sessao
    from pop_bd import gerar_vagas_iniciais

    pasta_src = os.path.dirname(diretorio_src)
    db_path = os.path.join(pasta_src, "porto.db")
    inicializar_banco(db_path)
    with obter_sessao() as session:
        gerar_vagas_iniciais(session, quantidade=5)

    page.title = "AdminPort - Sistema Portuário"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY)

    def mostrar_login():
        page.controls.clear()
        page.appbar = None

        login_view = view_login(page, on_login_success=iniciar_app)
        page.add(login_view)
        page.update()

    def iniciar_app(role):
        page.controls.clear()

        def alternar_tema(e):
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
                btn_tema.icon = ft.Icons.WB_SUNNY
                menu_lateral.bgcolor = ft.Colors.BLUE_GREY_900
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
                btn_tema.icon = ft.Icons.NIGHTS_STAY
                menu_lateral.bgcolor = ft.Colors.BLUE_GREY_50
            page.update()

        def gerar_dados_bd(e):
            try:
                import pop_bd
                from cad import obter_sessao

                with obter_sessao() as session:
                    pop_bd.gerar_navios_fake(session, 40)

                page.snack_bar = ft.SnackBar(
                    ft.Text("40 navios injetados com sucesso! Atualize a tabela."),
                    bgcolor=ft.Colors.GREEN_700,
                )
                page.snack_bar.open = True
            except Exception as err:
                print(f"Erro ao gerar dados: {err}")
            page.update()

        btn_sair = ft.IconButton(
            icon=ft.Icons.LOGOUT,
            icon_color=ft.Colors.RED_300,
            on_click=lambda e: mostrar_login(),
        )

        eh_escuro = page.theme_mode == ft.ThemeMode.DARK

        btn_tema = ft.IconButton(
            icon=ft.Icons.WB_SUNNY if eh_escuro else ft.Icons.NIGHTS_STAY,
            icon_color=ft.Colors.WHITE,
            on_click=alternar_tema,
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
                    on_click=gerar_dados_bd,
                ),
                btn_tema,
                btn_sair,
            ],
        )

        # Filtro de permissões
        if role == "admin":
            destinos_menu = [
                ft.NavigationRailDestination(
                    icon=ft.Icons.PIE_CHART, label="Visão Geral"
                ),
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
            mapa_rotas = {
                0: "dashboard",
                1: "vagas",
                2: "gerenciar",
                3: "auditoria",
                4: "fila",
                5: "historico",
            }
        else:
            destinos_menu = [
                ft.NavigationRailDestination(
                    icon=ft.Icons.PIE_CHART, label="Visão Geral"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.FORMAT_LIST_NUMBERED, label="Fila de Atracação"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANCHOR, label="Portal da Tripulação"
                ),
            ]
            mapa_rotas = {0: "dashboard", 1: "fila", 2: "tripulacao"}

        cache_telas = {}

        def navegar_para(target: str):
            page.active_tab = target

            if target not in cache_telas:
                # Carregamento sob demanda (Lazy Loading)
                if target == "dashboard":
                    cache_telas[target] = view_dashboard(page)
                elif target == "vagas":
                    cache_telas[target] = view_vagas(page)
                elif target == "gerenciar":
                    cache_telas[target] = view_gerenciar(page)
                elif target == "auditoria":
                    cache_telas[target] = view_auditoria(page)
                elif target == "fila":
                    cache_telas[target] = view_fila(page)
                elif target == "historico":
                    cache_telas[target] = view_historico(page)
                elif target == "tripulacao":
                    cache_telas[target] = view_tripulacao(page)

            active_view = cache_telas[target]
            conteudo_principal.content = active_view

            # Immediate refresh on navigation if the screen implements it
            if hasattr(active_view, "atualizar"):
                page.run_task(active_view.atualizar)

            for k, v in mapa_rotas.items():
                if v == target:
                    menu_lateral.selected_index = k
                    break
            page.update()

        menu_lateral = ft.NavigationRail(
            selected_index=0,
            extended=True,
            destinations=destinos_menu,
            bgcolor=ft.Colors.BLUE_GREY_900 if eh_escuro else ft.Colors.BLUE_GREY_50,
            on_change=lambda e: navegar_para(mapa_rotas[e.control.selected_index]),
        )

        conteudo_principal = ft.Container(expand=True)
        page.add(ft.Row([menu_lateral, conteudo_principal], expand=True))
        navegar_para("dashboard")

    mostrar_login()
