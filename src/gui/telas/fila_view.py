import os
import sys
import flet as ft
from threading import Thread
from cad import obter_sessao
from ord_propriety import obter_fila_atracacao_dto



def obter_view(page: ft.Page):
    # Tabela que vai listar os navios na fila
    tabela_fila = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Posição", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Nome do Navio", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Observação / Carga", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
    )

    # Texto informativo caso a fila esteja vazia
    txt_vazio = ft.Text(
        "Nenhum navio aguardando na fila de atracação no momento.",
        size=16,
        italic=True,
        color=ft.Colors.GREY_500,
        visible=False,
    )

    def fechar_dialogo(e):
        dialogo_detalhes.open = False
        page.update()

    dialogo_detalhes = ft.AlertDialog(
        actions=[
            ft.TextButton("Fechar Janela", on_click=fechar_dialogo),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=fechar_dialogo,
    )
    page.overlay.append(dialogo_detalhes)

    def abrir_detalhes_navio(navio, posicao):
        print(
            f"[DEBUG] Gerando ficha técnica do navio {navio.nome} (Posição: {posicao})..."
        )

        # Cálculo dinâmico extraindo dados dos relacionamentos 'cargas'
        capitao = getattr(
            navio, "nome_capitao", getattr(navio, "capitao", "Não informado")
        )
        peso_total = (
            sum(c.quantidade_toneladas for c in navio.cargas) if navio.cargas else 0
        )
        peso = f"{peso_total} Toneladas"
        categoria = (
            ", ".join(set(c.categoria for c in navio.cargas)) if navio.cargas else "N/A"
        )
        carga_desc = (
            " | ".join(c.descricao for c in navio.cargas) if navio.cargas else "N/A"
        )
        documentos = (
            "Completos"
            if (navio.cargas and all(c.documento_alfandega for c in navio.cargas))
            else "Incompletos"
        )
        perecivel = (
            "Sim"
            if (navio.cargas and any(c.eh_perecivel for c in navio.cargas))
            else "Não"
        )
        score = f"{navio.score:.2f}"

        # Função auxiliar para criar linhas com "justify between" e ícones
        def criar_linha(icone, rotulo, valor, destaque=False):
            return ft.Row(
                [
                    # Lado Esquerdo: Ícone + Rótulo
                    ft.Row(
                        [
                            ft.Icon(icone, size=18, color=ft.Colors.BLUE_GREY_500),
                            ft.Text(rotulo, color=ft.Colors.BLUE_GREY_700),
                        ],
                        spacing=8,
                    ),
                    # Lado Direito: Valor da variável (envolto em container para evitar overflow)
                    ft.Container(
                        content=ft.Text(
                            str(valor),
                            weight=(
                                ft.FontWeight.BOLD if destaque else ft.FontWeight.NORMAL
                            ),
                            color=ft.Colors.BLUE_900 if destaque else ft.Colors.BLACK87,
                            text_align=ft.TextAlign.RIGHT,
                        ),
                        expand=True,
                        padding=ft.Padding(left=10, right=0, top=0, bottom=0),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,  # Alinha nas extremidades
                vertical_alignment=ft.CrossAxisAlignment.START,
            )

        dialogo_detalhes.title = ft.Row(
            [
                ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=ft.Colors.BLUE_700),
                ft.Text(f"Ficha Técnica — Fila #{posicao}", weight=ft.FontWeight.BOLD),
            ],
            spacing=10,
        )
        dialogo_detalhes.content = ft.Container(
            width=500,
            content=ft.Column(
                [
                    ft.Divider(height=10),
                    criar_linha(ft.Icons.DIRECTIONS_BOAT_OUTLINED, "Nome da Embarcação:", navio.nome, destaque=True),
                    criar_linha(ft.Icons.NUMBERS, "Código IMO ID:", navio.imo_id),
                    criar_linha(ft.Icons.PERSON_OUTLINE, "Capitão Responsável:", capitao),
                    criar_linha(ft.Icons.BUSINESS, "Companhia / Armador:", navio.companhia),
                    criar_linha(ft.Icons.SCALE, "Peso Declarado:", peso),
                    criar_linha(ft.Icons.CATEGORY_OUTLINED, "Categoria Logística:", categoria),
                    criar_linha(ft.Icons.DESCRIPTION_OUTLINED, "Manifesto de Carga:", carga_desc),
                    criar_linha(ft.Icons.AC_UNIT, "Carga Perecível:", perecivel),
                    criar_linha(ft.Icons.ASSIGNMENT_TURNED_IN_OUTLINED, "Doc. Alfandegária:", documentos),
                    ft.Divider(height=10),
                    criar_linha(ft.Icons.STARS, "Score Atual de Fila:", score, destaque=True),
                ],
                tight=True,
                spacing=12,
            ),
        )

        dialogo_detalhes.open = True
        page.update()

    def carregar_dados_fila(e=None, sync=False):
        """Busca os navios validados no banco e monta as linhas da tabela ordenadas."""
        def worker():
            try:
                with obter_sessao() as session:
                    navios = obter_fila_atracacao_dto(session)

                    novas_linhas = []

                    if not navios:
                        txt_vazio.visible = True
                        tabela_fila.visible = False
                    else:
                        txt_vazio.visible = False
                        tabela_fila.visible = True

                        # Varre a lista calculando a posição na fila (index + 1)
                        for idx, navio in enumerate(navios):
                            posicao = idx + 1

                            # Define um texto de observação amigável baseado na perecibilidade
                            obs_texto = (
                                " | ".join(c.descricao for c in navio.cargas)
                                if navio.cargas
                                else "Carga Geral"
                            )
                            if navio.cargas and any(c.eh_perecivel for c in navio.cargas):
                                obs_texto += " ⚠️ [PERECÍVEL]"

                            # Criação do botão "Ver Mais" para a linha atual
                            btn_ver_mais = ft.ElevatedButton(
                                "Ver mais",
                                icon=ft.Icons.INFO_OUTLINED,
                                on_click=lambda e, n=navio, p=posicao: abrir_detalhes_navio(
                                    n, p
                                ),
                                style=ft.ButtonStyle(
                                    color=ft.Colors.BLUE_700,
                                    bgcolor=ft.Colors.BLUE_50,
                                ),
                            )

                            # Adiciona a linha estruturada na tabela visual
                            novas_linhas.append(
                                ft.DataRow(
                                    cells=[
                                        ft.DataCell(
                                            ft.Text(
                                                f"{posicao}º", weight=ft.FontWeight.BOLD
                                             )
                                        ),
                                        ft.DataCell(
                                            ft.Container(
                                                content=ft.Text(
                                                    navio.nome,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    max_lines=1,
                                                ),
                                                width=180,
                                                tooltip=navio.nome,
                                            )
                                        ),
                                        ft.DataCell(
                                            ft.Container(
                                                content=ft.Text(
                                                    obs_texto,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                    max_lines=1,
                                                    color=ft.Colors.BLUE_GREY_700,
                                                ),
                                                width=350,
                                                tooltip=obs_texto,
                                            )
                                        ),
                                        ft.DataCell(btn_ver_mais),
                                    ]
                                )
                            )
                    tabela_fila.rows = novas_linhas
                    page.update()
            except Exception as erro:
                print(f"Erro ao carregar fila de atracação: {erro}")

        if sync:
            worker()
        else:
            Thread(target=worker).start()

    # Força o carregamento assim que a tela abre pela primeira vez
    carregar_dados_fila(sync=True)

    container_fila = ft.Container(
        padding=30,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.FORMAT_LIST_NUMBERED,
                                    size=32,
                                    color=ft.Colors.BLUE_GREY_800,
                                ),
                                ft.Text(
                                    "Fila de Atracação Dinâmica",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.IconButton(
                            ft.Icons.REFRESH,
                            tooltip="Atualizar Fila",
                            on_click=carregar_dados_fila,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    "Abaixo estão listadas as embarcações autorizadas a atracar, ordenadas pelo motor de prioridade do porto.",
                    size=14,
                    color=ft.Colors.GREY_600,
                ),
                ft.Divider(height=20),
                txt_vazio,
                ft.ListView(controls=[tabela_fila], expand=True, spacing=10),
            ],
            expand=True,
        ),
    )

    # Auto-refresh loop a cada 2 segundos se a fila estiver ativa
    def auto_refresh_loop():
        import time
        while True:
            time.sleep(2)
            if not container_fila.page:
                break
            if getattr(page, "active_tab", None) != "fila":
                break
            try:
                carregar_dados_fila(sync=False)
            except Exception:
                pass

    Thread(target=auto_refresh_loop, daemon=True).start()

    return container_fila
