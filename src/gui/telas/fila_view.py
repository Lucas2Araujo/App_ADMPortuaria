import os
import sys
import flet as ft
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Ajuste de caminhos idêntico aos outros painéis para não quebrar os imports
diretorio_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from cad import Navio, StatusNavio

# Configuração de conexão com o Banco de Dados correto na raiz
diretorio_raiz = os.path.abspath(os.path.join(diretorio_src, ".."))
db_path = os.path.join(diretorio_raiz, "porto.db")
engine = create_engine(f"sqlite:///{db_path}")


def obter_view(page: ft.Page):
    # Tabela que vai listar os navios na fila
    tabela_fila = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Posição", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Nome do Navio", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Observação / Carga", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
    )

    # Texto informativo caso a fila esteja vazia
    txt_vazio = ft.Text(
        "Nenhum navio aguardando na fila de atracação no momento.",
        size=16,
        italic=True,
        color=ft.Colors.GREY_500,
        visible=False,
    )

    def abrir_detalhes_navio(navio, posicao):
        print(f"[DEBUG] Gerando ficha técnica do navio {navio.nome} (Posição: {posicao})...")

        def fechar_dialogo(e):
            dlg.open = False
            page.update()

        # Tratamento de segurança caso colunas tenham nomes ligeiramente diferentes no ORM
        capitao = getattr(navio, "nome_capitao", getattr(navio, "capitao", "Não informado"))
        peso = f"{getattr(navio, 'peso', 'N/A')} Toneladas"
        categoria = getattr(navio, "categoria", "N/A")
        carga_desc = getattr(navio, "carga_desc", "N/A")
        documentos = "Aprovados" if getattr(navio, "possui_documentos", False) else "Pendente"
        perecivel = "Sim (Alta)" if getattr(navio, "eh_perecivel", False) else "Não"
        score = getattr(navio, "score", "N/A")

        # Função auxiliar para criar linhas com "justify between" e ícones
        def criar_linha(icone, rotulo, valor, destaque=False):
            return ft.Row(
                [
                    # Lado Esquerdo: Ícone + Rótulo
                    ft.Row(
                        [
                            ft.Icon(icone, size=18, color=ft.Colors.BLUE_GREY_500),
                            ft.Text(rotulo, color=ft.Colors.BLUE_GREY_700),
                        ],
                        spacing=8,
                    ),
                    # Lado Direito: Valor da variável
                    ft.Text(
                        str(valor),
                        weight=ft.FontWeight.BOLD if destaque else ft.FontWeight.NORMAL,
                        color=ft.Colors.BLUE_900 if destaque else ft.Colors.BLACK87,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, # Alinha nas extremidades
            )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DIRECTIONS_BOAT, color=ft.Colors.BLUE_700),
                    ft.Text(f"Ficha Técnica — Fila #{posicao}", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                width=500, # Aumentei um pouco a largura para a divisão ficar elegante
                content=ft.Column(
                    [
                        ft.Divider(height=10),
                        criar_linha(ft.Icons.DIRECTIONS_BOAT_OUTLINED, "Nome da Embarcação:", navio.nome, destaque=True),
                        criar_linha(ft.Icons.NUMBERS, "Código IMO ID:", navio.imo_id),
                        criar_linha(ft.Icons.PERSON_OUTLINE, "Capitão Responsável:", capitao),
                        criar_linha(ft.Icons.BUSINESS, "Companhia / Armador:", navio.companhia),
                        criar_linha(ft.Icons.SCALE, "Peso Declarado:", peso),
                        criar_linha(ft.Icons.CATEGORY_OUTLINED, "Categoria Logística:", categoria),
                        criar_linha(ft.Icons.DESCRIPTION_OUTLINED, "Manifesto de Carga:", carga_desc),
                        criar_linha(ft.Icons.AC_UNIT, "Carga Perecível:", perecivel),
                        criar_linha(ft.Icons.ASSIGNMENT_TURNED_IN_OUTLINED, "Doc. Alfandegária:", documentos),
                        ft.Divider(height=10),
                        criar_linha(ft.Icons.STARS, "Score Atual de Fila:", score, destaque=True),
                    ],
                    tight=True,
                    spacing=12,
                ),
            ),
            actions=[
                ft.TextButton("Fechar Janela", on_click=fechar_dialogo),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dlg
        if dlg not in page.overlay:
            page.overlay.append(dlg)
            
        dlg.open = True
        page.update()    
    def carregar_dados_fila(e=None):
        """Busca os navios validados no banco e monta as linhas da tabela ordenadas."""
        try:
            with Session(engine) as session:
                # Se o seu modelo possuir a coluna 'score', ordena por ela de forma decrescente, senão usa o ID padrão
                query = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO)
                
                if hasattr(Navio, "score"):
                    navios = query.order_by(Navio.score.desc()).all()
                else:
                    navios = query.all()

                tabela_fila.rows.clear()

                if not navios:
                    txt_vazio.visible = True
                    tabela_fila.visible = False
                else:
                    txt_vazio.visible = False
                    tabela_fila.visible = True

                    # Varre a lista calculando a posição na fila (index + 1)
                    for idx, navio in enumerate(navios):
                        posicao = idx + 1
                        
                        # Define um texto de observação amigável baseado na perecibilidade
                        obs_texto = navio.carga_desc if hasattr(navio, "carga_desc") else "Carga Geral"
                        if getattr(navio, "eh_perecivel", False):
                            obs_texto += " ⚠️ [PERECÍVEL]"

                        # Criação do botão "Ver Mais" para a linha atual
                        btn_ver_mais = ft.ElevatedButton(
                            "Ver mais",
                            icon=ft.Icons.INFO_OUTLINED,
                            on_click=lambda e, n=navio, p=posicao: abrir_detalhes_navio(n, p),
                            style=ft.ButtonStyle(
                                color=ft.Colors.BLUE_700,
                                bgcolor=ft.Colors.BLUE_50,
                            )
                        )

                        # Adiciona a linha estruturada na tabela visual
                        tabela_fila.rows.append(
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(f"{posicao}º", weight=ft.FontWeight.BOLD)),
                                    ft.DataCell(ft.Text(navio.nome)),
                                    ft.DataCell(ft.Text(obs_texto, color=ft.Colors.BLUE_GREY_700)),
                                    ft.DataCell(btn_ver_mais),
                                ]
                            )
                        )
                if e:
                    page.update()
        except Exception as erro:
            print(f"Erro ao carregar fila de atracação: {erro}")

    # Força o carregamento assim que a tela abre pela primeira vez
    carregar_dados_fila()

    # Retorna o contêiner visual estruturado com cabeçalho, botão de atualizar e a tabela
    return ft.Container(
        padding=30,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.FORMAT_LIST_NUMBERED, size=32, color=ft.Colors.BLUE_GREY_800),
                                ft.Text("Fila de Atracação Dinâmica", size=26, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=10,
                        ),
                        ft.IconButton(
                            ft.Icons.REFRESH,
                            tooltip="Atualizar Fila",
                            on_click=carregar_dados_fila,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(
                    "Abaixo estão listadas as embarcações autorizadas a atracar, ordenadas pelo motor de prioridade do porto.",
                    size=14,
                    color=ft.Colors.GREY_600,
                ),
                ft.Divider(height=20),
                txt_vazio,
                ft.ListView(controls=[tabela_fila], expand=True, spacing=10),
            ],
            expand=True,
        ),
    )