import flet as ft
import os
import sys

diretorio_gui = os.path.dirname(os.path.abspath(__file__))
diretorio_src = os.path.abspath(os.path.join(diretorio_gui, ".."))

if diretorio_gui not in sys.path:
    sys.path.append(diretorio_gui)
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

# Importando todas as views (telas) da pasta correspondente
from telas.painel_adm import obter_view as view_dashboard
from telas.fila_view import obter_view as view_fila
from telas.painel_tripulacao import obter_view as view_tripulacao


def main(page: ft.Page):
    page.title = "AdminPort - Sistema Portuário"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY)

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

    # Botão Tema
    btn_tema = ft.IconButton(
        icon=ft.Icons.NIGHTS_STAY, icon_color=ft.Colors.WHITE, on_click=alternar_tema
    )

    def gerar_dados_bd(e):
        try:
            import pop_bd
            from sqlalchemy import create_engine
            from sqlalchemy.orm import Session
            import os

            db_path = os.path.join(os.path.dirname(__file__), "..", "porto.db")
            engine = create_engine(f"sqlite:///{db_path}")

            with Session(engine) as session:
                pop_bd.gerar_navios_fake(session, 60)

            page.snack_bar = ft.SnackBar(
                ft.Text(
                    "60 navios injetados secretamente com sucesso! Atualize a tabela."
                ),
                bgcolor=ft.Colors.GREEN_700,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as erro:
            print(f"Erro ao injetar navios: {erro}")

    # Barra superior do sistema
    page.appbar = ft.AppBar(
        leading=ft.Icon(
            ft.Icons.DIRECTIONS_BOAT_FILLED, color=ft.Colors.BLUE_200, size=28
        ),
        leading_width=60,
        title=ft.Text(
            "Terminal Portuário S/A",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
        ),
        center_title=False,
        bgcolor=ft.Colors.BLUE_GREY_900,
        actions=[
            btn_tema,
            ft.IconButton(
                ft.Icons.ACCOUNT_CIRCLE,
                icon_color=ft.Colors.WHITE,
                tooltip="Gerar Dados",
                on_click=gerar_dados_bd,
            ),
        ],
    )

    # Função central de navegação
    def navegar_para(target: str):
        # Limpa os modais/popups anteriores da memória para evitar sobreposição e bugs visuais
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

    # Inicializar conteúdo principal com a view do Dashboard
    conteudo_principal = ft.Container(
        content=view_dashboard(page, "dashboard"), expand=True
    )

    # Delegação de mudança pelo menu lateral
    def mudar_tela(e):
        index = e.control.selected_index
        mapa_rotas = {
            0: "dashboard",
            1: "vagas",
            2: "gerenciar",
            3: "auditoria",
            4: "fila",
            5: "tripulacao",
        }
        if index in mapa_rotas:
            navegar_para(mapa_rotas[index])

    # Menu Lateral Centralizado (Flat Navigation)
    menu_lateral = ft.NavigationRail(
        selected_index=0,  # Inicia com Visão Geral
        label_type=ft.NavigationRailLabelType.ALL,
        extended=True,
        min_width=72,
        min_extended_width=204,
        bgcolor=ft.Colors.BLUE_GREY_50,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.PIE_CHART_OUTLINE,
                selected_icon=ft.Icons.PIE_CHART,
                label="Visão Geral",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.VIEW_AGENDA_OUTLINED,
                selected_icon=ft.Icons.VIEW_AGENDA,
                label="Monitor de Berços",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DIRECTIONS_BOAT_OUTLINED,
                selected_icon=ft.Icons.DIRECTIONS_BOAT_FILLED,
                label="Gestão de Navios",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FACT_CHECK_OUTLINED,
                selected_icon=ft.Icons.FACT_CHECK,
                label="Auditar Solicitações",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FORMAT_LIST_NUMBERED,
                selected_icon=ft.Icons.FORMAT_LIST_NUMBERED,
                label="Fila de Atracação",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ANCHOR,
                selected_icon=ft.Icons.ANCHOR,
                label="Portal da Tripulação",
            ),
        ],
        on_change=mudar_tela,
    )

    # Adiciona layout à página
    page.add(ft.Row(controls=[menu_lateral, conteudo_principal], expand=True))


ft.run(main)
