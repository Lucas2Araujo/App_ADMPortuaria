import flet as ft
import asyncio
from cad import obter_sessao_async
from controller_operacao import obter_log_operacoes_dto


class HistoricoView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page

        # Configuração da tabela
        self.tabela_historico = ft.DataTable(
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
            heading_text_style=ft.TextStyle(
                color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.BOLD, size=12
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            columns=[
                ft.DataColumn(ft.Text("DATA/HORA")),
                ft.DataColumn(ft.Text("EVENTO")),
                ft.DataColumn(ft.Text("NAVIO (IMO)")),
                ft.DataColumn(ft.Text("VAGA")),
                ft.DataColumn(ft.Text("OP ID")),
            ],
            rows=[],
        )

        self.txt_vazio = ft.Text(
            "Nenhuma operação registrada.",
            size=13,
            italic=True,
            visible=False,
            color=ft.Colors.ON_SURFACE_VARIANT,
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
                                        ft.Icons.HISTORY,
                                        size=24,
                                        color="#2e7ec1",
                                    ),
                                    ft.Text(
                                        "Histórico de Operações",
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
                    ft.Divider(height=20, color="#dde3ec"),
                    self.txt_vazio,
                    ft.Container(
                        content=ft.ListView(
                            controls=[self.tabela_historico],
                            expand=True,
                        ),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=12,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        )

    def did_mount(self):
        """Called by Flet after this control is added to the page tree."""
        self._page.run_task(self.atualizar)

    async def carregar_dados(self, session):
        logs = await obter_log_operacoes_dto(session)

        novas_linhas = []
        for log in logs:
            hora_str = log.data_hora.strftime("%d/%m/%Y %H:%M")
            navio_str = f"{log.navio_nome} ({log.navio_imo_id})"

            # Badge de Evento
            if log.tipo == "ATRACAO":
                evento_widget = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ARROW_DOWNWARD, color="#10b981", size=14),
                            ft.Text(
                                "Atracação",
                                color="#10b981",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=4,
                    ),
                    bgcolor="#d1fae5",
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12,
                )
            else:
                evento_widget = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ARROW_UPWARD, color="#ef4444", size=14),
                            ft.Text(
                                "Desatracação",
                                color="#ef4444",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=4,
                    ),
                    bgcolor="#fee2e2",
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12,
                )

            novas_linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                hora_str, color=ft.Colors.ON_SURFACE_VARIANT, size=13
                            )
                        ),
                        ft.DataCell(evento_widget),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    navio_str,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                    color=ft.Colors.ON_SURFACE,
                                    weight=ft.FontWeight.W_600,
                                    size=13,
                                ),
                                width=200,
                                tooltip=navio_str,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"Berço {log.vaga_id}",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=13,
                                weight=ft.FontWeight.W_500,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"#{log.id}",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                    ]
                )
            )

        self.tabela_historico.rows = novas_linhas
        self.txt_vazio.visible = len(novas_linhas) == 0
        self.tabela_historico.visible = len(novas_linhas) > 0

    async def atualizar(self, e=None):
        try:
            async with obter_sessao_async() as session:
                await self.carregar_dados(session)
                self.update()
        except Exception as err:
            print(f"Erro ao carregar histórico: {err}")


def obter_view(page: ft.Page):
    return HistoricoView(page)
