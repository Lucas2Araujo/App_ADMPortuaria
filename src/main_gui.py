import flet as ft
import os
import sys

diretorio_src = os.path.dirname(os.path.abspath(__file__))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from gui.telas.painel_adm import obter_view as view_dashboard
from gui.telas.fila_view import obter_view as view_fila
from gui.telas.painel_tripulacao import obter_view as view_tripulacao

def main(page: ft.Page):
    # Inicialização do Banco de Dados
    from cad import inicializar_banco, obter_sessao
    from pop_bd import gerar_vagas_iniciais
    db_path = os.path.join(diretorio_src, "porto.db")
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
        
        senha_field = ft.TextField(
            label="Código de Acesso ADM",
            password=True,
            can_reveal_password=True,
            width=300,
            prefix_icon=ft.Icons.LOCK,
            on_submit=lambda e: verificar_senha()
        )
        
        def verificar_senha(e=None):
            if senha_field.value == "admin123":
                dialogo_senha.open = False
                iniciar_app(role="admin")
            else:
                senha_field.error_text = "Senha incorreta!"
                page.update()

        dialogo_senha = ft.AlertDialog(
            title=ft.Text("Acesso Administrativo"),
            content=senha_field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: fechar_dialogo()),
                ft.ElevatedButton("Entrar", on_click=verificar_senha, bgcolor=ft.Colors.BLUE_900, color=ft.Colors.WHITE)
            ],
        )
        
        def fechar_dialogo():
            dialogo_senha.open = False
            senha_field.value = ""
            senha_field.error_text = None
            page.update()

        def abrir_dialogo_admin(e):
            page.overlay.append(dialogo_senha)
            dialogo_senha.open = True
            page.update()

        login_view = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            bgcolor=ft.Colors.BLUE_GREY_50,
            content=ft.Card(
                elevation=8,
                shape=ft.RoundedRectangleBorder(radius=15),
                content=ft.Container(
                    padding=40,
                    width=420,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.DIRECTIONS_BOAT_FILLED, size=80, color=ft.Colors.BLUE_900),
                            ft.Text("Terminal Portuário S/A", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                            ft.Text("Selecione seu perfil de acesso", size=14, color=ft.Colors.GREY_600),
                            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                            ft.ElevatedButton(
                                "Representante / Tripulação",
                                icon=ft.Icons.ANCHOR,
                                width=320,
                                style=ft.ButtonStyle(padding=20, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                                on_click=lambda e: iniciar_app(role="tripulacao")
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.OutlinedButton(
                                "Administração do Porto",
                                icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                width=320,
                                style=ft.ButtonStyle(padding=20),
                                on_click=abrir_dialogo_admin
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True
                    )
                )
            )
        )
        page.add(login_view)
        page.update()

    def iniciar_app(role):
        page.controls.clear()

        def alternar_tema(e):
            page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
            page.update()

        btn_sair = ft.IconButton(icon=ft.Icons.LOGOUT, icon_color=ft.Colors.RED_300, on_click=lambda e: mostrar_login())

        page.appbar = ft.AppBar(
            title=ft.Text(f"Terminal Portuário S/A - {'[Admin]' if role == 'admin' else 'Tripulação'}"),
            bgcolor=ft.Colors.BLUE_GREY_900,
            color=ft.Colors.WHITE,
            actions=[ft.IconButton(ft.Icons.NIGHTS_STAY, on_click=alternar_tema), btn_sair],
        )

        # Filtro de permissões
        if role == "admin":
            destinos_menu = [
                ft.NavigationRailDestination(icon=ft.Icons.PIE_CHART, label="Visão Geral"),
                ft.NavigationRailDestination(icon=ft.Icons.VIEW_AGENDA, label="Monitor de Berços"),
                ft.NavigationRailDestination(icon=ft.Icons.DIRECTIONS_BOAT, label="Gestão de Navios"),
                ft.NavigationRailDestination(icon=ft.Icons.FACT_CHECK, label="Auditar Solicitações"),
                ft.NavigationRailDestination(icon=ft.Icons.FORMAT_LIST_NUMBERED, label="Fila de Atracação"),
                ft.NavigationRailDestination(icon=ft.Icons.ANCHOR, label="Portal da Tripulação"),
            ]
            mapa_rotas = {0: "dashboard", 1: "vagas", 2: "gerenciar", 3: "auditoria", 4: "fila", 5: "tripulacao"}
        else:
            destinos_menu = [
                ft.NavigationRailDestination(icon=ft.Icons.PIE_CHART, label="Visão Geral"),
                ft.NavigationRailDestination(icon=ft.Icons.FORMAT_LIST_NUMBERED, label="Fila de Atracação"),
                ft.NavigationRailDestination(icon=ft.Icons.ANCHOR, label="Portal da Tripulação"),
            ]
            mapa_rotas = {0: "dashboard", 1: "fila", 2: "tripulacao"}

        cache_telas = {}

        def navegar_para(target: str):
            page.active_tab = target
            
            if target not in cache_telas:
                # Carregamento sob demanda (Lazy Loading)
                if target == "dashboard": cache_telas[target] = view_dashboard(page, "dashboard")
                elif target == "vagas": cache_telas[target] = view_dashboard(page, "vagas")
                elif target == "gerenciar": cache_telas[target] = view_dashboard(page, "gerenciar")
                elif target == "auditoria": cache_telas[target] = view_dashboard(page, "auditoria")
                elif target == "fila": cache_telas[target] = view_fila(page)
                elif target == "tripulacao": cache_telas[target] = view_tripulacao(page)

            conteudo_principal.content = cache_telas[target]
            
            for k, v in mapa_rotas.items():
                if v == target:
                    menu_lateral.selected_index = k
                    break
            page.update()

        menu_lateral = ft.NavigationRail(
            selected_index=0,
            extended=True,
            destinations=destinos_menu,
            on_change=lambda e: navegar_para(mapa_rotas[e.control.selected_index]),
        )

        conteudo_principal = ft.Container(expand=True)
        page.add(ft.Row([menu_lateral, conteudo_principal], expand=True))
        navegar_para("dashboard")

    mostrar_login()

ft.run(main)