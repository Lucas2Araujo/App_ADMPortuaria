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


    btn_tema = ft.IconButton(
        icon=ft.Icons.NIGHTS_STAY, icon_color=ft.Colors.WHITE, on_click=alternar_tema
    )

    def gerar_dados_bd(e):
        try:
            import pop_bd
            from cad import obter_sessao

            with obter_sessao() as session:
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


    def navegar_para(target: str):
        page.active_tab = target

        page.overlay.clear()

        novo_conteudo = None

        if target == "dashboard":
            # Wrapper para animação da esquerda para direita
            conteudo = view_dashboard(page, "dashboard")
            novo_conteudo = ft.Container(
                content=conteudo,
                opacity=0,
                offset=ft.Offset(-0.05, 0),
                animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
                expand=True,
                key="dashboard_view" # Use key to force AnimatedSwitcher to see it as a new widget
            )
            menu_lateral.selected_index = 0
        elif target == "vagas":
            novo_conteudo = view_dashboard(page, "vagas")
            menu_lateral.selected_index = 1
        elif target == "gerenciar":
            novo_conteudo = view_dashboard(page, "gerenciar")
            menu_lateral.selected_index = 2
        elif target == "auditoria":
            novo_conteudo = view_dashboard(page, "auditoria")
            menu_lateral.selected_index = 3
        elif target == "fila":
            novo_conteudo = view_fila(page)
            menu_lateral.selected_index = 4
        elif target == "tripulacao":
            novo_conteudo = view_tripulacao(page)
            menu_lateral.selected_index = 5
            
        # Ensure that other views have a key as well so AnimatedSwitcher works properly
        if target != "dashboard" and isinstance(novo_conteudo, ft.Control):
            # Wrap in a simple container to give it a key
            novo_conteudo = ft.Container(content=novo_conteudo, key=target, expand=True)

        conteudo_principal.content = novo_conteudo
        page.update()

        # Dispara a animação do dashboard após ele ter sido renderizado com opacidade 0
        if target == "dashboard":
            novo_conteudo.opacity = 1
            novo_conteudo.offset = ft.Offset(0, 0)
            page.update()


    page.active_tab = "dashboard"
    
    # Inicia com o dashboard animado
    dash_inicial = ft.Container(
        content=view_dashboard(page, "dashboard"),
        opacity=0,
        offset=ft.Offset(-0.05, 0),
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        expand=True,
        key="dashboard_view_inicial"
    )
    
    conteudo_principal = ft.AnimatedSwitcher(
        content=dash_inicial,
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=400,
        reverse_duration=400,
        switch_in_curve=ft.AnimationCurve.EASE_IN,
        switch_out_curve=ft.AnimationCurve.EASE_OUT,
        expand=True
    )
    
    # Agenda a animação inicial assim que a UI for montada
    async def disparar_animacao_inicial(e=None):
        dash_inicial.opacity = 1
        dash_inicial.offset = ft.Offset(0, 0)
        page.update()
        
    page.run_task(disparar_animacao_inicial)


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


    menu_lateral = ft.NavigationRail(
        selected_index=0,
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


    page.add(ft.Row(controls=[menu_lateral, conteudo_principal], expand=True))



