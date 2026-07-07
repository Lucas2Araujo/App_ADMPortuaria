import os
import sys
import flet as ft
import gui.compat
import asyncio
import math
from cad import obter_sessao_async
from ord_propriety import obter_fila_atracacao_dto


class FilaView(ft.Container):
    """Manager class for the mooring queue view.

    This class handles the creation and updating of the Flet layout and controls,
    reducing Cognitive Complexity by modularizing event handling and UI building.
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page
        self._active = False  # lifecycle flag — stops loop on logout

        # Table showing the queue of ships
        self.tabela_fila = ft.DataTable(
            heading_row_color=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
            border_radius=12,
            horizontal_margin=20,
            column_spacing=20,
            heading_text_style=ft.TextStyle(
                color=ft.Colors.ON_SURFACE_VARIANT, size=12, weight=ft.FontWeight.BOLD
            ),
            columns=[
                ft.DataColumn(ft.Text("POSIÇÃO")),
                ft.DataColumn(ft.Text("EMBARCAÇÃO")),
                ft.DataColumn(ft.Text("OBSERVAÇÃO / CARGA")),
                ft.DataColumn(ft.Text("AÇÕES")),
            ],
            rows=[],
        )
        self.tabela_scroll = ft.ListView(
            controls=[self.tabela_fila],
            expand=True,
        )

        # Empty state container
        self.txt_vazio = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=36, color="#86efac"),
                    ft.Text(
                        "Fila vazia — todos os navios foram atracados.",
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=0, top=56, right=0, bottom=56),
            alignment=ft.Alignment(0, 0),
            visible=False,
        )

        # Detail dialog configuration
        self.dialogo_detalhes = ft.AlertDialog(
            actions=[
                ft.TextButton("Fechar Janela", on_click=self.fechar_dialogo),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=self.fechar_dialogo,
        )
        self._page.overlay.append(self.dialogo_detalhes)

        # Configuração da Paginação
        self.pagina_atual = 1
        self.itens_por_pagina = 10
        self.total_paginas = 1

        self.btn_anterior = ft.IconButton(
            icon=ft.Icons.NAVIGATE_BEFORE,
            tooltip="Página Anterior",
            on_click=self.pagina_anterior,
            disabled=True,
        )
        self.txt_pagina = ft.Text("Página 1 de 1", size=13, weight=ft.FontWeight.BOLD)
        self.btn_proximo = ft.IconButton(
            icon=ft.Icons.NAVIGATE_NEXT,
            tooltip="Próxima Página",
            on_click=self.proxima_pagina,
            disabled=True,
        )
        self.txt_paginas_info = ft.Text(
            "Exibindo 0-0 de 0 itens", size=12, color=ft.Colors.ON_SURFACE_VARIANT
        )

        self.dropdown_limite = ft.Dropdown(
            options=[
                ft.dropdown.Option("10", text="10 por página"),
                ft.dropdown.Option("25", text="25 por página"),
                ft.dropdown.Option("50", text="50 por página"),
                ft.dropdown.Option("todos", text="Todos"),
            ],
            value="10",
            on_select=self.alterar_limite,
            width=150,
            height=40,
            text_size=12,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
        )

        self.row_paginacao = ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [self.txt_paginas_info, self.dropdown_limite],
                        spacing=20,
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [self.btn_anterior, self.txt_pagina, self.btn_proximo],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        )

        # Counter text
        self.txt_contador = ft.Text(
            "0 navios aguardando", size=14, color=ft.Colors.ON_SURFACE_VARIANT
        )

        # Mooring/refresh button
        self.btn_atracar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.REFRESH, size=16, color="#ffffff"),
                    ft.Text(
                        "Atualizar Fila",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color="#ffffff",
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#0d2b4e",
            padding=ft.Padding(left=20, top=10, right=20, bottom=10),
            border_radius=12,
            ink=True,
            on_click=lambda e: self._page.run_task(self.carregar_dados_fila),
            on_hover=self.hover_btn_atracar,
        )

        # Main layout container
        self.content = ft.Container(
            padding=32,
            expand=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            self.txt_contador,
                            self.btn_atracar,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=8),
                    ft.Container(
                        bgcolor=ft.Colors.SURFACE,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        content=ft.Stack(
                            [
                                ft.Column(
                                    [
                                        self.tabela_scroll,
                                        self.row_paginacao,
                                    ],
                                    spacing=0,
                                    expand=True,
                                ),
                                self.txt_vazio,
                            ],
                            expand=True,
                        ),
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        )

    def did_mount(self):
        self._active = True
        self._page.run_task(self.carregar_dados_fila)
        self._page.run_task(self.auto_refresh_loop)

    def will_unmount(self):
        self._active = False

    def fechar_dialogo(self, e):
        """Closes the ship details dialog."""
        self.dialogo_detalhes.open = False
        self._page.update()

    def abrir_detalhes_navio(self, navio, posicao):
        """Builds and opens the details dialog for a given ship."""

        capitao = getattr(
            navio, "nome_capitao", getattr(navio, "capitao", "Não informado")
        )
        peso_total = (
            sum(c.quantidade_toneladas for c in navio.cargas) if navio.cargas else 0
        )
        peso = f"{peso_total} Toneladas"
        categoria = (
            ", ".join({c.categoria for c in navio.cargas}) if navio.cargas else "N/A"
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
        descricao_carga = (
            " | ".join(c.descricao for c in navio.cargas if c.descricao)
            if navio.cargas
            else "N/A"
        )
        score = f"{navio.score:.2f}"

        self.dialogo_detalhes.title = ft.Text(
            f"Ficha Técnica — Posição #{posicao}", weight=ft.FontWeight.BOLD
        )
        self.dialogo_detalhes.content = ft.Column(
            [
                ft.Text(
                    f"Nome da Embarcação: {navio.nome}",
                    size=14,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(f"Código IMO ID: {navio.imo_id}", size=14),
                ft.Text(f"Capitão Responsável: {capitao}", size=14),
                ft.Text(f"Companhia / Armador: {navio.companhia}", size=14),
                ft.Text(f"Peso Declarado: {peso}", size=14),
                ft.Text(f"Categoria Logística: {categoria}", size=14),
                ft.Text(f"Descrição da Carga: {descricao_carga}", size=14),
                ft.Text(f"Carga Perecível: {perecivel}", size=14),
                ft.Text(f"Documentação Alfandegária: {documentos}", size=14),
                ft.Text(
                    f"Score de Fila: {score}",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
            ],
            tight=True,
            spacing=10,
        )
        self.dialogo_detalhes.open = True
        self._page.update()

    def hover_ver_mais(self, e):
        """Hover effect handler for the 'Ver mais' button."""
        e.control.bgcolor = "#e8eef6" if e.data == "true" else None
        e.control.update()

    def hover_btn_atracar(self, e):
        """Hover effect handler for the main mooring/refresh button."""
        e.control.bgcolor = "#163d6e" if e.data == "true" else "#0d2b4e"
        e.control.update()

    def pagina_anterior(self, e):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
            self._page.run_task(self.carregar_dados_fila)

    def proxima_pagina(self, e):
        if self.pagina_atual < self.total_paginas:
            self.pagina_atual += 1
            self._page.run_task(self.carregar_dados_fila)

    def alterar_limite(self, e):
        limite_val = self.dropdown_limite.value
        if limite_val == "todos":
            self.itens_por_pagina = 1000000
        else:
            self.itens_por_pagina = int(limite_val)
        self.pagina_atual = 1
        self._page.run_task(self.carregar_dados_fila)

    async def carregar_dados_fila(self, e=None):
        """Loads mooring queue data asynchronously from the database."""
        try:
            async with obter_sessao_async() as session:
                navios = await obter_fila_atracacao_dto(session)

                self.txt_contador.value = (
                    f"{len(navios)} navio{'s' if len(navios) != 1 else ''} aguardando"
                )

                if not navios:
                    self.txt_vazio.visible = True
                    self.tabela_scroll.visible = False
                    self.tabela_fila.rows = []
                    self.row_paginacao.visible = False
                else:
                    self.txt_vazio.visible = False
                    self.tabela_scroll.visible = True
                    self.row_paginacao.visible = True

                    total_itens = len(navios)
                    limite = self.itens_por_pagina
                    self.total_paginas = max(1, (total_itens + limite - 1) // limite)

                    if self.pagina_atual > self.total_paginas:
                        self.pagina_atual = self.total_paginas

                    inicio = (self.pagina_atual - 1) * limite
                    fim = min(inicio + limite, total_itens)
                    navios_pagina = navios[inicio:fim]

                    novas_linhas = []
                    for idx, navio in enumerate(navios_pagina):
                        posicao = inicio + idx + 1
                        linha = self._criar_linha_navio(navio, posicao)
                        novas_linhas.append(linha)
                    self.tabela_fila.rows = novas_linhas

                    # Atualizar controles de paginação
                    self.txt_pagina.value = (
                        f"Página {self.pagina_atual} de {self.total_paginas}"
                    )
                    self.btn_anterior.disabled = self.pagina_atual <= 1
                    self.btn_proximo.disabled = self.pagina_atual >= self.total_paginas

                    limite_texto = (
                        "Todos" if limite >= 1000000 else f"{inicio + 1}-{fim}"
                    )
                    self.txt_paginas_info.value = (
                        f"Exibindo {limite_texto} de {total_itens} itens"
                    )

                self._page.update()
        except Exception as erro:
            print(f"Erro ao carregar fila de atracação: {erro}")

    def _obter_texto_cargas(self, cargas):
        """Formats the cargo descriptions for row observation text."""
        if not cargas:
            return "Carga Geral"
        descricoes = [c.descricao for c in cargas]
        if len(descricoes) > 3:
            return " | ".join(descricoes[:3]) + " | ..."
        return " | ".join(descricoes)

    def _criar_linha_navio(self, navio, posicao):
        """Helper method to construct a ft.DataRow for a specific ship in the queue."""
        obs_texto = self._obter_texto_cargas(navio.cargas)
        eh_perecivel = navio.cargas and any(c.eh_perecivel for c in navio.cargas)

        btn_ver_mais = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color="#2e7ec1"),
                    ft.Text(
                        "Ver mais", size=12, weight=ft.FontWeight.W_600, color="#2e7ec1"
                    ),
                ],
                spacing=6,
            ),
            border=ft.Border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
            padding=ft.Padding(left=14, top=8, right=14, bottom=8),
            ink=True,
            on_click=lambda e, n=navio, p=posicao: self.abrir_detalhes_navio(n, p),
            on_hover=self.hover_ver_mais,
        )

        posicao_widget = ft.Container(
            content=ft.Container(
                content=ft.Text(
                    str(posicao), size=12, weight=ft.FontWeight.BOLD, color="#ffffff"
                ),
                bgcolor="#0d2b4e",
                border_radius=16,
                width=32,
                height=32,
                alignment=ft.Alignment(0, 0),
            ),
            width=80,
            alignment=ft.Alignment(-1, 0),
        )

        acoes_widget = ft.Container(
            content=btn_ver_mais,
            width=120,
            alignment=ft.Alignment(-1, 0),
        )

        vessel_widget = ft.Column(
            [
                ft.Text(
                    navio.nome,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Text(
                    f"IMO {navio.imo_id}",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    font_family="monospace",
                ),
            ],
            spacing=2,
        )

        cargo_text = ft.Text(
            obs_texto, size=13, color=ft.Colors.ON_SURFACE, weight=ft.FontWeight.W_500
        )
        col_controls = [cargo_text]

        if eh_perecivel:
            selo_perecivel = ft.Container(
                content=ft.Text(
                    "Perecível", size=11, weight=ft.FontWeight.BOLD, color="#d97706"
                ),
                bgcolor="#fffbeb",
                border=ft.Border.all(0.5, "#fef3c7"),
                padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                border_radius=4,
            )
            col_controls.append(selo_perecivel)

        cargo_widget = ft.Container(
            content=ft.Column(
                col_controls,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            alignment=ft.Alignment(-1, 0),
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(posicao_widget),
                ft.DataCell(vessel_widget),
                ft.DataCell(cargo_widget),
                ft.DataCell(acoes_widget),
            ]
        )

    async def auto_refresh_loop(self):
        """Asynchronous loop that refreshes the queue data periodically."""
        while self._active:
            await asyncio.sleep(2)
            try:
                if not self._active:
                    break
                if getattr(self._page, "active_tab", None) == "fila":
                    await self.carregar_dados_fila()
            except Exception:
                pass


def obter_view(page: ft.Page):
    """Factory function that returns the mooring queue container."""
    return FilaView(page)
