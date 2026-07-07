import flet as ft
import gui.compat
import asyncio
from datetime import datetime, timedelta
from cad import obter_sessao_async


class DashboardView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page
        self._active = False  # lifecycle flag — stops loop on logout

        # State elements
        self.txt_vagas = ft.Text(
            "...", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE
        )
        self.txt_fila = ft.Text(
            "0", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE
        )
        self.txt_pendentes = ft.Text(
            "0", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE
        )
        self.txt_concluidos = ft.Text(
            "0", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE
        )
        self.txt_taxa = ft.Text(
            "0.0", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE
        )

        self.grafico_row = ft.Row(
            [],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            vertical_alignment=ft.CrossAxisAlignment.END,
            expand=True,
        )

        self.container_grafico = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Atracações Diárias (Última Semana)",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.Divider(height=20, color="transparent"),
                    self.grafico_row,
                ]
            ),
            bgcolor=ft.Colors.SURFACE,
            height=250,
            padding=20,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        self.coluna_logs = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.caixa_logs = self.criar_caixa(
            "Últimas Operações", ft.Icons.HISTORY, [self.coluna_logs]
        )

        self.coluna_proximos = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.caixa_proximos = self.criar_caixa(
            "Próximos na Fila", ft.Icons.FORMAT_LIST_NUMBERED, [self.coluna_proximos]
        )

        self.coluna_vagas = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.caixa_vagas = self.criar_caixa(
            "Monitor de Berços", ft.Icons.ANCHOR, [self.coluna_vagas]
        )

        # Content initialization
        self.content = ft.Container(
            padding=30,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.PIE_CHART,
                                        size=24,
                                        color="#2e7ec1",
                                    ),
                                    ft.Text(
                                        "Dashboard Executivo",
                                        size=20,
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
                                icon_color="#5a7494",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                    ft.Row(
                        [
                            self.create_stat_card(
                                "Vagas Livres / Total",
                                self.txt_vagas,
                                ft.Icons.ANCHOR,
                                "#3b82f6",
                            ),
                            self.create_stat_card(
                                "Navios na Fila",
                                self.txt_fila,
                                ft.Icons.FORMAT_LIST_NUMBERED,
                                "#f59e0b",
                            ),
                            self.create_stat_card(
                                "Auditorias Pendentes",
                                self.txt_pendentes,
                                ft.Icons.HOURGLASS_BOTTOM,
                                "#ef4444",
                            ),
                            self.create_stat_card(
                                "Operações Concluídas",
                                self.txt_concluidos,
                                ft.Icons.CHECK_CIRCLE,
                                "#10b981",
                            ),
                            self.create_stat_card(
                                "Taxa de Atracação/Dia",
                                self.txt_taxa,
                                ft.Icons.SPEED,
                                "#8b5cf6",
                            ),
                        ],
                        spacing=15,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    self.container_grafico,
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        [self.caixa_logs, self.caixa_proximos, self.caixa_vagas],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        spacing=15,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def did_mount(self):
        """Called by Flet after this control is added to the page tree."""
        self._active = True
        self._page.run_task(self.atualizar)
        self._page.run_task(self.auto_refresh_loop)

    def will_unmount(self):
        self._active = False

    def criar_caixa(self, titulo, icone, controles_lista):
        return ft.Container(
            expand=1,
            height=340,
            bgcolor=ft.Colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Column(
                [
                    ft.Container(
                        padding=15,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        border_radius=12,
                        content=ft.Row(
                            [
                                ft.Icon(icone, color="#2e7ec1", size=18),
                                ft.Text(
                                    titulo,
                                    weight=ft.FontWeight.W_600,
                                    size=14,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                    ),
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    ft.Container(
                        padding=15,
                        expand=True,
                        content=ft.Column(
                            controles_lista, spacing=5, scroll=ft.ScrollMode.AUTO
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    def create_stat_card(self, title, text_control, icon, icon_color):
        return ft.Container(
            expand=1,
            bgcolor=ft.Colors.SURFACE,
            padding=20,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=24, color=icon_color),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(height=5),
                    text_control,
                    ft.Text(
                        title,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    async def carregar_dados(self, session):
        # Update metrics
        from controller_operacao import obter_contadores_dashboard

        counts = await obter_contadores_dashboard(session)
        self.txt_vagas.value = f"{counts['vagas_livres']} / {counts['total_vagas']}"
        self.txt_fila.value = str(counts["total_validado"])
        self.txt_pendentes.value = str(counts["total_pendente"])
        self.txt_concluidos.value = str(counts["total_finalizado"])

        await self._atualizar_fila(session)
        await self._atualizar_vagas(session)
        await self._atualizar_grafico(session)
        await self._atualizar_logs(session)

    async def _atualizar_fila(self, session):
        """Update queue preview panel."""
        from ord_propriety import obter_fila_atracacao_dto

        fila = await obter_fila_atracacao_dto(session)
        proximos = fila[:10]  # Alterado para 10 como solicitado
        if not proximos:
            self.coluna_proximos.controls = [
                ft.Text(
                    "A fila está vazia no momento.",
                    size=13,
                    italic=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            ]
        else:
            self.coluna_proximos.controls = [
                ft.Text(
                    f"{idx+1}º - {p.nome}",
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                )
                for idx, p in enumerate(proximos)
            ]

    async def _atualizar_vagas(self, session):
        """Update berths status preview panel."""
        from controller_operacao import obter_painel_vagas_dto

        vagas = await obter_painel_vagas_dto(session)
        self.coluna_vagas.controls = [self._linha_vaga(v) for v in vagas]

    def _linha_vaga(self, v):
        """Build a single berth status row widget."""
        if v.status == "LIVRE":
            return ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="#10b981", size=14),
                    ft.Text(
                        f"Berço {v.id}: Livre",
                        size=13,
                        color="#10b981",
                        weight=ft.FontWeight.W_600,
                    ),
                ]
            )
        return ft.Row(
            [
                ft.Icon(ft.Icons.CANCEL, color="#ef4444", size=14),
                ft.Text(
                    f"Berço {v.id}: Ocupado",
                    size=13,
                    color="#ef4444",
                    weight=ft.FontWeight.W_500,
                ),
            ]
        )

    async def _atualizar_grafico(self, session):
        """Update the weekly docking bar chart."""
        from controller_operacao import obter_contagem_atracacoes_dia

        hoje_date = datetime.now().date()
        contagem_por_dia = await obter_contagem_atracacoes_dia(session, 7)
        total_semana = sum(contagem_por_dia.values())
        taxa_diaria = total_semana / 7.0
        self.txt_taxa.value = f"{taxa_diaria:.1f}"

        pico = max(contagem_por_dia.values(), default=1) or 1
        altura_max = 100
        novo_grafico = []
        for i in range(6, -1, -1):
            dia_iter = hoje_date - timedelta(days=i)
            dia_label = dia_iter.strftime("%d/%m")
            valor_dia = contagem_por_dia.get(dia_iter.isoformat(), 0)
            altura_barra = max(10, (valor_dia / pico) * altura_max)
            novo_grafico.append(
                ft.Column(
                    [
                        ft.Text(
                            str(valor_dia),
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(
                            width=30,
                            height=altura_barra,
                            bgcolor="#2e7ec1",
                            border_radius=4,
                            tooltip=f"{valor_dia} atracações em {dia_label}",
                        ),
                        ft.Text(dia_label, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        self.grafico_row.controls = novo_grafico

    async def _atualizar_logs(self, session):
        """Update the recent operations log panel."""
        from controller_operacao import obter_log_operacoes_dto

        eventos_log = (await obter_log_operacoes_dto(session))[:10]
        if not eventos_log:
            self.coluna_logs.controls = [
                ft.Text(
                    "Nenhuma operação registrada.",
                    size=13,
                    italic=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            ]
        else:
            self.coluna_logs.controls = [self._linha_log(ev) for ev in eventos_log]

    def _linha_log(self, ev):
        """Build a single log entry row widget."""
        hora_ev = ev.data_hora.strftime("%d/%m %H:%M")
        if ev.tipo == "DESATRACAO":
            icon = ft.Icon(ft.Icons.ARROW_UPWARD, color="#ef4444", size=14)
            texto = f"Saída: {ev.navio_nome} (B{ev.vaga_id}) — {hora_ev}"
        else:
            icon = ft.Icon(ft.Icons.ARROW_DOWNWARD, color="#10b981", size=14)
            texto = f"Entrada: {ev.navio_nome} (B{ev.vaga_id}) — {hora_ev}"
        return ft.Row(
            [
                icon,
                ft.Container(
                    content=ft.Text(
                        texto,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    expand=True,
                ),
            ]
        )

    async def atualizar(self, e=None):
        try:
            async with obter_sessao_async() as session:
                await self.carregar_dados(session)
                self.update()
        except Exception as err:
            print(f"Erro ao carregar dados do dashboard: {err}")

    async def auto_refresh_loop(self):
        while self._active:
            await asyncio.sleep(5)
            try:
                if not self._active:
                    break
                if getattr(self._page, "active_tab", None) == "dashboard":
                    await self.atualizar()
            except Exception:
                pass


def obter_view(page: ft.Page):
    return DashboardView(page)
