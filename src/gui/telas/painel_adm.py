import flet as ft
import os
import sys
import re
import random
from datetime import datetime, timedelta
from threading import Thread
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

diretorio_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from cad import Vaga, StatusVaga, Navio, StatusNavio, Atracacao
from controller_cadastros import solicitar_pre_cadastro

diretorio_raiz = os.path.abspath(os.path.join(diretorio_src, ".."))
db_path = os.path.join(diretorio_raiz, "porto.db")
engine = create_engine(f"sqlite:///{db_path}")


def validar_formulario_navio(imo: str, nome: str, capitao: str, companhia: str, peso: str, categoria: str) -> dict[str, str]:
    erros: dict[str, str] = {}
    imo = imo.strip()
    if not imo: erros["imo"] = "O IMO é obrigatório."
    elif not imo.isdigit() or len(imo) != 7: erros["imo"] = "O IMO deve conter exatamente 7 números."

    nome = nome.strip()
    if not nome: erros["nome"] = "O nome do navio é obrigatório."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", nome): erros["nome"] = "Contém caracteres inválidos."

    capitao = capitao.strip()
    if not capitao: erros["capitao"] = "O nome do capitão é obrigatório."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", capitao): erros["capitao"] = "Contém caracteres inválidos."

    companhia = companhia.strip()
    if not companhia: erros["companhia"] = "A companhia é obrigatória."
    elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", companhia): erros["companhia"] = "Contém caracteres inválidos."

    peso = peso.strip()
    if not peso: erros["peso"] = "O peso é obrigatório."
    else:
        try:
            if int(peso) <= 0: erros["peso"] = "O peso deve ser maior que zero."
        except ValueError: erros["peso"] = "Insira um número inteiro válido."

    if not categoria: erros["categoria"] = "Selecione uma categoria de carga."
    return erros


def obter_view(page: ft.Page):
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

    tabela_pendentes =ft.DataTable(
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

    txt_vazio_auditoria =ft.Text("Nenhuma solicitação pendente no momento.", size=12, italic=True, visible= False)

    imo_em_auditoria = None
    acao_em_auditoria = None

    def carregar_solicitacoes_pendentes():
        def worker():
            try:
                with Session(engine) as session:
                    pendentes = session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).all()
                    novas_linhas = []
                    for navio in pendentes:
                        capitao_nome = navio.nome_capitao if hasattr(navio, "nome_capitao") else getattr(navio, "capitao", "N/A")
                        carga_desc = navio.carga_desc if hasattr(navio, "carga_desc") else "N/A"
                        
                        btn_aprovar = ft.IconButton(
                            icon=ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.GREEN,
                            on_click=lambda e, imo=navio.imo_id: abrir_confirmacao(imo, "APROVAR")
                        )
                        btn_rejeitar = ft.IconButton(
                            icon=ft.Icons.CANCEL, icon_color=ft.Colors.RED,
                            on_click=lambda e, imo=navio.imo_id: abrir_confirmacao(imo, "REJEITAR")
                        )
                        novas_linhas.append(
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text(navio.imo_id)),
                                ft.DataCell(ft.Text(navio.nome)),
                                ft.DataCell(ft.Text(capitao_nome)),
                                ft.DataCell(ft.Text(navio.companhia)),
                                ft.DataCell(ft.Text(carga_desc)),
                                ft.DataCell(ft.Row([btn_aprovar, btn_rejeitar], spacing=5)),
                            ])
                        )
                def atualizar_ui():
                    tabela_pendentes.rows = novas_linhas
                    txt_vazio_auditoria.visible = len(novas_linhas) == 0
                    tabela_pendentes.visible = len(novas_linhas) > 0
                    page.update()
                page.call_later(atualizar_ui)
            except Exception as err:
                print(f"Erro na auditoria: {err}")
        Thread(target=worker).start()

    def processar_auditoria():
        dialogo_confirmacao.open = False
        page.update()
        def worker():
            msg = ""
            status_cor = ft.Colors.RED
            try:
                with Session(engine) as session:
                    navio = session.query(Navio).filter(Navio.imo_id == imo_em_auditoria).first()
                    if navio:
                        if acao_em_auditoria == "APROVAR":
                            navio.status = StatusNavio.VALIDADO
                            msg = f"Navio {navio.nome} APROVADO!"
                            status_cor = ft.Colors.GREEN
                        elif acao_em_auditoria == "REJEITAR":
                            navio.status = StatusNavio.FINALIZADO
                            msg = f"Solicitação do Navio {navio.nome} REJEITADA!"
                            status_cor = ft.Colors.ORANGE
                        session.commit()
            except Exception as err:
                msg = f"Erro: {err}"
            finally:
                def finalizar():
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_solicitacoes_pendentes()
                    carregar_dados() # Atualiza os cards do dashboard também
                page.call_later(finalizar)
        Thread(target=worker).start()

    txt_mensagem_modal = ft.Text("")
    def fechar_modal(e):
        dialogo_confirmacao.open = False
        page.update()

    def abrir_confirmacao(imo, acao):
        nonlocal imo_em_auditoria, acao_em_auditoria
        imo_em_auditoria = imo
        acao_em_auditoria = acao
        txt_mensagem_modal.value = f"Deseja {acao.lower()} a solicitação do navio {imo}?"
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
                with Session(engine) as session:
                    from controller_operacao import atracar_navio
                    
                    if tipo_atracacao == "PROXIMO":
                        sucesso = atracar_navio(session)
                        if sucesso:
                            msg = "O próximo navio da fila foi atracado com sucesso!"
                            status_cor = ft.Colors.GREEN
                        else:
                            msg = "Nenhum navio disponível na fila ou nenhuma vaga livre."
                            status_cor = ft.Colors.ORANGE
                    
                    elif tipo_atracacao == "LOTE":
                        sucesso_count = 0
                        while atracar_navio(session):
                            sucesso_count += 1
                        session.commit()
                        
                        if sucesso_count > 0:
                            msg = f"Atracação em lote concluída! {sucesso_count} navio(s) atracado(s)."
                            status_cor = ft.Colors.GREEN
                        else:
                            msg = "Nenhum navio pôde ser atracado em lote."
                            status_cor = ft.Colors.ORANGE
                    session.commit()
            except Exception as err:
                msg = f"Erro na operação de atracação: {err}"
            finally:
                def finalizar_ui():
                    loading_atracacao.visible = False
                    page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
                    page.snack_bar.open = True
                    carregar_dados()
                    page.update()
                page.call_later(finalizar_ui)

        Thread(target=worker).start()

    txt_msg_atracacao = ft.Text("")
    
    def fechar_modal_atracacao(e):
        dialogo_confirmar_atracacao.open = False
        page.update()

    def abrir_confirmacao_atracacao(tipo):
        nonlocal tipo_atracacao
        tipo_atracacao = tipo
        if tipo == "PROXIMO":
            txt_msg_atracacao.value = "Deseja atracar o proximo navio?"
        else:
            txt_msg_atracacao.value = "Deseja iniciar a atracação em lote de todas as vagas livres?"
        dialogo_confirmar_atracacao.open = True
        page.update()

    dialogo_confirmar_atracacao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Operação de atracaçao"),
        content=txt_msg_atracacao,
        actions=[
            ft.TextButton("Confirmar atracação", on_click=lambda e: processar_atracacao_backend()),
            ft.TextButton("Cancelar", on_click=fechar_modal_atracacao),
        ],
    )
    page.overlay.append(dialogo_confirmar_atracacao)


    # =============== DADOS FICTÍCIOS E GRÁFICO (VERSÃO ESTÁVEL) ===============
    hoje = datetime.now()
    dias_semana = [(hoje - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    valores_atracacoes = [random.randint(2, 12) for _ in range(7)]

    barras_grafico = []
    max_valor = 15 # Teto de exibição
    altura_max_barras = 120 # Altura máxima do container

    for dia, valor in zip(dias_semana, valores_atracacoes):
        altura_calculada = max(10, (valor / max_valor) * altura_max_barras) # Pelo menos 10px
        
        barras_grafico.append(
            ft.Column(
                [
                    ft.Text(str(valor), size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    ft.Container(
                        width=35,
                        height=altura_calculada,
                        bgcolor=ft.Colors.BLUE_500,
                        border_radius=5, # CORREÇÃO: Usando um inteiro genérico e universal para evitar quebra de API
                        tooltip=f"{valor} atracações no dia {dia}"
                    ),
                    ft.Text(dia, size=11, color=ft.Colors.BLUE_GREY_600)
                ],
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    grafico_estavel = ft.Row(
        barras_grafico,
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.END,
        expand=True
    )

    container_grafico = ft.Container(
        content=grafico_estavel,
        height=220,
        padding=20,
        border_radius=10,
        border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
        bgcolor=ft.Colors.WHITE,
    )

    # =============== AS 3 CAIXAS INFERIORES ===============
    def criar_caixa(titulo, icone, controles_lista):
        return ft.Container(
            expand=1,
            padding=15,
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_200),
            bgcolor=ft.Colors.WHITE,
            content=ft.Column(
                [
                    ft.Row([ft.Icon(icone, color=ft.Colors.BLUE_700, size=20), ft.Text(titulo, weight=ft.FontWeight.BOLD, size=14)], spacing=5),
                    ft.Divider(height=10),
                    *controles_lista
                ],
                spacing=5,
            )
        )

    logs_ficticios = [
        "⬅️ Saída: IMO9593505 (Berço 1) às 08:30",
        "➡️ Entrada: IMO1234567 (Berço 2) às 09:15",
        "⬅️ Saída: IMO7654321 (Berço 4) às 11:00",
        "➡️ Entrada: IMO1122334 (Berço 1) às 11:45",
        "➡️ Entrada: IMO9988776 (Berço 4) às 14:20",
    ]
    lista_logs = [ft.Text(log, size=12, color=ft.Colors.BLUE_GREY_800) for log in logs_ficticios]
    caixa_logs = criar_caixa("Últimas Atracações", ft.Icons.HISTORY, lista_logs)

    coluna_proximos = ft.Column(spacing=5)
    caixa_proximos = criar_caixa("Próximos na Fila", ft.Icons.FORMAT_LIST_NUMBERED, [coluna_proximos])

    coluna_vagas = ft.Column(spacing=5)
    caixa_vagas = criar_caixa("Monitor de Berços", ft.Icons.ANCHOR, [coluna_vagas])


    # =============== FUNÇÕES CORE DO CRUD ===============
    navio_selecionado = None
    edit_nome = ft.TextField(label="Nome do Navio", width=300)
    edit_capitao = ft.TextField(label="Nome do Capitão", width=300)
    edit_companhia = ft.TextField(label="Companhia", width=300)
    btn_salvar_edicao = ft.ElevatedButton("Salvar Alterações", icon=ft.Icons.SAVE, on_click=lambda e: submit_edicao_navio())

    secao_formulario_edicao = ft.Container(
        visible=False,
        padding=20,
        border=ft.Border.all(1, ft.Colors.BLUE),
        border_radius=10,
        content=ft.Column([
            ft.Text("Editar Dados da Embarcação", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([edit_nome, edit_capitao, edit_companhia]),
            ft.Row([btn_salvar_edicao, ft.TextButton("Cancelar", on_click=lambda e: fechar_edicao())]),
        ]),
    )

    def fechar_edicao():
        secao_formulario_edicao.visible = False
        edit_nome.value = edit_capitao.value = edit_companhia.value = ""
        page.update()

    def abrir_edicao_navio(navio):
        nonlocal navio_selecionado
        navio_selecionado = navio
        edit_nome.value = navio.nome
        edit_capitao.value = navio.nome_capitao if hasattr(navio, "capitao") else getattr(navio, "capitao", "")
        edit_companhia.value = navio.companhia
        secao_formulario_edicao.visible = True
        page.update()

    def submit_edicao_navio():
        if not edit_nome.value or not edit_capitao.value or not edit_companhia.value:
            page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos obrigatórios!"), bgcolor=ft.Colors.RED)
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
                with Session(engine) as session:
                    navio = session.query(Navio).filter(Navio.imo_id == navio_selecionado.imo_id).first()
                    if navio:
                        navio.nome = edit_nome.value
                        if hasattr(navio, "nome_capitao"): navio.nome_capitao = edit_capitao.value
                        else: navio.capitao = edit_capitao.value
                        navio.companhia = edit_companhia.value
                        session.commit()
                        msg = f"Navio {navio.nome} atualizado com sucesso!"
                        status = ft.Colors.GREEN
                    else:
                        msg = "Navio não encontrado."
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
            with Session(engine) as session:
                vaga = session.query(Vaga).filter(Vaga.id == vaga_id).first()
                if vaga and vaga.status == StatusVaga.OCUPADA:
                    if hasattr(vaga, "navio") and vaga.navio:
                        vaga.navio.status = StatusNavio.FINALIZADO
                    vaga.status = StatusVaga.LIVRE
                    vaga.navio_id = None
                    session.commit()
                    page.snack_bar = ft.SnackBar(ft.Text(f"Vaga {vaga_id} liberada!"), bgcolor=ft.Colors.GREEN)
                    page.snack_bar.open = True
                    carregar_dados()
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao liberar vaga: {e}"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
        page.update()

    def carregar_dados(e=None):
        try:
            with Session(engine) as session:
                # 1. ATUALIZA OS 4 CARDS
                total_vagas = session.query(Vaga).count()
                vagas_ocupadas = session.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).count()
                txt_vagas.value = f"{total_vagas - vagas_ocupadas} / {total_vagas}"
                txt_fila.value = str(session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).count())
                txt_pendentes.value = str(session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).count())
                txt_concluidos.value = str(session.query(Navio).filter(Navio.status == StatusNavio.FINALIZADO).count())

                # 2. ATUALIZA A CAIXA DOS PRÓXIMOS
                query_proximos = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO)
                if hasattr(Navio, "score"):
                    proximos = query_proximos.order_by(Navio.score.desc()).limit(5).all()
                else:
                    proximos = query_proximos.limit(5).all()
                
                coluna_proximos.controls.clear()
                if not proximos:
                    coluna_proximos.controls.append(ft.Text("A fila está vazia no momento.", size=12, italic=True))
                else:
                    for idx, p in enumerate(proximos):
                        coluna_proximos.controls.append(ft.Text(f"{idx+1}º - {p.nome}", size=12, weight=ft.FontWeight.W_500))

                # 3. ATUALIZA A CAIXA DE VAGAS
                todas_vagas = session.query(Vaga).all()
                coluna_vagas.controls.clear()
                for v in todas_vagas:
                    if v.status == StatusVaga.LIVRE:
                        coluna_vagas.controls.append(ft.Text(f"🟢 Berço {v.id}: Livre", size=12, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD))
                    else:
                        coluna_vagas.controls.append(ft.Text(f"🔴 Berço {v.id}: Ocupado", size=12, color=ft.Colors.RED_700))

                # 4. TABELAS DA ABA SECUNDÁRIA
                tabela_vagas.rows.clear()
                for vaga in todas_vagas:
                    navio_nome = vaga.navio.nome if hasattr(vaga, "navio") and vaga.navio else "N/A"
                    tempo_atracacao = (
                        f"{(ft.datetime.now() - vaga.navio.tempo_atracacao).seconds // 60} min"
                        if hasattr(vaga, "navio") and vaga.navio and vaga.navio.tempo_atracacao else "N/A"
                    )
                    status_cor = ft.Colors.GREEN if vaga.status == StatusVaga.LIVRE else ft.Colors.RED
                    btn_liberar = ft.IconButton(
                        icon=ft.Icons.NO_CRASH, icon_color=ft.Colors.RED,
                        disabled=(vaga.status == StatusVaga.LIVRE),
                        on_click=lambda e, vid=vaga.id: liberar_vaga(vid),
                    )
                    tabela_vagas.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(f"Berço {vaga.id}")),
                            ft.DataCell(ft.Text(vaga.status.name, color=status_cor, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(navio_nome)),
                            ft.DataCell(ft.Text(tempo_atracacao)),
                            ft.DataCell(btn_liberar),
                        ])
                    )

                navios = session.query(Navio).all()
                tabela_navios.rows.clear()
                for navio in navios:
                    capitao_nome = navio.nome_capitao if hasattr(navio, "nome_capitao") else getattr(navio, "capitao", "N/A")
                    btn_editar = ft.IconButton(
                        icon=ft.Icons.EDIT, icon_color=ft.Colors.BLUE,
                        on_click=lambda e, n=navio: abrir_edicao_navio(n),
                    )
                    tabela_navios.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(navio.imo_id)),
                            ft.DataCell(ft.Text(navio.nome)),
                            ft.DataCell(ft.Text(capitao_nome)),
                            ft.DataCell(ft.Text(navio.companhia)),
                            ft.DataCell(ft.Text(navio.status.name if hasattr(navio.status, "name") else str(navio.status))),
                            ft.DataCell(btn_editar),
                        ])
                    )
                if e: page.update()
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")

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
                        ft.Text(title, size=13, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    carregar_dados()

    # =============== ABA DASHBOARD ===============
    aba_dashboard = ft.Container(
        padding=20,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Métricas em Tempo Real", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar", on_click=carregar_dados),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        create_stat_card("Vagas Livres / Total", txt_vagas, ft.Icons.ANCHOR, ft.Colors.BLUE),
                        create_stat_card("Navios na Fila", txt_fila, ft.Icons.FORMAT_LIST_NUMBERED, ft.Colors.ORANGE),
                        create_stat_card("Auditorias Pendentes", txt_pendentes, ft.Icons.HOURGLASS_BOTTOM, ft.Colors.RED),
                        create_stat_card("Operações Concluídas", txt_concluidos, ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN),
                    ],
                    spacing=15,
                    run_spacing=15,
                    wrap=True,
                ),
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.Text("Atracações Diárias (Última Semana)", size=18, weight=ft.FontWeight.BOLD),
                container_grafico,
                ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                ft.Row(
                    [caixa_logs, caixa_proximos, caixa_vagas],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    spacing=15,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True
    )

    aba_vagas = ft.Container(
        padding=20, visible=False,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Painel de Controle de Vagas", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar", on_click=carregar_dados),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.ListView(controls=[tabela_vagas], expand=True, spacing=10),
            ], expand=True,
        ),
    )

    campo_imo = ft.TextField(label="Número IMO (ex: 1234567)", width=300, max_length=7, keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter())
    campo_nome = ft.TextField(label="Nome do Navio", width=300)
    campo_capitao = ft.TextField(label="Nome do Capitão", width=300)
    campo_companhia = ft.TextField(label="Companhia", width=300)
    campo_peso = ft.TextField(label="Peso Total (Toneladas)", width=200, keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.NumbersOnlyInputFilter())
    campo_categoria = ft.Dropdown(
        label="Categoria da Carga", width=400,
        options=[
            ft.dropdown.Option(key="URGENTE_PERECIVEL", text="Medicamentos / Carnes (Perecível)"),
            ft.dropdown.Option(key="ALTA_PERECIBILIDADE", text="Frutas / Laticínios (Perecível)"),
            ft.dropdown.Option(key="BAIXA_PERECIBILIDADE", text="Grãos Úmidos"),
            ft.dropdown.Option(key="COMUM", text="Carga Geral / Minérios / Contêineres"),
        ],
    )
    campo_docs = ft.Switch(label="Possui Documentos Alfandegários?", value=False)

    def salvar_navio(e):
        erros = validar_formulario_navio(
            imo=campo_imo.value or "", nome=campo_nome.value or "",
            capitao=campo_capitao.value or "", companhia=campo_companhia.value or "",
            peso=campo_peso.value or "", categoria=campo_categoria.value or "",
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
            eh_perecivel = campo_categoria.value in ["URGENTE_PERECIVEL", "ALTA_PERECIBILIDADE"]
            with Session(engine) as session:
                solicitar_pre_cadastro(
                    session=session, imo=imo_formatado, nome=campo_nome.value.strip(),
                    capitao=campo_capitao.value.strip(), companhia=campo_companhia.value.strip(),
                    carga_desc=f"Carga: {campo_categoria.value}", categoria=campo_categoria.value,
                    peso=peso, eh_perecivel=eh_perecivel, possui_documentos=campo_docs.value,
                )
            page.snack_bar = ft.SnackBar(ft.Text(f"Sucesso! Navio {campo_nome.value.strip()} registrado!"), bgcolor=ft.Colors.GREEN)
            page.snack_bar.open = True

            campo_imo.value = campo_nome.value = campo_capitao.value = campo_companhia.value = campo_peso.value = ""
            campo_categoria.value = None
            campo_docs.value = False
            carregar_dados()
        except Exception as erro:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar: {erro}"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
        page.update()

    aba_gerenciar = ft.Container(
        padding=20, visible=False,
        content=ft.Column([
            ft.Text("Registrar Nova Entrada de Navio", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([campo_imo, campo_nome]),
            ft.Row([campo_capitao, campo_companhia]),
            ft.Row([campo_categoria, campo_peso]),
            campo_docs,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.ElevatedButton("Salvar Solicitação", icon=ft.Icons.SAVE, on_click=salvar_navio, style=ft.ButtonStyle(padding=20)),
        ]),
    )
    aba_auditoria = ft.Container(
        padding=20, 
        visible=False, # Começa oculta para não encavalar com o Dashboard
        content=ft.Column([
            ft.Text("Auditoria de Solicitações Pendentes", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            txt_vazio_auditoria, # Texto que diz se não houver navios
            ft.ListView(controls=[tabela_pendentes], expand=True, spacing=10) # Lista que segura a tabela
        ]),
        expand=True
    )

    def trocar_aba(e):
        aba_dashboard.visible = e.control.data == "dashboard"
        aba_gerenciar.visible = e.control.data == "gerenciar"
        aba_vagas.visible = e.control.data == "vagas"
        aba_auditoria.visible = e.control.data == "auditoria"

        if aba_dashboard.visible: carregar_dados()
        if aba_auditoria.visible: carregar_solicitacoes_pendentes()
        page.update()

    botoes_navegacao = ft.Row([
        ft.TextButton("Visão Geral", icon=ft.Icons.PIE_CHART, data="dashboard", on_click=trocar_aba),
        ft.TextButton("Gerenciar Embarcações", icon=ft.Icons.SETTINGS, data="gerenciar", on_click=trocar_aba),
        ft.TextButton("Controle de Vagas", icon=ft.Icons.VIEW_AGENDA, data="vagas", on_click=trocar_aba),
        ft.TextButton("Auditar Solicitações", icon=ft.Icons.AUDIT_TRAIL, data="auditoria", on_click=trocar_aba),
    ])

    return ft.Container(content=ft.Column([botoes_navegacao, ft.Divider(), aba_dashboard, aba_gerenciar, aba_vagas, aba_auditoria], expand=True))