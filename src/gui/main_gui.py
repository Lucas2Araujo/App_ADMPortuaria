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
from telas.welcome_view import obter_view as view_welcome

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

    # Botão Home
    btn_home = ft.IconButton(
        ft.Icons.HOME, 
        icon_color=ft.Colors.WHITE, 
        tooltip="Home", 
        on_click=lambda e: navegar_para("welcome")
    )
    
    # Botão Tema
    btn_tema = ft.IconButton(
        icon=ft.Icons.NIGHTS_STAY, icon_color=ft.Colors.WHITE, on_click=alternar_tema
    )

    # AppBar Superior
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.DIRECTIONS_BOAT_FILLED, color=ft.Colors.WHITE),
        leading_width=40,
        title=ft.Text("AdminPort", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        bgcolor=ft.Colors.BLUE_GREY_900,
        actions=[
            btn_home,
            btn_tema,
            ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, icon_color=ft.Colors.WHITE),
        ],
    )

    # Função central de navegação
    def navegar_para(target: str):
        if target == "adm":
            conteudo_principal.content = view_dashboard(page)
            menu_lateral.selected_index = 0
        elif target == "fila":
            conteudo_principal.content = view_fila(page)
            menu_lateral.selected_index = 1
        elif target == "tripulacao":
            conteudo_principal.content = view_tripulacao(page)
            menu_lateral.selected_index = 2
        elif target == "welcome":
            conteudo_principal.content = view_welcome(page, navigate=navegar_para)
            menu_lateral.selected_index = None # Remove seleção se estiver na Home
        page.update()

    # Inicializar conteúdo principal com a view da Home
    conteudo_principal = ft.Container(content=view_welcome(page, navigate=navegar_para), expand=True)

    # Delegação de mudança pelo menu lateral
    def mudar_tela(e):
        index = e.control.selected_index
        if index == 0:
            navegar_para("adm")
        elif index == 1:
            navegar_para("fila")
        elif index == 2:
            navegar_para("tripulacao")

    # Menu Lateral
    menu_lateral = ft.NavigationRail(
        selected_index=None, # Inicia sem seleção
        label_type=ft.NavigationRailLabelType.ALL,
        extended=True,
        min_width=72,
        min_extended_width=200,
        bgcolor=ft.Colors.BLUE_GREY_50,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Painel ADM",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.FORMAT_LIST_NUMBERED,
                selected_icon=ft.Icons.FORMAT_LIST_NUMBERED,
                label="Fila de Atracação",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                selected_icon=ft.Icons.ADD_CIRCLE,
                label="Tripulação",
            ),
        ],
        on_change=mudar_tela,
    )

    # Adiciona layout à página
    page.add(ft.Row(controls=[menu_lateral, conteudo_principal], expand=True))

ft.run(main)