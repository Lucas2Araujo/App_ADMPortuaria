import flet as ft
import gui.compat
import asyncio
import math
from cad import obter_sessao_async
from controller_cadastros import (
    auditar_navio_individual,
    auditar_solicitacoes_pendentes,
    obter_solicitacoes_pendentes_dto,
    CargaNaoClassificadaError,
    classificar_carga,
)


class AuditoriaView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page
        self._active = False  # lifecycle flag — stops loop on logout

        # Configuração da tabela principal com cores e bordas da nova UI
        self.tabela_pendentes = ft.DataTable(
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
            heading_text_style=ft.TextStyle(
                color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.BOLD, size=12
            ),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            column_spacing=15,
            horizontal_margin=15,
            columns=[
                ft.DataColumn(ft.Text("IMO")),
                ft.DataColumn(ft.Text("EMBARCAÇÃO")),
                ft.DataColumn(ft.Text("CAPITÃO")),
                ft.DataColumn(ft.Text("CARGA")),
                ft.DataColumn(ft.Text("DOCS.")),
                ft.DataColumn(ft.Text("AÇÕES")),
            ],
            rows=[],
        )

        self.txt_vazio_auditoria = ft.Text(
            "Nenhuma solicitação pendente no momento.",
            size=12,
            italic=True,
            visible=False,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        self.imo_em_auditoria = None
        self.acao_em_auditoria = None
        self._is_batch_audit = False

        # Modal de Confirmação Normal
        self.txt_mensagem_modal = ft.Text("")
        self.dialogo_confirmacao = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HELP_OUTLINE, color="#2e7ec1"),
                    ft.Text(
                        "Confirmar Auditoria",
                        color="#0d1f35",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            content=self.txt_mensagem_modal,
            actions=[
                ft.Button(
                    "Cancelar",
                    on_click=self.fechar_modal,
                    style=ft.ButtonStyle(
                        color="#5a7494", bgcolor="transparent", elevation=0
                    ),
                ),
                ft.Button(
                    "Confirmar",
                    on_click=lambda e: self._page.run_task(
                        self.__auditar_documentacao_navio
                    ),
                    style=ft.ButtonStyle(bgcolor="#0d2b4e", color="white"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.modal_classificacao = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#dc2626"),
                    ft.Text(
                        "Classificação Requerida",
                        color="#dc2626",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            content=ft.Container(),  # Dinâmico
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self.fechar_modal_classificacao,
                    style=ft.ButtonStyle(color="#5a7494"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.erro_carga_pendente = None  # Guarda a exceção original

        # Controle de Leitura de Descrição Customizada ("Outros")
        self.imos_lidos = set()
        self.imo_em_leitura = None
        self.txt_descricao_carga = ft.Text("", size=14, color="#334155")
        self.dialogo_leitura = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DESCRIPTION, color="#2e7ec1"),
                    ft.Text(
                        "Descrição da Carga",
                        color="#0d1f35",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            content=ft.Container(
                content=self.txt_descricao_carga,
                bgcolor="#f1f5f9",
                padding=15,
                border_radius=8,
                width=450,
            ),
            actions=[
                ft.Button(
                    "Confirmar Leitura",
                    on_click=self.confirmar_leitura_carga,
                    style=ft.ButtonStyle(bgcolor="#0d2b4e", color="white"),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Modal de Seleção de Perecibilidade (Aprovar carga Outros)
        self._imo_aprovacao_outros = None
        self._nome_aprovacao_outros = None
        self.modal_perecibilidade = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.LOCAL_SHIPPING, color="#0d2b4e"),
                    ft.Text(
                        "Classificar Perecibilidade",
                        color="#0d1f35",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            content=ft.Column(
                [
                    ft.Text(
                        "Antes de aprovar, defina o nível de perecibilidade desta carga:",
                        size=13,
                        color="#334155",
                    ),
                    ft.Container(height=8),
                    ft.Button(
                        "Ultra Perecivel (Medicamentos / Carnes)",
                        on_click=lambda e: self._page.run_task(
                            self._aprovar_outros, "URGENTE_PERECIVEL", True
                        ),
                        width=400,
                        style=ft.ButtonStyle(bgcolor="#fee2e2", color="#dc2626"),
                    ),
                    ft.Button(
                        "Alta Perecibilidade (Frutas / Laticínios)",
                        on_click=lambda e: self._page.run_task(
                            self._aprovar_outros, "ALTA_PERECIBILIDADE", True
                        ),
                        width=400,
                        style=ft.ButtonStyle(bgcolor="#ffedd5", color="#ea580c"),
                    ),
                    ft.Button(
                        "Baixa Perecibilidade (Grãos Úmidos)",
                        on_click=lambda e: self._page.run_task(
                            self._aprovar_outros, "BAIXA_PERECIBILIDADE", True
                        ),
                        width=400,
                        style=ft.ButtonStyle(bgcolor="#fef3c7", color="#d97706"),
                    ),
                    ft.Button(
                        "Comum (Não Perecivel)",
                        on_click=lambda e: self._page.run_task(
                            self._aprovar_outros, "COMUM", False
                        ),
                        width=400,
                        style=ft.ButtonStyle(bgcolor="#f1f5f9", color="#64748b"),
                    ),
                ],
                tight=True,
                spacing=8,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self._fechar_modal_perecibilidade,
                    style=ft.ButtonStyle(color="#5a7494"),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

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

        self.content = ft.Container(
            padding=30,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.FACT_CHECK,
                                        size=24,
                                        color="#2e7ec1",
                                    ),
                                    ft.Text(
                                        "Auditoria de Solicitações",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.ON_SURFACE,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.REFRESH,
                                        tooltip="Atualizar",
                                        on_click=lambda e: self._page.run_task(
                                            self.atualizar
                                        ),
                                        icon_color="#5a7494",
                                    ),
                                    ft.Button(
                                        "Auditar Todos Automaticamente",
                                        icon=ft.Icons.FACT_CHECK,
                                        on_click=lambda e: self._page.run_task(
                                            self.auditar_todos_pendentes
                                        ),
                                        tooltip="Aprova navios com documentação completa e rejeita os demais",
                                        style=ft.ButtonStyle(
                                            bgcolor="#0d2b4e",
                                            color=ft.Colors.WHITE,
                                            padding=15,
                                            shape=ft.RoundedRectangleBorder(radius=8),
                                        ),
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(color=ft.Colors.OUTLINE_VARIANT, height=20),
                    self.txt_vazio_auditoria,
                    ft.ListView(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                self.tabela_pendentes,
                                                self.row_paginacao,
                                            ],
                                            spacing=0,
                                        ),
                                        bgcolor=ft.Colors.SURFACE,
                                        border_radius=12,
                                    )
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                            )
                        ],
                        expand=True,
                        spacing=10,
                    ),
                ]
            ),
        )

        self._page.overlay.extend(
            [
                self.dialogo_confirmacao,
                self.modal_classificacao,
                self.dialogo_leitura,
                self.modal_perecibilidade,
            ]
        )

    def did_mount(self):
        """Called by Flet after this control is added to the page tree."""
        self._active = True
        self._page.run_task(self.atualizar)
        self._page.run_task(self.auto_refresh_loop)

    def will_unmount(self):
        self._active = False

    def abrir_confirmacao(self, imo, nome, acao):
        self.imo_em_auditoria = imo
        self.acao_em_auditoria = acao
        self.txt_mensagem_modal.value = (
            f"Deseja {acao.lower()} a solicitação do navio {nome} ({imo})?"
        )
        self.dialogo_confirmacao.open = True
        self._page.update()

    def fechar_modal(self, e=None):
        self.dialogo_confirmacao.open = False
        self._page.update()

    def fechar_modal_classificacao(self, e=None):
        self.modal_classificacao.open = False
        self.erro_carga_pendente = None
        self._page.update()

    def abrir_leitura(self, imo, nome, desc):
        self.imo_em_leitura = imo
        self.txt_descricao_carga.value = (
            f"Descrição da carga declarada para o navio {nome} ({imo}):\n\n{desc}"
        )
        self.dialogo_leitura.open = True
        self._page.update()

    def confirmar_leitura_carga(self, e):
        """Confirma a leitura da descrição da carga e fecha o diálogo."""
        if self.imo_em_leitura:
            self.imos_lidos.add(self.imo_em_leitura)
            self.imo_em_leitura = None
        # Sempre fecha o diálogo, mesmo em condição de corrida
        self.dialogo_leitura.open = False
        self._page.run_task(self.atualizar)
        self._page.update()

    def _fechar_modal_perecibilidade(self, e=None):
        self.modal_perecibilidade.open = False
        self._imo_aprovacao_outros = None
        self._nome_aprovacao_outros = None
        self._page.update()

    def abrir_aprovacao_outros(self, imo, nome):
        """Abre o seletor de perecibilidade obrigatório para cargas Outros ao aprovar."""
        self._imo_aprovacao_outros = imo
        self._nome_aprovacao_outros = nome
        self.modal_perecibilidade.open = True
        self._page.update()

    async def _aprovar_outros(self, categoria: str, eh_perecivel: bool):
        """Classifica a carga Outros e depois executa a aprovação."""
        self.modal_perecibilidade.open = False
        self._page.update()

        imo = self._imo_aprovacao_outros
        self._imo_aprovacao_outros = None
        self._nome_aprovacao_outros = None

        if not imo:
            return

        try:
            async with obter_sessao_async() as session:
                # Busca o ID da carga pendente deste navio para classificar
                navios = await obter_solicitacoes_pendentes_dto(session)
                navio = next((n for n in navios if n.imo_id == imo), None)
                if navio:
                    for carga in navio.cargas:
                        if carga.categoria == "OUTROS_PENDENTE":
                            await classificar_carga(
                                session, carga.id, categoria, eh_perecivel
                            )

            # Agora aprova normalmente
            self.imo_em_auditoria = imo
            self.acao_em_auditoria = "APROVAR"
            await self.__auditar_documentacao_navio()
            # Limpa o IMO do set de lidos (navio aprovado sai da fila)
            self.imos_lidos.discard(imo)
        except Exception as err:
            self._page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao aprovar: {err}"), bgcolor=ft.Colors.RED
            )
            self._page.snack_bar.open = True
            self._page.update()

    def _abrir_modal_classificacao(self, err):
        self.erro_carga_pendente = err
        self.modal_classificacao.content = ft.Column(
            [
                ft.Text(
                    f"O navio {err.navio_nome} declarou uma carga desconhecida:",
                    size=14,
                    color="#0d1f35",
                ),
                ft.Container(
                    content=ft.Text(err.carga_descricao, italic=True, color="#334155"),
                    bgcolor="#f1f5f9",
                    padding=10,
                    border_radius=8,
                ),
                ft.Text(
                    "Qual o nível de perecibilidade desta carga?",
                    size=14,
                    color="#0d1f35",
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Column(
                    [
                        ft.Button(
                            "1. Ultra Perecível",
                            on_click=lambda e: self._page.run_task(
                                self._solicitar_classificacao_carga,
                                "URGENTE_PERECIVEL",
                                True,
                            ),
                            width=350,
                            style=ft.ButtonStyle(bgcolor="#fee2e2", color="#dc2626"),
                        ),
                        ft.Button(
                            "2. Alta Perecibilidade",
                            on_click=lambda e: self._page.run_task(
                                self._solicitar_classificacao_carga,
                                "ALTA_PERECIBILIDADE",
                                True,
                            ),
                            width=350,
                            style=ft.ButtonStyle(bgcolor="#ffedd5", color="#ea580c"),
                        ),
                        ft.Button(
                            "3. Baixa Perecibilidade",
                            on_click=lambda e: self._page.run_task(
                                self._solicitar_classificacao_carga,
                                "BAIXA_PERECIBILIDADE",
                                True,
                            ),
                            width=350,
                            style=ft.ButtonStyle(bgcolor="#fef3c7", color="#d97706"),
                        ),
                        ft.Button(
                            "4. Comum",
                            on_click=lambda e: self._page.run_task(
                                self._solicitar_classificacao_carga, "COMUM", False
                            ),
                            width=350,
                            style=ft.ButtonStyle(bgcolor="#f1f5f9", color="#64748b"),
                        ),
                    ],
                    spacing=8,
                ),
            ],
            tight=True,
            spacing=12,
        )

        self.modal_classificacao.open = True
        self._page.update()

    async def _solicitar_classificacao_carga(self, categoria, eh_perecivel):
        self.modal_classificacao.open = False
        self._page.update()

        if self.erro_carga_pendente:
            try:
                async with obter_sessao_async() as session:
                    await classificar_carga(
                        session,
                        self.erro_carga_pendente.carga_id,
                        categoria,
                        eh_perecivel,
                    )

                self._page.snack_bar = ft.SnackBar(
                    ft.Text(
                        f"Carga '{self.erro_carga_pendente.carga_descricao}' classificada com sucesso. Re-tentando auditoria..."
                    ),
                    bgcolor=ft.Colors.BLUE,
                )
                self._page.snack_bar.open = True
                self._page.update()

                # Re-tenta a ação original
                if getattr(self, "_is_batch_audit", False):
                    await self.auditar_todos_pendentes()
                else:
                    await self.__auditar_documentacao_navio()
            except Exception as err:
                self._page.snack_bar = ft.SnackBar(
                    ft.Text(f"Erro ao classificar carga: {err}"), bgcolor=ft.Colors.RED
                )
                self._page.snack_bar.open = True
                self._page.update()
            finally:
                self.erro_carga_pendente = None

    async def __auditar_documentacao_navio(self):
        """Executa a auditoria individual de um navio via sessão assíncrona."""
        self._is_batch_audit = False
        if self.dialogo_confirmacao.open:
            self.dialogo_confirmacao.open = False
            self._page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                navio_dto = await auditar_navio_individual(
                    session, self.imo_em_auditoria, self.acao_em_auditoria
                )
                if navio_dto.status == "VALIDADO":
                    msg = f"Navio {navio_dto.nome} APROVADO!"
                    status_cor = ft.Colors.GREEN
                else:
                    msg = f"Navio {navio_dto.nome} REJEITADO — documentação alfandegária incompleta."
                    status_cor = ft.Colors.ORANGE
        except CargaNaoClassificadaError as err:
            self._abrir_modal_classificacao(err)
            return  # Sai para aguardar a classificação do usuário
        except Exception as err:
            msg = f"Erro: {err}"

        self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
        self._page.snack_bar.open = True
        await self.atualizar()
        self._page.update()

    async def auditar_todos_pendentes(self):
        self._is_batch_audit = True
        # NOTA: Auditar todos também pode disparar CargaNaoClassificadaError.
        # Nesse caso, vamos capturar e avisar o usuário para classificar manualmente primeiro.
        try:
            async with obter_sessao_async() as session:
                auditos = await auditar_solicitacoes_pendentes(session)
                aprovados = sum(1 for n in auditos if n.status == "VALIDADO")
                rejeitados = sum(1 for n in auditos if n.status == "REJEITADO")

            msg = f"Auditoria concluída: {aprovados} aprovado(s), {rejeitados} rejeitado(s) por documentação."
            cor = ft.Colors.GREEN if rejeitados == 0 else ft.Colors.ORANGE
            self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cor)
            self._page.snack_bar.open = True
            await self.atualizar()
            self._page.update()
        except CargaNaoClassificadaError as err:
            self._abrir_modal_classificacao(err)
        except Exception as err:
            print(f"Erro na auditoria em lote: {err}")

    def _hover_btn(self, e):
        # Adiciona transição de cor
        if e.control.data == "aprovar":
            e.control.bgcolor = "#bbf7d0" if e.data == "true" else "#dcfce7"
        elif e.control.data == "rejeitar":
            e.control.bgcolor = "#fecaca" if e.data == "true" else "#fee2e2"
        e.control.update()

    def _criar_linha_navio(self, navio):
        capitao_nome = navio.nome_capitao
        carga_txt = (
            ", ".join(c.descricao for c in navio.cargas) if navio.cargas else "N/A"
        )
        docs_ok = (
            all(c.documento_alfandega for c in navio.cargas) if navio.cargas else False
        )

        docs_widget = ft.Row(
            [
                (
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="#16a34a", size=16)
                    if docs_ok
                    else ft.Icon(ft.Icons.CANCEL, color="#dc2626", size=16)
                ),
                ft.Text(
                    "Sim" if docs_ok else "Não",
                    color="#16a34a" if docs_ok else "#dc2626",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=4,
        )

        btn_aprovar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK, color="#16a34a", size=16),
                    ft.Text(
                        "Aprovar", color="#16a34a", size=12, weight=ft.FontWeight.BOLD
                    ),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#dcfce7",
            border=ft.border.all(1, "#86efac"),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            on_click=lambda e, imo=navio.imo_id, nome=navio.nome: self.abrir_confirmacao(
                imo, nome, "APROVAR"
            ),
            on_hover=self._hover_btn,
            data="aprovar",
            ink=True,
        )

        btn_rejeitar = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CLOSE, color="#dc2626", size=16),
                    ft.Text(
                        "Rejeitar", color="#dc2626", size=12, weight=ft.FontWeight.BOLD
                    ),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#fee2e2",
            border=ft.border.all(1, "#fca5a5"),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            on_click=lambda e, imo=navio.imo_id, nome=navio.nome: self.abrir_confirmacao(
                imo, nome, "REJEITAR"
            ),
            on_hover=self._hover_btn,
            data="rejeitar",
            ink=True,
        )

        tem_carga_outros = any(c.categoria == "OUTROS_PENDENTE" for c in navio.cargas)
        lido = navio.imo_id in self.imos_lidos

        if tem_carga_outros and not lido:
            btn_ler = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DESCRIPTION, color="#1e3a8a", size=16),
                        ft.Text(
                            "Ler Descrição",
                            color="#1e3a8a",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor="#dbeafe",
                border=ft.border.all(1, "#3b82f6"),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                on_click=lambda e, imo=navio.imo_id, nome=navio.nome, desc=carga_txt: self.abrir_leitura(
                    imo, nome, desc
                ),
                ink=True,
            )
            acoes_widget = ft.Row([btn_ler], spacing=8)
        elif tem_carga_outros and lido:
            btn_aprovar_outros = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK, color="#16a34a", size=16),
                        ft.Text(
                            "Aprovar",
                            color="#16a34a",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor="#dcfce7",
                border=ft.border.all(1, "#86efac"),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                on_click=lambda e, imo=navio.imo_id, nome=navio.nome: self.abrir_aprovacao_outros(
                    imo, nome
                ),
                on_hover=self._hover_btn,
                data="aprovar",
                ink=True,
            )
            acoes_widget = ft.Row([btn_aprovar_outros, btn_rejeitar], spacing=8)
        else:
            acoes_widget = ft.Row([btn_aprovar, btn_rejeitar], spacing=8)

        return ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(
                        navio.imo_id,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        size=12,
                        weight=ft.FontWeight.W_500,
                    )
                ),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            navio.nome,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                            color=ft.Colors.ON_SURFACE,
                            weight=ft.FontWeight.W_600,
                            size=13,
                        ),
                        width=150,
                        tooltip=navio.nome,
                    )
                ),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            capitao_nome,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            size=13,
                        ),
                        width=130,
                        tooltip=capitao_nome,
                    )
                ),
                ft.DataCell(
                    ft.Container(
                        content=ft.Text(
                            carga_txt,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                            color=ft.Colors.ON_SURFACE,
                            size=12,
                        ),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=12,
                        tooltip=carga_txt,
                    )
                ),
                ft.DataCell(docs_widget),
                ft.DataCell(acoes_widget),
            ]
        )

    def pagina_anterior(self, e):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
            self._page.run_task(self.atualizar)

    def proxima_pagina(self, e):
        if self.pagina_atual < self.total_paginas:
            self.pagina_atual += 1
            self._page.run_task(self.atualizar)

    def alterar_limite(self, e):
        limite_val = self.dropdown_limite.value
        if limite_val == "todos":
            self.itens_por_pagina = 1000000
        else:
            self.itens_por_pagina = int(limite_val)
        self.pagina_atual = 1
        self._page.run_task(self.atualizar)

    async def carregar_solicitacoes_pendentes(self, session):
        navios = await obter_solicitacoes_pendentes_dto(session)
        total_itens = len(navios)
        limite = self.itens_por_pagina
        self.total_paginas = max(1, (total_itens + limite - 1) // limite)

        if self.pagina_atual > self.total_paginas:
            self.pagina_atual = self.total_paginas

        inicio = (self.pagina_atual - 1) * limite
        fim = min(inicio + limite, total_itens)
        navios_pagina = navios[inicio:fim]

        novas_linhas = [self._criar_linha_navio(navio) for navio in navios_pagina]
        self.tabela_pendentes.rows = novas_linhas
        self.txt_vazio_auditoria.visible = len(novas_linhas) == 0
        self.tabela_pendentes.visible = len(novas_linhas) > 0

        # Atualizar controles de paginação
        self.txt_pagina.value = f"Página {self.pagina_atual} de {self.total_paginas}"
        self.btn_anterior.disabled = self.pagina_atual <= 1
        self.btn_proximo.disabled = self.pagina_atual >= self.total_paginas

        if total_itens == 0:
            self.txt_paginas_info.value = "Exibindo 0 de 0 itens"
            self.row_paginacao.visible = False
        else:
            limite_texto = "Todos" if limite >= 1000000 else f"{inicio + 1}-{fim}"
            self.txt_paginas_info.value = (
                f"Exibindo {limite_texto} de {total_itens} itens"
            )
            self.row_paginacao.visible = True

    async def atualizar(self, e=None):
        try:
            async with obter_sessao_async() as session:
                await self.carregar_solicitacoes_pendentes(session)
                self.update()
        except Exception as err:
            print(f"Erro ao carregar auditorias pendentes: {err}")

    async def auto_refresh_loop(self):
        while self._active:
            await asyncio.sleep(3)
            try:
                if not self._active:
                    break
                if getattr(self._page, "active_tab", None) == "auditoria":
                    await self.atualizar()
            except Exception:
                pass


def obter_view(page: ft.Page):
    return AuditoriaView(page)
