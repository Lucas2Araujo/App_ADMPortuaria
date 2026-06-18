import flet as ft
import os
import sys
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

    def carregar_dados(e=None):
        try:
            with Session(engine) as session:
                total_vagas = session.query(Vaga).count()
                vagas_ocupadas = session.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).count()
                txt_vagas.value = f"{total_vagas - vagas_ocupadas} / {total_vagas}"
                txt_fila.value = str(session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).count())
                txt_pendentes.value = str(session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).count())
                if e: page.update()
        except Exception:
            pass

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
            aba_dashboard.visible = True
            aba_gerenciar.visible = False
        else:
            aba_dashboard.visible = False
            aba_gerenciar.visible = True
        page.update()

    botoes_navegacao = ft.Row([
        ft.TextButton("Visão Geral", icon=ft.Icons.PIE_CHART, data="dashboard", on_click=trocar_aba),
        ft.TextButton("Gerenciar Embarcações", icon=ft.Icons.SETTINGS, data="gerenciar", on_click=trocar_aba),
    ])

    return ft.Container(
        content=ft.Column([
            botoes_navegacao,
            ft.Divider(),
            aba_dashboard,
            aba_gerenciar
        ], expand=True)
    )