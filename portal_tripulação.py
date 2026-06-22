import re
import flet as ft
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Importações estritas baseadas no ecossistema do seu projeto
from cad import Base, Navio, Carga, StatusNavio
from controller_cadastros import solicitar_pre_cadastro

# Expressão regular padrão para validação de campos textuais (padrão SonarQube)
REGEX_VALIDACAO = r"[A-Za-z0-9À-ÿ\s\-']+"

# Estrutura de dados espelhada no dicionário MAPA_CARGAS do seu arquivo pop_bd.py
MAPA_CARGAS_SISTEMA = {
    'Vacinas': 'URGENTE_PERECIVEL',
    'Carne Bovina': 'URGENTE_PERECIVEL',
    'Peixes': 'URGENTE_PERECIVEL',
    'Frutas': 'ALTA_PERECIBILIDADE',
    'Verduras': 'ALTA_PERECIBILIDADE',
    'Grãos': 'BAIXA_PERECIBILIDADE',
    'Biscoitos': 'BAIXA_PERECIBILIDADE',
    'Petróleo': 'COMUM',
    'Minério de Ferro': 'COMUM',
    'Containers': 'COMUM',
    'Automóveis': 'COMUM',
    'Produtos Químicos': 'COMUM',
    'Gás Natural': 'COMUM',
    'Carvão': 'COMUM',
    'Eletrodomésticos': 'COMUM',
    'RTX 5090': 'COMUM'
}

def obter_tela_formulario(page: ft.Page, engine_bd) -> ft.Container:
    """
    Retorna o componente de formulário do Portal da Tripulação totalmente aderente
    às assinaturas de função e modelos ORM do ecossistema original.
    """
    
    # --- CONFIGURAÇÃO DOS INPUTS ---
    txt_imo = ft.TextField(
        label="Número IMO (7 dígitos numéricos)",
        placeholder="Ex: 9593505",
        max_length=7,
        icon=ft.icons.NUMBERS,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=290
    )
    
    txt_nome_navio = ft.TextField(
        label="Nome da Embarcação",
        placeholder="Ex: ESTRELA DO MAR",
        icon=ft.icons.DIRECTIONS_BOAT,
        width=290
    )
    
    txt_capitao = ft.TextField(
        label="Nome do Capitão",
        placeholder="Ex: Cap. Amilcar Silva",
        icon=ft.icons.PERSON,
        width=290
    )
    
    txt_companhia = ft.TextField(
        label="Companhia / Armador",
        placeholder="Ex: Transatlântica Logística",
        icon=ft.icons.BUSINESS,
        width=290
    )
    
    txt_peso = ft.TextField(
        label="Peso Total (Toneladas)",
        placeholder="Ex: 45",
        icon=ft.icons.SCALE,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200
    )
    
    # Mapeia as opções do Dropdown usando as chaves do seu pop_bd.py
    opcoes_dropdown = [ft.dropdown.Option(prod) for prod in MAPA_CARGAS_SISTEMA.keys()]
    opcoes_dropdown.append(ft.dropdown.Option(key="OUTROS", text="Outros (Especificar Manualmente)"))
    
    txt_descricao_manual = ft.TextField(
        label="Especifique a Carga",
        placeholder="Ex: Maquinário Industrial Agrícola",
        visible=False,
        icon=ft.icons.DESCRIPTION,
        multiline=True,
        rows=2
    )
    
    def monitorar_dropdown_carga(e):
        txt_descricao_manual.visible = (dd_produto_carga.value == "OUTROS")
        page.update()

    dd_produto_carga = ft.Dropdown(
        label="Carga Principal Declarada",
        options=opcoes_dropdown,
        icon=ft.icons.LAYERS,
        width=380,
        on_change=monitorar_dropdown_carga
    )
    
    switch_docs = ft.Switch(
        label="Possui Documentos de Liberação Alfandegária?",
        value=False
    )
    
    # --- PROCESSO DE VALIDAÇÃO E SUBMISSÃO ---
    def processar_submissao_cadastro(e):
        # Reset de erros visuais anteriores
        txt_imo.error_text = None
        txt_nome_navio.error_text = None
        txt_capitao.error_text = None
        txt_companhia.error_text = None
        txt_peso.error_text = None
        dd_produto_carga.error_text = None
        txt_descricao_manual.error_text = None
        
        erros_detectados = False
        
        # 1. Validação do IMO (Exatamente 7 dígitos numéricos)
        imo_val = txt_imo.value.strip()
        if not imo_val or len(imo_val) != 7:
            txt_imo.error_text = "O IMO deve conter exatamente 7 números."
            erros_detectados = True
            
        # 2. Validações de campos de texto obrigatórios baseados no padrão regex
        campos_texto = [
            (txt_nome_navio, "O nome do navio é obrigatório."),
            (txt_capitao, "O nome do capitão é obrigatório."),
            (txt_companhia, "A companhia é obrigatória.")
        ]
        
        for campo, msg_erro in campos_texto:
            valor = campo.value.strip()
            if not valor:
                campo.error_text = msg_erro
                erros_detectados = True
            elif not re.fullmatch(REGEX_VALIDACAO, valor):
                campo.error_text = "Contém caracteres inválidos."
                erros_detectados = True

        # 3. Validação do Peso (Deve ser Integer estrito para o SQLite)
        peso_val = txt_peso.value.strip()
        peso_int = 0
        if not peso_val:
            txt_peso.error_text = "O peso é obrigatório."
            erros_detectados = True
        else:
            try:
                peso_int = int(peso_val)
                if peso_int <= 0:
                    txt_peso.error_text = "O peso deve ser maior que zero."
                    erros_detectados = True
            except ValueError:
                txt_peso.error_text = "Insira um número inteiro válido."
                erros_detectados = True
                
        # 4. Validação da Seleção da Carga
        if not dd_produto_carga.value:
            dd_produto_carga.error_text = "Selecione o tipo de carga."
            erros_detectados = True
        elif dd_produto_carga.value == "OUTROS" and not txt_descricao_manual.value.strip():
            txt_descricao_manual.error_text = "Especifique a descrição da carga."
            erros_detectados = True
            
        if erros_detectados:
            page.update()
            return

        # --- PROCESSAMENTO LOGÍSTICO COMPATÍVEL COM O BACKEND ---
        # Concatena o prefixo padrão "IMO" conforme esperado na base de dados
        imo_formatado = f"IMO{imo_val}"
        
        if dd_produto_carga.value == "OUTROS":
            carga_desc = txt_descricao_manual.value.strip()
            categoria = "OUTROS_PENDENTE"
            eh_perecivel = False
        else:
            carga_desc = dd_produto_carga.value
            categoria = MAPA_CARGAS_SISTEMA[carga_desc]
            # Alinhamento matemático com ord_propriety.py: URGENTE, ALTA e BAIXA são True
            eh_perecivel = categoria in ['URGENTE_PERECIVEL', 'ALTA_PERECIBILIDADE', 'BAIXA_PERECIBILIDADE']

        # Persistência atômica no banco de dados através da Session
        try:
            with Session(engine_bd) as session:
                solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=txt_nome_navio.value.strip().upper(),
                    capitao=txt_capitao.value.strip(),
                    companhia=txt_companhia.value.strip(),
                    carga_desc=carga_desc,
                    categoria=categoria,
                    peso=peso_int,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=switch_docs.value
                )
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Sucesso! Navio {txt_nome_navio.value.upper()} ({imo_formatado}) registrado como PENDENTE."),
                bgcolor=ft.colors.GREEN_700
            )
            page.snack_bar.open = True
            
            # Reset de campos pós-sucesso
            txt_imo.value = ""
            txt_nome_navio.value = ""
            txt_capitao.value = ""
            txt_companhia.value = ""
            txt_peso.value = ""
            dd_produto_carga.value = None
            txt_descricao_manual.value = ""
            txt_descricao_manual.visible = False
            switch_docs.value = False
            
        except Exception as erro:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro de persistência no banco: {erro}"),
                bgcolor=ft.colors.RED_700
            )
            page.snack_bar.open = True
            
        page.update()

    btn_enviar = ft.ElevatedButton(
        text="Enviar Declaração de Chegada",
        icon=ft.icons.DOCK,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.BLUE_700,
            padding=22,
            shape=ft.RoundedRectangleBorder(radius=6)
        ),
        on_click=processar_submissao_cadastro
    )

    # --- MONTAGEM E RETORNO DO CONTAINER ---
    return ft.Container(
        content=ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.icons.ANCHOR, color=ft.colors.BLUE_400, size=28),
                            ft.Text("Portal da Tripulação - Pré-Cadastro", size=20, weight=ft.FontWeight.BOLD),
                        ], spacing=8),
                        ft.Text("Preencha as informações do manifesto de carga para dar entrada na fila de auditoria.", color=ft.colors.GREY_400, size=13),
                        ft.Divider(height=15, color=ft.colors.BLUE_900),
                        
                        ft.Row([txt_imo, txt_nome_navio], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([txt_capitao, txt_companhia], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([dd_produto_carga, txt_peso], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        txt_descricao_manual,
                        ft.Container(padding=ft.padding.only(top=5, bottom=5), content=switch_docs),
                        ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                        ft.Row([btn_enviar], alignment=ft.MainAxisAlignment.CENTER)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    spacing=12
                ),
                padding=24
            ),
            elevation=10
        ),
        width=630,
        padding=10
    )

if __name__ == "__main__":
    engine_teste = create_engine("sqlite:///porto.db")
    
    def main(page: ft.Page):
        page.title = "Terminal Portuário - Balcão Web"
        page.theme_mode = ft.ThemeMode.DARK
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.scroll = "adaptive"
        
        page.add(obter_tela_formulario(page, engine_teste))
        
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
