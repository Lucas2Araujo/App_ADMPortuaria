import flet as ft
import os
import sys
from threading import Thread
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

diretorio_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if diretorio_src not in sys.path: sys.path.append(diretorio_src)

from cad import Vaga, StatusVaga, Navio, StatusNavio
from controller_cadastros import solicitar_pre_cadastro 

diretorio_raiz = os.path.abspath(os.path.join(diretorio_src, '..'))
db_path = os.path.join(diretorio_raiz, 'porto.db')
engine = create_engine(f"sqlite:///{db_path}")

def obter_view(page: ft.Page):
    txt_vagas = ft.Text("...", size=32, weight=ft.FontWeight.BOLD)
    txt_fila = ft.Text("0", size=32, weight=ft.FontWeight.BOLD)
    txt_pendentes = ft.Text("0", size=32, weight=ft.FontWeight.BOLD)

    loading_indicator = ft.ProgressRing(visible =False)
    
    tabela_vagas = ft.DataTable( 
        columns=[
        ft.DataColumn(ft.Text("ID Vaga")),
        ft.DataColumn(ft.Text("Status")),
        ft.DataColumn(ft.Text("Navio Atracado")),
        ft.DataColumn(ft.Text("Tempo de atracação")),
        ft.DataColumn(ft.Text("Ações"))    ], 
    rows=[]
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
        rows=[]
    )

    navio_selecionado = None
    edit_nome = ft.TextField(label="Nome do Navio", width=300)
    edit_capitao = ft.TextField(label="Nome do Capitão", width=300)
    edit_companhia = ft.TextField(label="Companhia", width=300)
    edit_salvar_edicao = ft.ElevatedButton("Salvar Alterações", icon=ft.Icons.SAVE, on_click=lambda e: submit_edicao_navio())

    secao_formulario_edicao =ft.Container(
        visible=False,
        padding=20,
        border=ft.border.all(1, ft.Colors.BLUE),
        border_radius=10,
        content=ft.Column([
            ft.Text("Editar Dados da Embarcação", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([edit_nome, edit_capitao, edit_companhia]),
            ft.Row([btn_salvar_edicao, ft.TextButton("Cancelar", on_click=lambda e: fechar_edicao())])
        ])
    )

    def fechar_edicao():
        secao_formulario_edicao.visible = False
        edit_nome.value = edit_capitao.value = edit_companhia.value = ""
        page.update()   

    def abrir_edicao_navio(navio):
        nonlocal navio_selecionado
        navio_selecionado = navio
        edit_nome.value = navio.nome
        edit_capitao.value = navio.nome_capitao if hasattr(navio, 'capitao') else getattr(navio, 'capitao', '')
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

    def worer():
        msg = ""
        status = ft.Colors.RED
        try:

            with Session(engine) as session:
                navio = session.query(Navio).filter(Navio.id == navio_selecionado.id).first()
                if navio:
                    navio.nome = edit_nome.value
                    if hasattr(navio, 'nome_capitao'): navio.nome_capitao = edit_capitao.value
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
            page.call_later(finalizar)
    Thread


    def liberar_vaga(vaga_id):
        try:
            with Session(engine) as session:
                vaga = session.query(Vaga).filter(Vaga.id == vaga_id).first()
                if vaga and vaga.status == StatusVaga.OCUPADA:
                    if hasattr(vaga, 'navio') and vaga.navio:
                        vaga.navio.status = StatusNavio.FINALIZADO
                    vaga.status = StatusVaga.LIVRE
                    vaga.navio_id = None
                    session.commit()
                    page.snack_bar = ft.SnackBar(ft.Text(f"Vaga {vaga_id} liberada!"), bgcolor=ft.Colors.GREEN)
                    page.snack_bar.open = True
                    carregar_dados()
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Vaga {vaga_id} não encontrada ou já está livre."), bgcolor=ft.Colors.RED)
                    page.snack_bar.open = True
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao liberar vaga: {e}"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
        page.update()
            
    def carregar_dados(e=None):
        try:
            with Session(engine) as session:
                total_vagas = session.query(Vaga).count()
                vagas_ocupadas = session.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).count()
                txt_vagas.value = f"{total_vagas - vagas_ocupadas} / {total_vagas}"
                txt_fila.value = str(session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).count())
                txt_pendentes.value = str(session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).count())
                
                vagas = session.query(Vaga).all()
                tabela_vagas.rows.clear()
                for vaga in vagas:
                    navio_nome = vaga.navio.nome if hasattr(vaga, 'navio') and vaga.navio else "N/A"
                    tempo_atracacao = f"{(ft.datetime.now() - vaga.navio.tempo_atracacao).seconds // 60} min" if hasattr(vaga, 'navio') and vaga.navio and vaga.navio.tempo_atracacao else "N/A"
                    status_cor = ft.Colors.GREEN if vaga.status == StatusVaga.LIVRE else ft.Colors.RED
                    
                    btn_liberar = ft.IconButton(
                        icon=ft.Icons.NO_CRASH, icon_color=ft.Colors.RED,
                        disabled=(vaga.status == StatusVaga.LIVRE),
                        on_click=lambda e, vid=vaga.id: liberar_vaga(vid)
                    )
                
                    tabela_vagas.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(f"Berço {vaga.id}")),
                            ft.DataCell(ft.Text(vaga.status.name, color=status_cor, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(navio_nome)),
                            ft.DataCell(ft.Text(tempo_atracacao)),
                            ft.DataCell(btn_liberar
                            )
                        ])
                    )
                
                if e: page.update()
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")

    def create_stat_card(title, text_control, icon, icon_color):
        return ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20, width=240, border_radius=10,
                content=ft.Column([
                    ft.Icon(icon, size=40, color=icon_color),
                    text_control,
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    carregar_dados()

    aba_dashboard = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Text("Métricas em Tempo Real", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar", on_click=carregar_dados)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                create_stat_card("Vagas Livres / Total", txt_vagas, ft.Icons.ANCHOR, ft.Colors.BLUE),
                create_stat_card("Navios na Fila", txt_fila, ft.Icons.FORMAT_LIST_NUMBERED, ft.Colors.ORANGE),
                create_stat_card("Auditorias Pendentes", txt_pendentes, ft.Icons.HOURGLASS_BOTTOM, ft.Colors.RED),
            ], spacing=20)
        ])
    )

    aba_vagas = ft.Container(
        padding=20,
        visible=False,
        content=ft.Column([
            ft.Row([
                ft.Text("Painel de Controle de Vagas", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar", on_click=carregar_dados)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.ListView(controls=tabela_vagas, expand=True, spacing=10)
        ], expand=True)
    )

    campo_imo = ft.TextField(label="Número IMO (ex: 1234567)", width=300)
    campo_nome = ft.TextField(label="Nome do Navio", width=300)
    campo_capitao = ft.TextField(label="Nome do Capitão", width=300)
    campo_companhia = ft.TextField(label="Companhia", width=300)
    campo_peso = ft.TextField(label="Peso Total (Toneladas)", width=200, keyboard_type=ft.KeyboardType.NUMBER)
    
    campo_categoria = ft.Dropdown(
        label="Categoria da Carga",
        width=400,
        options=[
            ft.dropdown.Option(key="URGENTE_PERECIVEL", text="Medicamentos / Carnes (Perecível)"),
            ft.dropdown.Option(key="ALTA_PERECIBILIDADE", text="Frutas / Laticínios (Perecível)"),
            ft.dropdown.Option(key="BAIXA_PERECIBILIDADE", text="Grãos Úmidos"),
            ft.dropdown.Option(key="COMUM", text="Carga Geral / Minérios / Contêineres"),
        ]
    )
    
    campo_docs = ft.Switch(label="Possui Documentos Alfandegários?", value=False)

    def salvar_navio(e):
        if not campo_imo.value or not campo_nome.value or not campo_peso.value or not campo_categoria.value:
            page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos obrigatórios!"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return

        imo_formatado = f"IMO{campo_imo.value}" if campo_imo.value.isdigit() else campo_imo.value
        
        try:
            peso = int(campo_peso.value)
            eh_perecivel = campo_categoria.value in ["URGENTE_PERECIVEL", "ALTA_PERECIBILIDADE"]

            with Session(engine) as session:
                solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=campo_nome.value,
                    capitao=campo_capitao.value,
                    companhia=campo_companhia.value,
                    carga_desc=f"Carga: {campo_categoria.value}",
                    categoria=campo_categoria.value,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=campo_docs.value
                )
            
            page.snack_bar = ft.SnackBar(ft.Text(f"Sucesso! Navio {campo_nome.value} ({imo_formatado}) registrado e aguardando auditoria!"), bgcolor=ft.Colors.GREEN)
            page.snack_bar.open = True
            
            # Limpa os campos após salvar
            campo_imo.value = campo_nome.value = campo_capitao.value = campo_companhia.value = campo_peso.value = ""
            campo_categoria.value = None
            campo_docs.value = False
            
            carregar_dados()
            
        except Exception as erro:
            print(f"Erro ao salvar: {erro}")
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar: {erro}"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            
        page.update()

    aba_gerenciar = ft.Container(
        padding=20,
        visible=False, 
        content=ft.Column([
            ft.Text("Registrar Nova Entrada de Navio", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([campo_imo, campo_nome]),
            ft.Row([campo_capitao, campo_companhia]),
            ft.Row([campo_categoria, campo_peso]),
            campo_docs,
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.ElevatedButton("Salvar Solicitação", icon=ft.Icons.SAVE, on_click=salvar_navio, style=ft.ButtonStyle(padding=20))
        ])
    )

    def trocar_aba(e):
        if e.control.data == "dashboard":
            aba_dashboard.visible = (e.control.data == "dashboard")
            aba_gerenciar.visible = (e.control.data == "gerenciar")
            aba_vagas.visible = (e.control.data == "vagas")
            carregar_dados()
            page.update()

        elif e.control.data == "gerenciar":
            aba_dashboard.visible = False
            aba_gerenciar.visible = True
            aba_vagas.visible = False
        else:
            aba_dashboard.visible = False
            aba_gerenciar.visible = False
            aba_vagas.visible = True
        page.update()

    botoes_navegacao = ft.Row([
        ft.TextButton("Visão Geral", icon=ft.Icons.PIE_CHART, data="dashboard", on_click=trocar_aba),
        ft.TextButton("Gerenciar Embarcações", icon=ft.Icons.SETTINGS, data="gerenciar", on_click=trocar_aba),
        ft.TextButton("Controle de Vagas", icon=ft.Icons.VIEW_AGENDA, data="vagas", on_click=trocar_aba),
    ])

    return ft.Container(
        content=ft.Column([
            botoes_navegacao,
            ft.Divider(),
            aba_dashboard,
            aba_gerenciar,
            aba_vagas
        ], expand=True)
    )
