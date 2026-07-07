import flet as ft
import os
import sys
import re
import asyncio

from datetime import datetime, timedelta
from cad import obter_sessao_async, StatusVaga, StatusNavio, Vaga, Navio, Atracacao
from controller_cadastros import (
    solicitar_pre_cadastro,
    auditar_solicitacoes_pendentes,
    excluir_registro_navio,
    editar_registro_navio,
)
from controller_operacao import (
    atracar_navio,
    registrar_desatracacao,
    obter_painel_vagas_dto,
    obter_log_operacoes_dto,
)
from ord_propriety import obter_fila_atracacao_dto


def _validar_texto_comum(valor: str, msg_obrigatorio: str) -> str:
    valor = valor.strip()
    if not valor:
        return msg_obrigatorio
    if not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", valor):
        return "Contém caracteres inválidos."
    return ""

def _validar_peso(peso: str) -> str:
    peso = peso.strip()
    if not peso:
        return "O peso é obrigatório."
    try:
        if int(peso) <= 0:
            return "O peso deve ser maior que zero."
    except ValueError:
        return "Insira um número inteiro válido."
    return ""

def validar_formulario_navio(
    imo: str, nome: str, capitao: str, companhia: str, peso: str, categoria: str
) -> dict[str, str]:
    erros: dict[str, str] = {}
    
    imo = imo.strip()
    if not imo:
        erros["imo"] = "O IMO é obrigatório."
    elif not imo.isdigit() or len(imo) != 7:
        erros["imo"] = "O IMO deve conter exatamente 7 números."

    if erro_nome := _validar_texto_comum(nome, "O nome do navio é obrigatório."):
        erros["nome"] = erro_nome

    if erro_capitao := _validar_texto_comum(capitao, "O nome do capitão é obrigatório."):
        erros["capitao"] = erro_capitao

    if erro_companhia := _validar_texto_comum(companhia, "A companhia é obrigatória."):
        erros["companhia"] = erro_companhia

    if erro_peso := _validar_peso(peso):
        erros["peso"] = erro_peso

    if not categoria:
        erros["categoria"] = "Selecione uma categoria de carga."
        
    return erros


class PainelAdmView:
    def __init__(self, page: ft.Page, aba_ativa="dashboard"):
        self.page = page
        self.aba_ativa = aba_ativa

        self.txt_vagas = ft.Text("...", size=30, weight=ft.FontWeight.BOLD)
        self.txt_fila = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_pendentes = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_concluidos = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_taxa = ft.Text("0.0", size=30, weight=ft.FontWeight.BOLD)

        self.loading_indicator = ft.ProgressRing(visible=False)

        self.tabela_vagas = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID Vaga")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Navio Atracado")),
                ft.DataColumn(ft.Text("Tempo de atracação")),
                ft.DataColumn(ft.Text("Ações")),
            ],
            rows=[],
        )

        self.tabela_navios = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID Navio")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Capitão")),
                ft.DataColumn(ft.Text("Companhia")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Ações")),
            ],
            rows=[],
        )

        self.tabela_pendentes = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID Navio")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Capitão")),
                ft.DataColumn(ft.Text("Carga")),
                ft.DataColumn(ft.Text("Documentos")),
                ft.DataColumn(ft.Text("Ações")),
            ],
            rows=[],
        )

        self.txt_vazio_auditoria = ft.Text(
            "Nenhuma solicitação pendente no momento.", size=12, italic=True, visible=False
        )

        self.imo_em_auditoria = None
        self.acao_em_auditoria = None

        self.txt_mensagem_modal = ft.Text("")

        self.dialogo_confirmacao = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Auditoria"),
            content=self.txt_mensagem_modal,
            actions=[
                ft.TextButton("Confirmar", on_click=lambda e: self.page.run_task(self.processar_auditoria)),
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
            ],
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
                    "Confirmar atracação", on_click=lambda e: self.page.run_task(self.processar_atracacao_backend)
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
                    "Confirmar Saída", on_click=lambda e: self.page.run_task(self.processar_desatracacao_backend)
                ),
                ft.TextButton("Cancelar", on_click=self.fechar_modal_desatracacao),
            ],
        )

        self.imo_para_excluir = None
        self.txt_msg_exclusao = ft.Text("")

        self.dialogo_confirmar_exclusao = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Exclusão de Registro"),
            content=self.txt_msg_exclusao,
            actions=[
                ft.TextButton(
                    "Confirmar Exclusão", on_click=lambda e: self.page.run_task(self.processar_exclusao_backend)
                ),
                ft.TextButton("Cancelar", on_click=self.fechar_modal_exclusao),
            ],
        )

        self.grafico_row = ft.Row(
            [],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            vertical_alignment=ft.CrossAxisAlignment.END,
            expand=True,
        )

        self.container_grafico = ft.Container(
            content=self.grafico_row,
            height=220,
            padding=20,
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_500),
        )

        self.coluna_logs = ft.Column(spacing=5)
        self.caixa_logs = self.criar_caixa("Últimas Operações", ft.Icons.HISTORY, [self.coluna_logs])

        self.coluna_proximos = ft.Column(spacing=5)
        self.caixa_proximos = self.criar_caixa(
            "Próximos na Fila", ft.Icons.FORMAT_LIST_NUMBERED, [self.coluna_proximos]
        )

        self.coluna_vagas = ft.Column(spacing=5)
        self.caixa_vagas = self.criar_caixa("Monitor de Berços", ft.Icons.ANCHOR, [self.coluna_vagas])

        self.navio_selecionado = None
        self.edit_nome = ft.TextField(label="Nome do Navio", width=300)
        self.edit_capitao = ft.TextField(label="Nome do Capitão", width=300)
        self.edit_companhia = ft.TextField(label="Companhia", width=300)
        self.btn_salvar_edicao = ft.ElevatedButton(
            "Salvar Alterações",
            icon=ft.Icons.SAVE,
            on_click=lambda e: self.page.run_task(self.submit_edicao_navio),
        )

        self.secao_formulario_edicao = ft.Container(
            visible=False,
            padding=20,
            border=ft.Border.all(1, ft.Colors.BLUE),
            border_radius=10,
            content=ft.Column(
                [
                    ft.Text(
                        "Editar Dados da Embarcação", size=20, weight=ft.FontWeight.BOLD
                    ),
                    ft.Row([self.edit_nome, self.edit_capitao, self.edit_companhia]),
                    ft.Row(
                        [
                            self.btn_salvar_edicao,
                            ft.TextButton("Cancelar", on_click=lambda e: self.fechar_edicao()),
                        ]
                    ),
                ]
            ),
        )

        self.campo_imo = ft.TextField(
            label="Número IMO (ex: 1234567)",
            max_length=7,
            prefix_icon=ft.Icons.NUMBERS,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        self.campo_nome = ft.TextField(
            label="Nome do Navio", 
            prefix_icon=ft.Icons.DIRECTIONS_BOAT
        )
        self.campo_capitao = ft.TextField(
            label="Nome do Capitão", 
            prefix_icon=ft.Icons.PERSON
        )
        self.campo_companhia = ft.TextField(
            label="Companhia", 
            prefix_icon=ft.Icons.BUSINESS
        )
        self.campo_peso = ft.TextField(
            label="Peso Total (Toneladas)",
            prefix_icon=ft.Icons.SCALE,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        self.campo_categoria = ft.Dropdown(
            label="Categoria da Carga",
            leading_icon=ft.Icons.CATEGORY,
            options=[
                ft.dropdown.Option(
                    key="URGENTE_PERECIVEL", text="Medicamentos / Carnes (Perecível)"
                ),
                ft.dropdown.Option(
                    key="ALTA_PERECIBILIDADE", text="Frutas / Laticínios (Perecível)"
                ),
                ft.dropdown.Option(key="BAIXA_PERECIBILIDADE", text="Grãos Úmidos"),
                ft.dropdown.Option(
                    key="COMUM", text="Carga Geral / Minérios / Contêineres"
                ),
            ],
        )
        self.campo_docs = ft.Switch(label="Possui Documentos Alfandegários?", value=False)

        self.campo_limite_navios = ft.Dropdown(
            label="Limite de Exibição",
            value="100",
            options=[
                ft.dropdown.Option(key="25", text="25 Navios"),
                ft.dropdown.Option(key="50", text="50 Navios"),
                ft.dropdown.Option(key="100", text="100 Navios"),
                ft.dropdown.Option(key="TODOS", text="Todos os Navios"),
            ],
            width=200,
        )
        self.campo_limite_navios.on_change = lambda e: self.page.run_task(self.carregar_dados)

        self.page.overlay.append(self.dialogo_confirmacao)
        self.page.overlay.append(self.dialogo_confirmar_atracacao)
        self.page.overlay.append(self.dialogo_confirmar_desatracacao)
        self.page.overlay.append(self.dialogo_confirmar_exclusao)

        self.setup_tabs()

    def setup_tabs(self):
        self.aba_dashboard_container = ft.Container(
            padding=30,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.PIE_CHART,
                                        size=32,
                                        color=ft.Colors.BLUE_GREY_800,
                                    ),
                                    ft.Text(
                                        "Métricas em Tempo Real",
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                tooltip="Atualizar",
                                on_click=lambda e: self.page.run_task(self.carregar_dados),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    # APLICADO EXPAND=1 DENTRO DO CREATE_STAT_CARD - Sempre lado a lado com espaços respeitados
                    ft.Row(
                        [
                            self.create_stat_card("Vagas Livres / Total", self.txt_vagas, ft.Icons.ANCHOR, ft.Colors.BLUE),
                            self.create_stat_card("Navios na Fila", self.txt_fila, ft.Icons.FORMAT_LIST_NUMBERED, ft.Colors.ORANGE),
                            self.create_stat_card("Auditorias Pendentes", self.txt_pendentes, ft.Icons.HOURGLASS_BOTTOM, ft.Colors.RED),
                            self.create_stat_card("Operações Concluídas", self.txt_concluidos, ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
                            self.create_stat_card("Taxa de Atracação/Dia", self.txt_taxa, ft.Icons.SPEED, ft.Colors.PURPLE),
                        ],
                        spacing=15,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        "Atracações Diárias (Última Semana)",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                    self.container_grafico,
                    ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                    # APLICADO FIXED HEIGHT NAS CAIXAS E RETIRADO O STRETCH BUGADO
                    ft.Row(
                        [self.caixa_logs, self.caixa_proximos, self.caixa_vagas],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        spacing=15,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

        self.aba_vagas_container = ft.Container(
            padding=30,
            visible=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.VIEW_AGENDA,
                                        size=32,
                                        color=ft.Colors.BLUE_GREY_800,
                                    ),
                                    ft.Text(
                                        "Painel de Controle de Vagas",
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                tooltip="Atualizar",
                                on_click=lambda e: self.page.run_task(self.carregar_dados),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Atracar Próximo",
                                icon=ft.Icons.LOGIN,
                                on_click=lambda e: self.abrir_confirmacao_atracacao("PROXIMO"),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.GREEN_700,
                                    color=ft.Colors.WHITE,
                                    padding=15,
                                ),
                            ),
                            ft.ElevatedButton(
                                "Atracar em Lote",
                                icon=ft.Icons.PLAYLIST_ADD_CHECK,
                                on_click=lambda e: self.abrir_confirmacao_atracacao("LOTE"),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.BLUE_700,
                                    color=ft.Colors.WHITE,
                                    padding=15,
                                ),
                            ),
                            ft.ElevatedButton(
                                "Liberar Todos os Berços",
                                icon=ft.Icons.LOGOUT,
                                on_click=lambda e: self.abrir_confirmacao_desatracacao("MASSA"),
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.RED_700,
                                    color=ft.Colors.WHITE,
                                    padding=15,
                                ),
                            ),
                            self.loading_atracacao,
                            self.loading_desatracacao,
                        ],
                        spacing=10,
                    ),
                    ft.Divider(),
                    ft.ListView(controls=[self.tabela_vagas], expand=True, spacing=10),
                ],
                expand=True,
            ),
        )

        self.aba_gerenciar_container = ft.Container(
            padding=30,
            visible=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.DIRECTIONS_BOAT_FILLED,
                                size=32,
                                color=ft.Colors.BLUE_GREY_800,
                            ),
                            ft.Text(
                                "Registrar Nova Entrada de Navio",
                                size=26,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_imo]),
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_nome]),
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_capitao]),
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_companhia]),
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_categoria]),
                            ft.Column(col={"sm": 12, "md": 6}, controls=[self.campo_peso]),
                        ],
                        run_spacing=15,
                    ),
                    self.campo_docs,
                    ft.ElevatedButton(
                        "Salvar Solicitação",
                        icon=ft.Icons.SAVE,
                        on_click=lambda e: self.page.run_task(self.salvar_navio),
                        style=ft.ButtonStyle(padding=15),
                    ),
                    ft.Divider(height=20, color=ft.Colors.GREY_300),
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.SETTINGS, size=24, color=ft.Colors.BLUE_GREY_800
                                    ),
                                    ft.Text(
                                        "Gerenciar Embarcações Cadastradas",
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=8,
                            ),
                            self.campo_limite_navios
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    self.secao_formulario_edicao,
                    ft.ListView(
                        controls=[self.tabela_navios], expand=True, spacing=10, height=400
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

        self.aba_auditoria_container = ft.Container(
            padding=30,
            visible=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.FACT_CHECK,
                                        size=32,
                                        color=ft.Colors.BLUE_GREY_800,
                                    ),
                                    ft.Text(
                                        "Auditoria de Solicitações Pendentes",
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.ElevatedButton(
                                "Auditar Todos Automaticamente",
                                icon=ft.Icons.FACT_CHECK,
                                on_click=lambda e: self.page.run_task(self.auditar_todos_pendentes),
                                tooltip="Aprova navios com documentação completa e rejeita os demais",
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.BLUE_700,
                                    color=ft.Colors.WHITE,
                                    padding=15,
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(),
                    self.txt_vazio_auditoria,
                    ft.ListView(controls=[self.tabela_pendentes], expand=True, spacing=10),
                ]
            ),
            expand=True,
        )

    async def carregar_solicitacoes_pendentes(self, e=None):
        try:
            from controller_cadastros import obter_solicitacoes_pendentes_dto
            async with obter_sessao_async() as session:
                pendentes = await obter_solicitacoes_pendentes_dto(session)
                novas_linhas = []
                for navio in pendentes:
                    capitao_nome = navio.nome_capitao
                    carga_txt = (
                        ", ".join(c.descricao for c in navio.cargas)
                        if navio.cargas
                        else "N/A"
                    )
                    docs_ok = (
                        all(c.documento_alfandega for c in navio.cargas)
                        if navio.cargas
                        else False
                    )
                    docs_txt = "✅ Completa" if docs_ok else "❌ Pendente"

                    btn_aprovar = ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE,
                        icon_color=ft.Colors.GREEN,
                        on_click=lambda e, imo=navio.imo_id: self.abrir_confirmacao(imo, "APROVAR"),
                    )
                    btn_rejeitar = ft.IconButton(
                        icon=ft.Icons.CANCEL,
                        icon_color=ft.Colors.RED,
                        on_click=lambda e, imo=navio.imo_id: self.abrir_confirmacao(imo, "REJEITAR"),
                    )
                    novas_linhas.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(navio.imo_id)),
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Text(navio.nome, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                        width=150,
                                        tooltip=navio.nome
                                    )
                                ),
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Text(capitao_nome, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                        width=130,
                                        tooltip=capitao_nome
                                    )
                                ),
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Text(carga_txt, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                        width=250,
                                        tooltip=carga_txt
                                    )
                                ),
                                ft.DataCell(ft.Text(docs_txt, no_wrap=True)),
                                ft.DataCell(
                                    ft.Row([btn_aprovar, btn_rejeitar], spacing=5)
                                ),
                            ]
                        )
                    )
                self.tabela_pendentes.rows = novas_linhas
                self.txt_vazio_auditoria.visible = len(novas_linhas) == 0
                self.tabela_pendentes.visible = len(novas_linhas) > 0
                self.page.update()
        except Exception as err:
            print(f"Erro na auditoria: {err}")

    async def processar_auditoria(self):
        self.dialogo_confirmacao.open = False
        self.page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            from controller_cadastros import auditar_navio_individual
            async with obter_sessao_async() as session:
                navio_dto = await auditar_navio_individual(session, self.imo_em_auditoria, self.acao_em_auditoria)
                if navio_dto.status == "VALIDADO":
                    msg = f"Navio {navio_dto.nome} APROVADO!"
                    status_cor = ft.Colors.GREEN
                else:
                    msg = f"Navio {navio_dto.nome} REJEITADO — documentação alfandegária incompleta."
                    status_cor = ft.Colors.ORANGE
        except Exception as err:
            msg = f"Erro: {err}"
        finally:
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self.page.snack_bar.open = True
            await self.carregar_solicitacoes_pendentes()
            await self.carregar_dados()
            self.page.update()

    async def auditar_todos_pendentes(self):
        try:
            from controller_cadastros import auditar_solicitacoes_pendentes
            async with obter_sessao_async() as session:
                auditos = await auditar_solicitacoes_pendentes(session)
                aprovados = sum(1 for n in auditos if n.status == "VALIDADO")
                rejeitados = sum(1 for n in auditos if n.status == "REJEITADO")

            msg = f"Auditoria concluída: {aprovados} aprovado(s), {rejeitados} rejeitado(s) por documentação."
            cor = ft.Colors.GREEN if rejeitados == 0 else ft.Colors.ORANGE
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cor)
            self.page.snack_bar.open = True
            await self.carregar_solicitacoes_pendentes()
            await self.carregar_dados()
            self.page.update()
        except Exception as err:
            print(f"Erro na auditoria em lote: {err}")

    def fechar_modal(self, e=None):
        self.dialogo_confirmacao.open = False
        self.page.update()

    def abrir_confirmacao(self, imo, acao):
        self.imo_em_auditoria = imo
        self.acao_em_auditoria = acao
        self.txt_mensagem_modal.value = f"Deseja {acao.lower()} a solicitação do navio {imo}?"
        self.dialogo_confirmacao.open = True
        self.page.update()

    async def processar_atracacao_backend(self):
        self.dialogo_confirmar_atracacao.open = False
        self.loading_atracacao.visible = True
        self.page.update()

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
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self.page.snack_bar.open = True
            await self.carregar_dados()
            self.page.update()

    def fechar_modal_atracacao(self, e=None):
        self.dialogo_confirmar_atracacao.open = False
        self.page.update()

    def abrir_confirmacao_atracacao(self, tipo):
        self.tipo_atracacao = tipo
        if tipo == "PROXIMO":
            self.txt_msg_atracacao.value = "Deseja atracar o proximo navio?"
        else:
            self.txt_msg_atracacao.value = "Deseja iniciar a atracação em lote de todas as vagas livres?"
        self.dialogo_confirmar_atracacao.open = True
        self.page.update()

    async def processar_desatracacao_backend(self):
        self.dialogo_confirmar_desatracacao.open = False
        self.loading_desatracacao.visible = True
        self.page.update()

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
                    sucesso_count = 0
                    for vaga in vagas:
                        if vaga.status == "OCUPADA" and vaga.navio_atracado:
                            await registrar_desatracacao(session, vaga.navio_atracado.imo_id)
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
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self.page.snack_bar.open = True
            await self.carregar_dados()
            self.page.update()

    def fechar_modal_desatracacao(self, e=None):
        self.dialogo_confirmar_desatracacao.open = False
        self.page.update()

    def abrir_confirmacao_desatracacao(self, tipo, imo=None):
        self.tipo_desatracacao = tipo
        self.imo_desatracacao = imo

        if tipo == "INDIVIDUAL":
            self.txt_msg_desatracacao.value = f"Deseja destracar navio {imo} e liberar este berço?"
        else:
            self.txt_msg_desatracacao.value = "ATENÇÃO: Deseja realmente desatracar TODOS os navios ativos de todos os berços ao mesmo tempo?"

        self.dialogo_confirmar_desatracacao.open = True
        self.page.update()

    async def processar_exclusao_backend(self):
        self.dialogo_confirmar_exclusao.open = False
        self.page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                await excluir_registro_navio(session, self.imo_para_excluir)
                msg = f"Sucesso: Registro do navio ({self.imo_para_excluir}) foi excluído definitivamente."
                status_cor = ft.Colors.GREEN
        except Exception as err:
            msg = f"{err}"
            status_cor = ft.Colors.ORANGE
        finally:
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self.page.snack_bar.open = True
            await self.carregar_dados()
            self.page.update()

    def fechar_modal_exclusao(self, e=None):
        self.dialogo_confirmar_exclusao.open = False
        self.page.update()

    def abrir_confirmacao_exclusao(self, imo):
        self.imo_para_excluir = imo
        self.txt_msg_exclusao.value = f"Tem certeza que deseja excluir permanentemente o navio {imo}?"
        self.dialogo_confirmar_exclusao.open = True
        self.page.update()

    def criar_caixa(self, titulo, icone, controles_lista):
        return ft.Container(
            expand=1,
            height=340,          # diminuit a autura do cards inferiores, achei muito grand
            padding=15,
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_500),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icone, color=ft.Colors.BLUE_700, size=20),
                            ft.Text(titulo, weight=ft.FontWeight.BOLD, size=14),
                        ],
                        spacing=5,
                    ),
                    ft.Divider(height=10),
                    *controles_lista,
                ],
                spacing=5,
                # analizar, chatão isso ai
                scroll=ft.ScrollMode.AUTO, # permite scroll nas caixas que precisarem 
            ),
        )

    def fechar_edicao(self):
        self.secao_formulario_edicao.visible = False
        self.edit_nome.value = self.edit_capitao.value = self.edit_companhia.value = ""
        self.page.update()

    def abrir_edicao_navio(self, navio):
        self.navio_selecionado = navio
        self.edit_nome.value = navio.nome
        self.edit_capitao.value = (
            navio.nome_capitao
            if hasattr(navio, "nome_capitao")
            else getattr(navio, "capitao", "")
        )
        self.edit_companhia.value = navio.companhia
        self.secao_formulario_edicao.visible = True
        self.page.update()

    async def submit_edicao_navio(self):
        if not self.edit_nome.value or not self.edit_capitao.value or not self.edit_companhia.value:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Preencha todos os campos obrigatórios!"), bgcolor=ft.Colors.RED
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.btn_salvar_edicao.disabled = True
        self.loading_indicator.visible = True
        self.page.update()

        msg = ""
        status = ft.Colors.RED
        try:
            from controller_cadastros import editar_registro_navio
            async with obter_sessao_async() as session:
                await editar_registro_navio(
                    session,
                    self.navio_selecionado.imo_id,
                    self.edit_nome.value,
                    self.edit_capitao.value,
                    self.edit_companhia.value
                )
                msg = f"Navio {self.edit_nome.value} atualizado com sucesso!"
                status = ft.Colors.GREEN
        except Exception as e:
            msg = f"Erro ao atualizar navio: {e}"
        finally:
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status)
            self.page.snack_bar.open = True
            self.btn_salvar_edicao.disabled = False
            self.loading_indicator.visible = False
            self.secao_formulario_edicao.visible = False
            await self.carregar_dados()
            self.page.update()

    async def liberar_vaga(self, vaga_id):
        try:
            from controller_operacao import liberar_vaga_individual
            async with obter_sessao_async() as session:
                await liberar_vaga_individual(session, vaga_id)
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"Vaga {vaga_id} liberada!"), bgcolor=ft.Colors.GREEN
                )
                self.page.snack_bar.open = True
                await self.carregar_dados()
        except Exception as e:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao liberar vaga: {e}"), bgcolor=ft.Colors.RED
            )
            self.page.snack_bar.open = True
        self.page.update()

    async def _atualizar_cards(self, session):
        from controller_operacao import obter_contadores_dashboard
        counts = await obter_contadores_dashboard(session)
        self.txt_vagas.value = f"{counts['vagas_livres']} / {counts['total_vagas']}"
        self.txt_fila.value = str(counts['total_validado'])
        self.txt_pendentes.value = str(counts['total_pendente'])
        self.txt_concluidos.value = str(counts['total_finalizado'])

    async def _atualizar_caixa_proximos(self, session):
        from ord_propriety import obter_fila_atracacao_dto
        fila = await obter_fila_atracacao_dto(session)
        proximos = fila[:5]

        novos_proximos = []
        if not proximos:
            novos_proximos.append(
                ft.Text("A fila está vazia no momento.", size=12, italic=True)
            )
        else:
            for idx, p in enumerate(proximos):
                novos_proximos.append(
                    ft.Text(
                        f"{idx+1}º - {p.nome}",
                        size=12,
                        weight=ft.FontWeight.W_500,
                    )
                )
        self.coluna_proximos.controls = novos_proximos

    async def _atualizar_caixa_vagas(self, session):
        from controller_operacao import obter_painel_vagas_dto
        vagas = await obter_painel_vagas_dto(session)
        novas_vagas = []
        for v in vagas:
            if v.status == "LIVRE":
                novas_vagas.append(
                    ft.Text(
                        f"🟢 Berço {v.id}: Livre",
                        size=12,
                        color=ft.Colors.GREEN_700,
                        weight=ft.FontWeight.BOLD,
                    )
                )
            else:
                novas_vagas.append(
                    ft.Text(
                        f"🔴 Berço {v.id}: Ocupado",
                        size=12,
                        color=ft.Colors.RED_700,
                    )
                )
        self.coluna_vagas.controls = novas_vagas

    async def _atualizar_grafico(self, session):
        from controller_operacao import obter_contagem_atracacoes_dia
        hoje_date = datetime.now().date()
        contagem_por_dia = await obter_contagem_atracacoes_dia(session, 7)

        total_semana = sum(contagem_por_dia.values())
        taxa_diaria = total_semana / 7.0
        self.txt_taxa.value = f"{taxa_diaria:.1f}"

        pico = max(contagem_por_dia.values(), default=1) or 1
        altura_max = 120
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
                            str(valor_dia), size=13, weight=ft.FontWeight.BOLD
                        ),
                        ft.Container(
                            width=35,
                            height=altura_barra,
                            bgcolor=ft.Colors.BLUE_500,
                            border_radius=5,
                            tooltip=f"{valor_dia} atracações em {dia_label}",
                        ),
                        ft.Text(dia_label, size=11),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        self.grafico_row.controls = novo_grafico

    async def _atualizar_logs(self, session):
        from controller_operacao import obter_log_operacoes_dto
        eventos_log = (await obter_log_operacoes_dto(session))[:5]
        novos_logs = []
        if not eventos_log:
            novos_logs.append(
                ft.Text("Nenhuma operação registrada.", size=12, italic=True)
            )
        else:
            for ev in eventos_log:
                hora_ev = ev.data_hora.strftime("%d/%m %H:%M")
                if ev.tipo == "DESATRACAO":
                    novos_logs.append(
                        ft.Text(
                            f"⬅️ Saída: {ev.navio_nome} (Berço {ev.vaga_id}) — {hora_ev}",
                            size=12,
                        )
                    )
                else:
                    novos_logs.append(
                        ft.Text(
                            f"➡️ Entrada: {ev.navio_nome} (Berço {ev.vaga_id}) — {hora_ev}",
                            size=12,
                        )
                    )
        self.coluna_logs.controls = novos_logs

    async def _atualizar_tabelas_secundarias(self, session):
        from controller_operacao import obter_painel_vagas_dto
        from controller_cadastros import obter_todos_navios_dto
        
        vagas = await obter_painel_vagas_dto(session)
        novas_linhas_vagas = []
        for vaga in vagas:
            if vaga.status == "OCUPADA":
                navio_atracado = vaga.navio_atracado
                navio_nome = navio_atracado.nome if navio_atracado else "Desconhecido"
                minutos = int(
                    (
                        datetime.now() - vaga.data_hora_inicio
                    ).total_seconds()
                    / 60
                )
                tempo_txt = (
                    f"{minutos} min"
                    if minutos < 60
                    else f"{minutos // 60}h {minutos % 60}min"
                )
                imo_btn = navio_atracado.imo_id if navio_atracado else None
            else:
                navio_nome = "—"
                tempo_txt = "—"
                imo_btn = None

            status_cor = (
                ft.Colors.GREEN
                if vaga.status == "LIVRE"
                else ft.Colors.RED
            )
            btn_liberar = ft.IconButton(
                icon=ft.Icons.NO_CRASH,
                icon_color=ft.Colors.RED,
                tooltip="Desatracar navio",
                disabled=(vaga.status == "LIVRE"),
                on_click=lambda e, imo=imo_btn: (
                    self.abrir_confirmacao_desatracacao("INDIVIDUAL", imo)
                    if imo
                    else None
                ),
            )
            novas_linhas_vagas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"Berço {vaga.id}")),
                        ft.DataCell(
                            ft.Text(
                                vaga.status,
                                color=status_cor,
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(navio_nome, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                width=180,
                                tooltip=navio_nome
                            )
                        ),
                        ft.DataCell(ft.Text(tempo_txt, no_wrap=True)),
                        ft.DataCell(btn_liberar),
                    ]
                )
            )
        self.tabela_vagas.rows = novas_linhas_vagas

        navios = await obter_todos_navios_dto(session)
        navios.sort(key=lambda x: x.data_solicitacao, reverse=True)
        
        if self.campo_limite_navios.value != "TODOS":
            try:
                limite = int(self.campo_limite_navios.value)
                navios = navios[:limite]
            except ValueError:
                navios = navios[:100]

        novas_linhas_navios = []
        for navio in navios:
            capitao_nome = navio.nome_capitao
            btn_editar = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=ft.Colors.BLUE,
                on_click=lambda e, n=navio: self.abrir_edicao_navio(n),
            )
            btn_excluir = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                on_click=lambda e, imo=navio.imo_id: self.abrir_confirmacao_exclusao(imo),
            )
            novas_linhas_navios.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(navio.imo_id)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(navio.nome, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                width=150,
                                tooltip=navio.nome
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(capitao_nome, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                width=130,
                                tooltip=capitao_nome
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(navio.companhia, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                width=130,
                                tooltip=navio.companhia
                            )
                        ),
                        ft.DataCell(ft.Text(navio.status, no_wrap=True)),
                        ft.DataCell(
                            ft.Row([btn_editar, btn_excluir], spacing=5)
                        ),
                    ]
                )
            )
        self.tabela_navios.rows = novas_linhas_navios

    async def carregar_dados(self, e=None):
        try:
            async with obter_sessao_async() as session:
                await self._atualizar_cards(session)
                await self._atualizar_caixa_proximos(session)
                await self._atualizar_caixa_vagas(session)
                await self._atualizar_grafico(session)
                await self._atualizar_logs(session)
                await self._atualizar_tabelas_secundarias(session)
                
                self.page.update()
        except Exception as erro:
            import traceback
            traceback.print_exc()
            print(f"Erro ao carregar dados: {erro}")

    def create_stat_card(self, title, text_control, icon, icon_color):
        return ft.Card(
            elevation=4,
            expand=1,        # força o Card a preencher proporcionalmente o espaço horizontal
            content=ft.Container(
                padding=15,
                border_radius=10,
                content=ft.Column(
                    [
                        ft.Icon(icon, size=36, color=icon_color),
                        text_control,
                        ft.Text(
                            title,
                            size=13,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    async def salvar_navio(self, e=None):
        erros = validar_formulario_navio(
            imo=self.campo_imo.value or "",
            nome=self.campo_nome.value or "",
            capitao=self.campo_capitao.value or "",
            companhia=self.campo_companhia.value or "",
            peso=self.campo_peso.value or "",
            categoria=self.campo_categoria.value or "",
        )
        self.campo_imo.error_text = erros.get("imo")
        self.campo_nome.error_text = erros.get("nome")
        self.campo_capitao.error_text = erros.get("capitao")
        self.campo_companhia.error_text = erros.get("companhia")
        self.campo_peso.error_text = erros.get("peso")
        self.campo_categoria.error_text = erros.get("categoria")

        if erros:
            self.page.update()
            return

        imo_formatado = f"IMO{self.campo_imo.value.strip()}"
        peso = int(self.campo_peso.value.strip())

        try:
            eh_perecivel = self.campo_categoria.value in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
            ]
            async with obter_sessao_async() as session:
                await solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=self.campo_nome.value.strip(),
                    capitao=self.campo_capitao.value.strip(),
                    companhia=self.campo_companhia.value.strip(),
                    carga_desc=f"Carga: {self.campo_categoria.value}",
                    categoria=self.campo_categoria.value,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=self.campo_docs.value,
                )
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Sucesso! Navio {self.campo_nome.value.strip()} registrado!"),
                bgcolor=ft.Colors.GREEN,
            )
            self.page.snack_bar.open = True

            self.campo_imo.value = self.campo_nome.value = self.campo_capitao.value = (
                self.campo_companhia.value
            ) = self.campo_peso.value = ""
            self.campo_categoria.value = None
            self.campo_docs.value = False
            await self.carregar_dados()
        except Exception as erro:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao salvar: {erro}"), bgcolor=ft.Colors.RED
            )
            self.page.snack_bar.open = True
        self.page.update()

    async def auto_refresh_loop(self):
        while True:
            await asyncio.sleep(2)
            try:
                if getattr(self.page, "active_tab", None) != self.aba_ativa:
                    break
            except Exception:
                break
            try:
                await self.carregar_dados()
                if self.aba_ativa == "auditoria":
                    await self.carregar_solicitacoes_pendentes()
            except Exception:
                pass

    def build(self):
        self.page.run_task(self.carregar_dados)
        if self.aba_ativa == "auditoria":
            self.page.run_task(self.carregar_solicitacoes_pendentes)

        self.aba_retornada = self.aba_dashboard_container
        if self.aba_ativa == "dashboard":
            self.aba_retornada = self.aba_dashboard_container
        elif self.aba_ativa == "gerenciar":
            self.aba_retornada = self.aba_gerenciar_container
        elif self.aba_ativa == "vagas":
            self.aba_retornada = self.aba_vagas_container
        elif self.aba_ativa == "auditoria":
            self.aba_retornada = self.aba_auditoria_container

        self.page.run_task(self.auto_refresh_loop)

        return self.aba_retornada

def obter_view(page: ft.Page, aba_ativa="dashboard"):
    view = PainelAdmView(page, aba_ativa)
    return view.build()