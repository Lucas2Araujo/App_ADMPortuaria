import flet as ft
import os
import sys
import re

from datetime import datetime, timedelta
from threading import Thread
from cad import obter_sessao, StatusVaga, StatusNavio, Vaga, Navio, Atracacao
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



def validar_formulario_navio(
    imo: str, nome: str, capitao: str, companhia: str, peso: str, categoria: str
) -> dict[str, str]:
    erros: dict[str, str] = {}
    imo = imo.strip()
    if not imo:
        erros["imo"] = "O IMO é obrigatório."
    elif not imo.isdigit() or len(imo) != 7:
        erros["imo"] = "O IMO deve conter exatamente 7 números."

    nome = nome.strip()
    if not nome:
        erros["nome"] = "O nome do navio é obrigatório."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", nome):
        erros["nome"] = "Contém caracteres inválidos."

    capitao = capitao.strip()
    if not capitao:
        erros["capitao"] = "O nome do capitão é obrigatório."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", capitao):
        erros["capitao"] = "Contém caracteres inválidos."

    companhia = companhia.strip()
    if not companhia:
        erros["companhia"] = "A companhia é obrigatória."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", companhia):
        erros["companhia"] = "Contém caracteres inválidos."

    peso = peso.strip()
    if not peso:
        erros["peso"] = "O peso é obrigatório."
    else:
        try:
            if int(peso) <= 0:
                erros["peso"] = "O peso deve ser maior que zero."
        except ValueError:
            erros["peso"] = "Insira um número inteiro válido."

    if not categoria:
        erros["categoria"] = "Selecione uma categoria de carga."
    return erros


def obter_view(page: ft.Page, aba_ativa="dashboard"):
    # Textos dos 4 cards do topo
    txt_vagas = ft.Text("...", size=30, weight=ft.FontWeight.BOLD)
    txt_fila = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
    txt_pendentes = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
    txt_concluidos = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)

    loading_indicator = ft.ProgressRing(visible=False)

    tabela_vagas = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID Vaga")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Navio Atracado")),
            ft.DataColumn(ft.Text("Tempo de atracação")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
    )

    tabela_navios = ft.DataTable(
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

    tabela_pendentes = ft.DataTable(
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

    txt_vazio_auditoria = ft.Text(
        "Nenhuma solicitação pendente no momento.", size=12, italic=True, visible=False
    )

    imo_em_auditoria = None
    acao_em_auditoria = None

    def carregar_solicitacoes_pendentes(sync=False):
        def run_load():
            try:
                from controller_cadastros import obter_solicitacoes_pendentes_dto
                with obter_sessao() as session:
                    pendentes = obter_solicitacoes_pendentes_dto(session)
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
                            on_click=lambda e, imo=navio.imo_id: abrir_confirmacao(
                                imo, "APROVAR"
                            ),
                        )
                        btn_rejeitar = ft.IconButton(
                            icon=ft.Icons.CANCEL,
                            icon_color=ft.Colors.RED,
                            on_click=lambda e, imo=navio.imo_id: abrir_confirmacao(
                                imo, "REJEITAR"
                            ),
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
                    tabela_pendentes.rows = novas_linhas
                    txt_vazio_auditoria.visible = len(novas_linhas) == 0
                    tabela_pendentes.visible = len(novas_linhas) > 0
                    page.update()
            except Exception as err:
                print(f"Erro na auditoria: {err}")

        if sync:
            run_load()
        else:
            Thread(target=run_load).start()

    def processar_auditoria():
        dialogo_confirmacao.open = False
        page.update()

        def worker():
            msg = ""
            status_cor = ft.Colors.RED
            try:
                from controller_cadastros import auditar_navio_individual
                with obter_sessao() as session:
                    navio_dto = auditar_navio_individual(session, imo_em_auditoria, acao_em_auditoria)
                    if navio_dto.status == "VALIDADO":
                        msg = f"Navio {navio_dto.nome} APROVADO!"
                        status_cor = ft.Colors.GREEN
                    else:
                        msg = f"Navio {navio_dto.nome} REJEITADO — documentação alfandegária incompleta."
                        status_cor = ft.Colors.ORANGE
            except Exception as err:
                msg = f"Erro: {err}"
            finally:
                def finalizar():
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_solicitacoes_pendentes()
                    carregar_dados()

                finalizar()

        Thread(target=worker).start()

    def auditar_todos_pendentes():
        """Aplica a auditoria automática do CLI: aprova quem tem docs completos, rejeita quem não tem."""
        def worker():
            try:
                from controller_cadastros import auditar_solicitacoes_pendentes
                with obter_sessao() as session:
                    auditos = auditar_solicitacoes_pendentes(session)
                    aprovados = sum(1 for n in auditos if n.status == "VALIDADO")
                    rejeitados = sum(1 for n in auditos if n.status == "REJEITADO")

                def finalizar():
                    msg = f"Auditoria concluída: {aprovados} aprovado(s), {rejeitados} rejeitado(s) por documentação."
                    cor = ft.Colors.GREEN if rejeitados == 0 else ft.Colors.ORANGE
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cor)
                    page.snack_bar.open = True
                    carregar_solicitacoes_pendentes()
                    carregar_dados()

                finalizar()
            except Exception as err:
                print(f"Erro na auditoria em lote: {err}")

        Thread(target=worker).start()

    txt_mensagem_modal = ft.Text("")

    def fechar_modal(e):
        dialogo_confirmacao.open = False
        page.update()

    def abrir_confirmacao(imo, acao):
        nonlocal imo_em_auditoria, acao_em_auditoria
        imo_em_auditoria = imo
        acao_em_auditoria = acao
        txt_mensagem_modal.value = (
            f"Deseja {acao.lower()} a solicitação do navio {imo}?"
        )
        dialogo_confirmacao.open = True
        page.update()

    dialogo_confirmacao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Auditoria"),
        content=txt_mensagem_modal,
        actions=[
            ft.TextButton("Confirmar", on_click=lambda e: processar_auditoria()),
            ft.TextButton("Cancelar", on_click=fechar_modal),
        ],
    )
    page.overlay.append(dialogo_confirmacao)

    loading_atracacao = ft.ProgressRing(visible=False, width=20, height=20)
    tipo_atracacao = None

    def processar_atracacao_backend():
        dialogo_confirmar_atracacao.open = False
        loading_atracacao.visible = True
        page.update()

        def worker():
            msg = ""
            status_cor = ft.Colors.RED
            try:
                with obter_sessao() as session:
                    if tipo_atracacao == "PROXIMO":
                        sucesso = atracar_navio(session)
                        if sucesso:
                            msg = "O próximo navio da fila foi atracado com sucesso!"
                            status_cor = ft.Colors.GREEN
                        else:
                            msg = (
                                "Nenhum navio disponível na fila ou nenhuma vaga livre."
                            )
                            status_cor = ft.Colors.ORANGE

                    elif tipo_atracacao == "LOTE":
                        sucesso_count = 0
                        while atracar_navio(session):
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
                def finalizar_ui():
                    loading_atracacao.visible = False
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_dados()
                    page.update()

                finalizar_ui()

        Thread(target=worker).start()

    txt_msg_atracacao = ft.Text("")

    def fechar_modal_atracacao(e):
        dialogo_confirmar_atracacao.open = False
        page.update()

    # ATRACAÇÃO

    def abrir_confirmacao_atracacao(tipo):
        nonlocal tipo_atracacao
        tipo_atracacao = tipo
        if tipo == "PROXIMO":
            txt_msg_atracacao.value = "Deseja atracar o proximo navio?"
        else:
            txt_msg_atracacao.value = (
                "Deseja iniciar a atracação em lote de todas as vagas livres?"
            )
        dialogo_confirmar_atracacao.open = True
        page.update()

    dialogo_confirmar_atracacao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Operação de atracaçao"),
        content=txt_msg_atracacao,
        actions=[
            ft.TextButton(
                "Confirmar atracação", on_click=lambda e: processar_atracacao_backend()
            ),
            ft.TextButton("Cancelar", on_click=fechar_modal_atracacao),
        ],
    )
    page.overlay.append(dialogo_confirmar_atracacao)

    # DESATRACAÇÃO

    loading_desatracacao = ft.ProgressRing(visible=False, width=20, height=20)
    imo_desatracacao = None
    tipo_desatracacao = None

    def processar_desatracacao_backend():
        dialogo_confirmar_desatracacao.open = False
        loading_desatracacao.visible = True
        page.update()

        def worker():
            msg = ""
            status_cor = ft.Colors.RED
            try:
                with obter_sessao() as session:
                    if tipo_desatracacao == "INDIVIDUAL":
                        registrar_desatracacao(session, imo_desatracacao)
                        msg = f"Navio {imo_desatracacao} desatracado com sucesso!"
                        status_cor = ft.Colors.GREEN

                    elif tipo_desatracacao == "MASSA":
                        vagas = obter_painel_vagas_dto(session)
                        sucesso_count = 0
                        for vaga in vagas:
                            if vaga.status == "OCUPADA" and vaga.navio_atracado:
                                registrar_desatracacao(session, vaga.navio_atracado.imo_id)
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
                def finalizar_ui():
                    loading_desatracacao.visible = False
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_dados()
                    page.update()

                finalizar_ui()

        Thread(target=worker).start()

    txt_msg_desatracacao = ft.Text("")

    def fechar_modal_desatracacao(e):
        dialogo_confirmar_desatracacao.open = False
        page.update()

    def abrir_confirmacao_desatracacao(tipo, imo=None):
        nonlocal tipo_desatracacao, imo_desatracacao
        tipo_desatracacao = tipo
        imo_desatracacao = imo

        if tipo == "INDIVIDUAL":
            txt_msg_desatracacao.value = (
                f"Deseja destracar navio {imo} e liberar este berço?"
            )
        else:
            txt_msg_desatracacao.value = "ATENÇÃO: Deseja realmente desatracar TODOS os navios ativos de todos os berços ao mesmo tempo?"

        dialogo_confirmar_desatracacao.open = True
        page.update()

    dialogo_confirmar_desatracacao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Liberação de Berço"),
        content=txt_msg_desatracacao,
        actions=[
            ft.TextButton(
                "Confirmar Saída", on_click=lambda e: processar_desatracacao_backend()
            ),
            ft.TextButton("Cancelar", on_click=fechar_modal_desatracacao),
        ],
    )
    page.overlay.append(dialogo_confirmar_desatracacao)

    # EXCLUSÃO DE NAVIO
    imo_para_excluir = None

    def processar_exclusao_backend():
        dialogo_confirmar_exclusao.open = False
        page.update()

        def worker():
            msg = ""
            status_cor = ft.Colors.RED
            try:
                with obter_sessao() as session:
                    excluir_registro_navio(session, imo_para_excluir)
                    msg = f"Sucesso: Registro do navio ({imo_para_excluir}) foi excluído definitivamente."
                    status_cor = ft.Colors.GREEN
            except Exception as err:
                msg = f"{err}"
                status_cor = ft.Colors.ORANGE
            finally:
                def finalizar_ui():
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_dados()
                    page.update()
                finalizar_ui()

        Thread(target=worker).start()

    txt_msg_exclusao = ft.Text("")

    def fechar_modal_exclusao(e):
        dialogo_confirmar_exclusao.open = False
        page.update()

    def abrir_confirmacao_exclusao(imo):
        nonlocal imo_para_excluir
        imo_para_excluir = imo
        txt_msg_exclusao.value = f"Tem certeza que deseja excluir permanentemente o navio {imo}?"
        dialogo_confirmar_exclusao.open = True
        page.update()

    dialogo_confirmar_exclusao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Exclusão de Registro"),
        content=txt_msg_exclusao,
        actions=[
            ft.TextButton(
                "Confirmar Exclusão", on_click=lambda e: processar_exclusao_backend()
            ),
            ft.TextButton("Cancelar", on_click=fechar_modal_exclusao),
        ],
    )
    page.overlay.append(dialogo_confirmar_exclusao)

    # =============== GRÁFICO DINÂMICO (DADOS REAIS DO BANCO) ===============
    grafico_row = ft.Row(
        [],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.END,
        expand=True,
    )

    container_grafico = ft.Container(
        content=grafico_row,
        height=220,
        padding=20,
        border_radius=10,
        border=ft.Border.all(1, ft.Colors.BLUE_GREY_500),
    )

    # =============== AS 3 CAIXAS INFERIORES ===============
    def criar_caixa(titulo, icone, controles_lista):
        return ft.Container(
            expand=1,
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
            ),
        )

    coluna_logs = ft.Column(spacing=5)
    caixa_logs = criar_caixa("Últimas Operações", ft.Icons.HISTORY, [coluna_logs])

    coluna_proximos = ft.Column(spacing=5)
    caixa_proximos = criar_caixa(
        "Próximos na Fila", ft.Icons.FORMAT_LIST_NUMBERED, [coluna_proximos]
    )

    coluna_vagas = ft.Column(spacing=5)
    caixa_vagas = criar_caixa("Monitor de Berços", ft.Icons.ANCHOR, [coluna_vagas])

    # =============== FUNÇÕES CORE DO CRUD ===============
    navio_selecionado = None
    edit_nome = ft.TextField(label="Nome do Navio", width=300)
    edit_capitao = ft.TextField(label="Nome do Capitão", width=300)
    edit_companhia = ft.TextField(label="Companhia", width=300)
    btn_salvar_edicao = ft.ElevatedButton(
        "Salvar Alterações",
        icon=ft.Icons.SAVE,
        on_click=lambda e: submit_edicao_navio(),
    )

    secao_formulario_edicao = ft.Container(
        visible=False,
        padding=20,
        border=ft.Border.all(1, ft.Colors.BLUE),
        border_radius=10,
        content=ft.Column(
            [
                ft.Text(
                    "Editar Dados da Embarcação", size=20, weight=ft.FontWeight.BOLD
                ),
                ft.Row([edit_nome, edit_capitao, edit_companhia]),
                ft.Row(
                    [
                        btn_salvar_edicao,
                        ft.TextButton("Cancelar", on_click=lambda e: fechar_edicao()),
                    ]
                ),
            ]
        ),
    )

    def fechar_edicao():
        secao_formulario_edicao.visible = False
        edit_nome.value = edit_capitao.value = edit_companhia.value = ""
        page.update()

    def abrir_edicao_navio(navio):
        nonlocal navio_selecionado
        navio_selecionado = navio
        edit_nome.value = navio.nome
        edit_capitao.value = (
            navio.nome_capitao
            if hasattr(navio, "nome_capitao")
            else getattr(navio, "capitao", "")
        )
        edit_companhia.value = navio.companhia
        secao_formulario_edicao.visible = True
        page.update()

    def submit_edicao_navio():
        if not edit_nome.value or not edit_capitao.value or not edit_companhia.value:
            page.snack_bar = ft.SnackBar(
                ft.Text("Preencha todos os campos obrigatórios!"), bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
            page.update()
            return

        btn_salvar_edicao.disabled = True
        loading_indicator.visible = True
        page.update()

        def worker():
            msg = ""
            status = ft.Colors.RED
            try:
                from controller_cadastros import editar_registro_navio
                with obter_sessao() as session:
                    editar_registro_navio(
                        session,
                        navio_selecionado.imo_id,
                        edit_nome.value,
                        edit_capitao.value,
                        edit_companhia.value
                    )
                    msg = f"Navio {edit_nome.value} atualizado com sucesso!"
                    status = ft.Colors.GREEN
            except Exception as e:
                msg = f"Erro ao atualizar navio: {e}"
            finally:
                def finalizar():
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status)
                    page.snack_bar.open = True
                    btn_salvar_edicao.disabled = False
                    loading_indicator.visible = False
                    secao_formulario_edicao.visible = False
                    carregar_dados()
                    page.update()

                finalizar()

        Thread(target=worker).start()

    def liberar_vaga(vaga_id):
        try:
            from controller_operacao import liberar_vaga_individual
            with obter_sessao() as session:
                liberar_vaga_individual(session, vaga_id)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Vaga {vaga_id} liberada!"), bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                carregar_dados()
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao liberar vaga: {e}"), bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
        page.update()

    def carregar_dados(e=None, sync=False):
        def worker():
            try:
                from controller_operacao import (
                    obter_contadores_dashboard,
                    obter_painel_vagas_dto,
                    obter_log_operacoes_dto,
                    obter_contagem_atracacoes_dia,
                )
                from controller_cadastros import obter_todos_navios_dto
                with obter_sessao() as session:
                    # 1. ATUALIZA OS 4 CARDS
                    counts = obter_contadores_dashboard(session)
                    txt_vagas.value = f"{counts['vagas_livres']} / {counts['total_vagas']}"
                    txt_fila.value = str(counts['total_validado'])
                    txt_pendentes.value = str(counts['total_pendente'])
                    txt_concluidos.value = str(counts['total_finalizado'])

                    # 2. ATUALIZA A CAIXA DOS PRÓXIMOS
                    fila = obter_fila_atracacao_dto(session)
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
                    coluna_proximos.controls = novos_proximos

                    # 3. ATUALIZA A CAIXA DE VAGAS
                    vagas = obter_painel_vagas_dto(session)
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
                    coluna_vagas.controls = novas_vagas

                    # 4. ATUALIZA O GRÁFICO DE ATRACAÇÕES DIÁRIAS
                    hoje_date = datetime.now().date()
                    contagem_por_dia = obter_contagem_atracacoes_dia(session, 7)

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
                    grafico_row.controls = novo_grafico

                    # 5. ATUALIZA O LOG DE ÚLTIMAS OPERAÇÕES
                    eventos_log = obter_log_operacoes_dto(session)[:5]
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
                    coluna_logs.controls = novos_logs

                    # 6. TABELAS DA ABA SECUNDÁRIA
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
                                abrir_confirmacao_desatracacao("INDIVIDUAL", imo)
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
                    tabela_vagas.rows = novas_linhas_vagas

                    # Limita a 100 navios mais recentes na aba de gestão para evitar sobrecarga da UI
                    navios = obter_todos_navios_dto(session)
                    navios.sort(key=lambda x: x.data_solicitacao, reverse=True)
                    navios = navios[:100]

                    novas_linhas_navios = []
                    for navio in navios:
                        capitao_nome = navio.nome_capitao
                        btn_editar = ft.IconButton(
                            icon=ft.Icons.EDIT,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e, n=navio: abrir_edicao_navio(n),
                        )
                        btn_excluir = ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=lambda e, imo=navio.imo_id: abrir_confirmacao_exclusao(imo),
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
                    tabela_navios.rows = novas_linhas_navios
                    page.update()
            except Exception as erro:
                print(f"Erro ao carregar dados: {erro}")

        if sync:
            worker()
        else:
            Thread(target=worker).start()

    def create_stat_card(title, text_control, icon, icon_color):
        return ft.Card(
            elevation=4,
            content=ft.Container(
                padding=15,
                width=220,
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

    carregar_dados(sync=True)
    if aba_ativa == "auditoria":
        carregar_solicitacoes_pendentes(sync=True)

    # =============== ABA DASHBOARD ===============
    aba_dashboard = ft.Container(
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
                            on_click=carregar_dados,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        create_stat_card(
                            "Vagas Livres / Total",
                            txt_vagas,
                            ft.Icons.ANCHOR,
                            ft.Colors.BLUE,
                        ),
                        create_stat_card(
                            "Navios na Fila",
                            txt_fila,
                            ft.Icons.FORMAT_LIST_NUMBERED,
                            ft.Colors.ORANGE,
                        ),
                        create_stat_card(
                            "Auditorias Pendentes",
                            txt_pendentes,
                            ft.Icons.HOURGLASS_BOTTOM,
                            ft.Colors.RED,
                        ),
                        create_stat_card(
                            "Operações Concluídas",
                            txt_concluidos,
                            ft.Icons.CHECK_CIRCLE,
                            ft.Colors.GREEN,
                        ),
                    ],
                    spacing=15,
                    run_spacing=15,
                    wrap=True,
                ),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.Text(
                    "Atracações Diárias (Última Semana)",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                container_grafico,
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.Row(
                    [caixa_logs, caixa_proximos, caixa_vagas],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    spacing=15,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
    )

    aba_vagas = ft.Container(
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
                            on_click=carregar_dados,
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
                            on_click=lambda e: abrir_confirmacao_atracacao("PROXIMO"),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                padding=15,
                            ),
                        ),
                        ft.ElevatedButton(
                            "Atracar em Lote",
                            icon=ft.Icons.PLAYLIST_ADD_CHECK,
                            on_click=lambda e: abrir_confirmacao_atracacao("LOTE"),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                padding=15,
                            ),
                        ),
                        ft.ElevatedButton(
                            "Liberar Todos os Berços",
                            icon=ft.Icons.LOGOUT,
                            on_click=lambda e: abrir_confirmacao_desatracacao("MASSA"),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE,
                                padding=15,
                            ),
                        ),
                        loading_atracacao,
                        loading_desatracacao,
                    ],
                    spacing=10,
                ),
                ft.Divider(),
                ft.ListView(controls=[tabela_vagas], expand=True, spacing=10),
            ],
            expand=True,
        ),
    )

    campo_imo = ft.TextField(
        label="Número IMO (ex: 1234567)",
        width=300,
        max_length=7,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.NumbersOnlyInputFilter(),
    )
    campo_nome = ft.TextField(label="Nome do Navio", width=300)
    campo_capitao = ft.TextField(label="Nome do Capitão", width=300)
    campo_companhia = ft.TextField(label="Companhia", width=300)
    campo_peso = ft.TextField(
        label="Peso Total (Toneladas)",
        width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.NumbersOnlyInputFilter(),
    )
    campo_categoria = ft.Dropdown(
        label="Categoria da Carga",
        width=400,
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
    campo_docs = ft.Switch(label="Possui Documentos Alfandegários?", value=False)

    def salvar_navio(e):
        erros = validar_formulario_navio(
            imo=campo_imo.value or "",
            nome=campo_nome.value or "",
            capitao=campo_capitao.value or "",
            companhia=campo_companhia.value or "",
            peso=campo_peso.value or "",
            categoria=campo_categoria.value or "",
        )
        campo_imo.error_text = erros.get("imo")
        campo_nome.error_text = erros.get("nome")
        campo_capitao.error_text = erros.get("capitao")
        campo_companhia.error_text = erros.get("companhia")
        campo_peso.error_text = erros.get("peso")
        campo_categoria.error_text = erros.get("categoria")

        if erros:
            page.update()
            return

        imo_formatado = f"IMO{campo_imo.value.strip()}"
        peso = int(campo_peso.value.strip())

        try:
            eh_perecivel = campo_categoria.value in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
            ]
            with obter_sessao() as session:
                solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=campo_nome.value.strip(),
                    capitao=campo_capitao.value.strip(),
                    companhia=campo_companhia.value.strip(),
                    carga_desc=f"Carga: {campo_categoria.value}",
                    categoria=campo_categoria.value,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=campo_docs.value,
                )
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Sucesso! Navio {campo_nome.value.strip()} registrado!"),
                bgcolor=ft.Colors.GREEN,
            )
            page.snack_bar.open = True

            campo_imo.value = campo_nome.value = campo_capitao.value = (
                campo_companhia.value
            ) = campo_peso.value = ""
            campo_categoria.value = None
            campo_docs.value = False
            carregar_dados()
        except Exception as erro:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao salvar: {erro}"), bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
        page.update()

    aba_gerenciar = ft.Container(
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
                ft.Row([campo_imo, campo_nome]),
                ft.Row([campo_capitao, campo_companhia]),
                ft.Row([campo_categoria, campo_peso]),
                campo_docs,
                ft.ElevatedButton(
                    "Salvar Solicitação",
                    icon=ft.Icons.SAVE,
                    on_click=salvar_navio,
                    style=ft.ButtonStyle(padding=15),
                ),
                ft.Divider(height=20, color=ft.Colors.GREY_300),
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
                secao_formulario_edicao,
                ft.ListView(
                    controls=[tabela_navios], expand=True, spacing=10, height=400
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
    )
    aba_auditoria = ft.Container(
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
                            on_click=lambda e: auditar_todos_pendentes(),
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
                txt_vazio_auditoria,
                ft.ListView(controls=[tabela_pendentes], expand=True, spacing=10),
            ]
        ),
        expand=True,
    )

    aba_retornada = aba_dashboard
    if aba_ativa == "dashboard":
        aba_retornada = aba_dashboard
    elif aba_ativa == "gerenciar":
        aba_retornada = aba_gerenciar
    elif aba_ativa == "vagas":
        aba_retornada = aba_vagas
    elif aba_ativa == "auditoria":
        aba_retornada = aba_auditoria

    # Auto-refresh loop a cada 2 segundos se a aba estiver ativa
    def auto_refresh_loop():
        import time
        while True:
            time.sleep(2)
            if not aba_retornada.page:
                break
            if getattr(page, "active_tab", None) != aba_ativa:
                break
            try:
                carregar_dados(sync=False)
                if aba_ativa == "auditoria":
                    carregar_solicitacoes_pendentes(sync=False)
            except Exception:
                pass

    Thread(target=auto_refresh_loop, daemon=True).start()

    return aba_retornada
