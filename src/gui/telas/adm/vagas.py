import flet as ft
import gui.compat
import asyncio
from datetime import datetime
from cad import obter_sessao_async
from controller_operacao import (
    atracar_navio,
    registrar_desatracacao,
    obter_painel_vagas_dto,
)


class VagasView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page

        # Lifecycle flag — prevents orphan tasks after logout
        self._active = False

        # State elements
        self.txt_livres_count = ft.Text(
            "0 livres", size=14, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.txt_ocupadas_count = ft.Text(
            "0 ocupadas", size=14, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.container_bercos = ft.Column(
            spacing=24, expand=True, scroll=ft.ScrollMode.AUTO
        )

        self.loading_atracacao = ft.ProgressRing(visible=False, width=20, height=20)
        self.tipo_atracacao = None
        self.txt_msg_atracacao = ft.Text("")

        self.dialogo_confirmar_atracacao = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Operação de atracação"),
            content=self.txt_msg_atracacao,
            actions=[
                ft.TextButton(
                    "Confirmar atracação",
                    on_click=lambda e: self._page.run_task(
                        self.processar_atracacao_backend
                    ),
                ),
                ft.TextButton("Cancelar", on_click=self.fechar_modal_atracacao),
            ],
        )

        self.loading_desatracacao = ft.ProgressRing(visible=False, width=20, height=20)
        self.imo_desatracacao = None
        self.tipo_desatracacao = None
        self.txt_msg_desatracacao = ft.Text("")

        self.dialogo_confirmar_desatracacao = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Liberação de Berço"),
            content=self.txt_msg_desatracacao,
            actions=[
                ft.TextButton(
                    "Confirmar Saída",
                    on_click=lambda e: self._page.run_task(
                        self.processar_desatracacao_backend
                    ),
                ),
                ft.TextButton("Cancelar", on_click=self.fechar_modal_desatracacao),
            ],
        )

        def hover_atracar_lote(e):
            e.control.bgcolor = "#163d6e" if e.data == "true" else "#0d2b4e"
            e.control.update()

        def hover_desatracar_lote(e):
            e.control.bgcolor = "#fee2e2" if e.data == "true" else "#fff5f5"
            e.control.update()

        btn_atracar_lote_bercos = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, size=16, color="#ffffff"),
                    ft.Text(
                        "Atracar em Lote",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color="#ffffff",
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#0d2b4e",
            padding=ft.padding.only(left=16, top=10, right=16, bottom=10),
            border_radius=12,
            ink=True,
            on_click=lambda e: self.abrir_confirmacao_atracacao("LOTE"),
            on_hover=hover_atracar_lote,
        )

        btn_desatracar_lote_bercos = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.REMOVE, size=16, color="#dc2626"),
                    ft.Text(
                        "Desatracar Lote",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color="#dc2626",
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#fff5f5",
            border=ft.border.all(1, "#fca5a5"),
            padding=ft.padding.only(left=16, top=9, right=16, bottom=9),
            border_radius=12,
            ink=True,
            on_click=lambda e: self.abrir_confirmacao_desatracacao("MASSA"),
            on_hover=hover_desatracar_lote,
        )

        header_vagas = ft.Row(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    border_radius=5,
                                    bgcolor="#16a34a",
                                ),
                                self.txt_livres_count,
                            ],
                            spacing=6,
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    width=10,
                                    height=10,
                                    border_radius=5,
                                    bgcolor="#dc2626",
                                ),
                                self.txt_ocupadas_count,
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=16,
                ),
                ft.Row(
                    [btn_desatracar_lote_bercos, btn_atracar_lote_bercos], spacing=10
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.content = ft.Container(
            padding=30,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.LAYERS,
                                        size=32,
                                        color=ft.Colors.ON_SURFACE,
                                    ),
                                    ft.Text(
                                        "Monitor de Berços",
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.ON_SURFACE,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                tooltip="Atualizar",
                                on_click=lambda e: self._page.run_task(self.atualizar),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=16),
                    header_vagas,
                    ft.Container(height=16),
                    self.container_bercos,
                ],
                expand=True,
            ),
        )

        self._page.overlay.append(self.dialogo_confirmar_atracacao)
        self._page.overlay.append(self.dialogo_confirmar_desatracacao)

    def did_mount(self):
        self._active = True
        self._page.run_task(self.atualizar)
        self._page.run_task(self.auto_refresh_loop)

    def will_unmount(self):
        self._active = False

    def abrir_confirmacao_atracacao(self, tipo):
        self.tipo_atracacao = tipo
        if tipo == "PROXIMO":
            self.txt_msg_atracacao.value = "Deseja atracar o proximo navio?"
        else:
            self.txt_msg_atracacao.value = (
                "Deseja iniciar a atracação em lote de todas as vagas livres?"
            )
        self.dialogo_confirmar_atracacao.open = True
        self._page.update()

    def fechar_modal_atracacao(self, e=None):
        self.dialogo_confirmar_atracacao.open = False
        self._page.update()

    async def processar_atracacao_backend(self):
        self.dialogo_confirmar_atracacao.open = False
        self.loading_atracacao.visible = True
        self._page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                if self.tipo_atracacao == "PROXIMO":
                    sucesso = await atracar_navio(session)
                    if sucesso:
                        msg = "O próximo navio da fila foi atracado com sucesso!"
                        status_cor = ft.Colors.GREEN
                    else:
                        msg = "Nenhum navio disponível na fila ou nenhuma vaga livre."
                        status_cor = ft.Colors.ORANGE

                elif self.tipo_atracacao == "LOTE":
                    sucesso_count = 0
                    while await atracar_navio(session):
                        sucesso_count += 1

                    if sucesso_count > 0:
                        msg = f"Atracação em lote concluída! {sucesso_count} navio(s) atracado(s)."
                        status_cor = ft.Colors.GREEN
                    else:
                        msg = "Nenhum navio pôde ser atracado em lote."
                        status_cor = ft.Colors.ORANGE
        except Exception as err:
            msg = f"Erro na operação de atracação: {err}"
        finally:
            self.loading_atracacao.visible = False
            self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self._page.snack_bar.open = True
            await self.atualizar()
            self._page.update()

    def abrir_confirmacao_desatracacao(self, tipo, imo=None):
        self.tipo_desatracacao = tipo
        self.imo_desatracacao = imo

        if tipo == "INDIVIDUAL":
            self.txt_msg_desatracacao.value = (
                f"Deseja desatracar o navio {imo} e liberar este berço?"
            )
        else:
            self.txt_msg_desatracacao.value = "ATENÇÃO: Deseja realmente desatracar TODOS os navios ativos de todos os berços ao mesmo tempo?"

        self.dialogo_confirmar_desatracacao.open = True
        self._page.update()

    def fechar_modal_desatracacao(self, e=None):
        self.dialogo_confirmar_desatracacao.open = False
        self._page.update()

    async def processar_desatracacao_backend(self):
        self.dialogo_confirmar_desatracacao.open = False
        self.loading_desatracacao.visible = True
        self._page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                if self.tipo_desatracacao == "INDIVIDUAL":
                    await registrar_desatracacao(session, self.imo_desatracacao)
                    msg = f"Navio {self.imo_desatracacao} desatracado com sucesso!"
                    status_cor = ft.Colors.GREEN

                elif self.tipo_desatracacao == "MASSA":
                    vagas = await obter_painel_vagas_dto(session)
                    # Coleta todos os IMOs antes do loop para evitar stale data entre iterações
                    imos_para_desatracar = [
                        vaga.navio_atracado.imo_id
                        for vaga in vagas
                        if vaga.status == "OCUPADA" and vaga.navio_atracado
                    ]
                    sucesso_count = 0
                    for imo in imos_para_desatracar:
                        resultado = await registrar_desatracacao(session, imo)
                        if resultado:
                            sucesso_count += 1

                    if sucesso_count > 0:
                        msg = f"Operação em massa concluída! {sucesso_count} navio(s) liberado(s)."
                        status_cor = ft.Colors.GREEN
                    else:
                        msg = "Nenhum navio atracado encontrado para liberar."
                        status_cor = ft.Colors.ORANGE
        except Exception as err:
            msg = f"Erro na operação de desatracação: {err}"
        finally:
            self.loading_desatracacao.visible = False
            self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self._page.snack_bar.open = True
            await self.atualizar()
            self._page.update()

    @staticmethod
    def _hover_action_btn(e, base_bg, hover_bg):
        e.control.bgcolor = hover_bg if e.data == "true" else base_bg
        e.control.update()

    def _build_content_livre(self, next_in_queue) -> list:
        """Returns the content controls for a free berth card."""
        items = [
            ft.Text("Disponível", size=14, weight=ft.FontWeight.W_600, color="#16a34a"),
            ft.Container(expand=True),
        ]
        if next_in_queue:
            items.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ARROW_DOWNWARD, size=14, color="#ffffff"),
                            ft.Text(
                                "Atracar Próximo",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color="#ffffff",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    bgcolor="#0d2b4e",
                    border_radius=8,
                    padding=ft.padding.only(left=0, top=8, right=0, bottom=8),
                    ink=True,
                    on_click=lambda e: self.abrir_confirmacao_atracacao("PROXIMO"),
                    on_hover=lambda e, bg="#0d2b4e", h="#163d6e": self._hover_action_btn(
                        e, bg, h
                    ),
                )
            )
        else:
            items.append(
                ft.Text("Fila vazia", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
            )
        return items

    def _build_content_ocupada(self, vaga) -> list:
        """Returns the content controls for an occupied berth card."""
        navio = vaga.navio_atracado
        navio_nome = navio.nome if navio else "Desconhecido"
        navio_imo = navio.imo_id if navio else "---"
        navio_comp = navio.companhia if navio else "---"

        if vaga.data_hora_inicio:
            minutos = int((datetime.now() - vaga.data_hora_inicio).total_seconds() / 60)
            tempo_txt = (
                f"{minutos} min"
                if minutos < 60
                else f"{minutos // 60}h {minutos % 60}min"
            )
        else:
            tempo_txt = "N/A"

        return [
            ft.Column(
                [
                    ft.Text(
                        navio_nome,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    ft.Text(
                        f"IMO {navio_imo}", size=12, color=ft.Colors.ON_SURFACE_VARIANT
                    ),
                    ft.Text(
                        navio_comp,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                ],
                spacing=2,
            ),
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.ACCESS_TIME,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        f"{tempo_txt} atracado",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=6,
            ),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_UPWARD, size=14, color="#dc2626"),
                        ft.Text(
                            "Desatracar",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color="#dc2626",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
                bgcolor="#fff5f5",
                border=ft.border.all(1, "#fca5a5"),
                border_radius=8,
                padding=ft.padding.only(left=0, top=8, right=0, bottom=8),
                ink=True,
                on_click=lambda e, imo=navio_imo: self.abrir_confirmacao_desatracacao(
                    "INDIVIDUAL", imo
                ),
                on_hover=lambda e, bg="#fff5f5", h="#fee2e2": self._hover_action_btn(
                    e, bg, h
                ),
            ),
        ]

    def _build_card_berco(self, vaga, next_in_queue) -> ft.Container:
        """Assembles and returns a complete berth card."""
        free = vaga.status == "LIVRE"
        # Cores adaptativas: fundo translúcido sobre a cor Surface do tema
        color = "#16a34a" if free else "#dc2626"
        bg_color = ft.Colors.with_opacity(0.08, color)
        border_color = ft.Colors.with_opacity(0.4, color)

        header = ft.Row(
            [
                ft.Text(
                    f"BERÇO {vaga.id:02d}",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
                ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        content = (
            self._build_content_livre(next_in_queue)
            if free
            else self._build_content_ocupada(vaga)
        )

        return ft.Container(
            content=ft.Column([header, *content], expand=True),
            height=220,
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=12,
            padding=16,
        )

    async def carregar_dados(self, session):
        from ord_propriety import obter_fila_atracacao_dto

        vagas = await obter_painel_vagas_dto(session)
        fila = await obter_fila_atracacao_dto(session)
        next_in_queue = fila[0] if fila else None

        livres = sum(1 for v in vagas if v.status == "LIVRE")
        ocupadas = len(vagas) - livres

        self.txt_livres_count.value = f"{livres} livre{'s' if livres != 1 else ''}"
        self.txt_ocupadas_count.value = (
            f"{ocupadas} ocupada{'s' if ocupadas != 1 else ''}"
        )

        cards_bercos = [self._build_card_berco(v, next_in_queue) for v in vagas]

        grid_bercos = ft.ResponsiveRow(
            [
                ft.Column(col={"sm": 12, "md": 6, "lg": 3}, controls=[c])
                for c in cards_bercos
            ],
            run_spacing=16,
        )

        self.container_bercos.controls = [
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "TERMINAL PRINCIPAL",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Container(
                                expand=True, height=1, bgcolor=ft.Colors.OUTLINE_VARIANT
                            ),
                        ],
                        spacing=12,
                    ),
                    grid_bercos,
                ],
                spacing=12,
            )
        ]

    async def atualizar(self, e=None):
        try:
            async with obter_sessao_async() as session:
                await self.carregar_dados(session)
                self.update()
        except Exception as err:
            print(f"Erro ao carregar dados dos berços: {err}")

    async def auto_refresh_loop(self):
        while self._active:
            await asyncio.sleep(3)
            try:
                if not self._active:
                    break
                if getattr(self._page, "active_tab", None) == "vagas":
                    await self.atualizar()
            except Exception:
                pass


def obter_view(page: ft.Page):
    return VagasView(page)
