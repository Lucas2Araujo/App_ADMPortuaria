"""
Tela do Portal da Tripulação — Pré-Cadastro de Navios.

Formulário para a tripulação (capitão) declarar a chegada de uma embarcação,
preenchendo os dados do manifesto de carga para dar entrada na fila de auditoria.
"""

import re
import os
import sys
import flet as ft
from cad import obter_sessao_async

diretorio_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from controller_cadastros import solicitar_pre_cadastro
from gui.telas.adm.gerenciar import validar_formulario_navio
import gui.compat


def sanitizar_texto(texto: str) -> str:
    if not texto:
        return ""
    # Remove tags HTML simples
    texto = re.sub(r"<[^>]*>", "", texto)
    # Remove aspas simples, aspas duplas, ponto-e-vírgula e barras invertidas
    texto = texto.replace("'", "").replace('"', "").replace(";", "").replace("\\", "")
    return texto.strip()


def obter_view(page: ft.Page):
    """
    Retorna o componente de formulário do Portal da Tripulação,
    aderente às assinaturas de função e modelos ORM do ecossistema.
    """

    txt_imo = ft.TextField(
        label="Número IMO (7 dígitos numéricos)",
        hint_text="Ex: 9593505",
        max_length=7,
        prefix_icon=ft.Icons.NUMBERS,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=ft.Colors.OUTLINE,
    )

    txt_nome_navio = ft.TextField(
        label="Nome da Embarcação",
        hint_text="Ex: ESTRELA DO MAR",
        prefix_icon=ft.Icons.DIRECTIONS_BOAT,
        border_color=ft.Colors.OUTLINE,
        max_length=100,
    )

    txt_capitao = ft.TextField(
        label="Nome do Capitão",
        hint_text="Ex: Cap. Amilcar Silva",
        prefix_icon=ft.Icons.PERSON,
        border_color=ft.Colors.OUTLINE,
        max_length=100,
    )

    txt_companhia = ft.TextField(
        label="Companhia / Armador",
        hint_text="Ex: Transatlântica Logística",
        prefix_icon=ft.Icons.BUSINESS,
        border_color=ft.Colors.OUTLINE,
        max_length=100,
    )

    txt_peso = ft.TextField(
        label="Peso Total (Toneladas)",
        hint_text="Ex: 45",
        prefix_icon=ft.Icons.SCALE,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=ft.Colors.OUTLINE,
        max_length=10,
    )

    dd_produto_carga = ft.Dropdown(
        label="Categoria da Carga",
        leading_icon=ft.Icons.CATEGORY,
        border_color=ft.Colors.OUTLINE,
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
            ft.dropdown.Option(
                key="OUTROS_PENDENTE", text="Outros (Especificar manualmente)"
            ),
        ],
    )

    txt_carga_customizada = ft.TextField(
        label='Descrição da Carga (Obrigatório para "Outros", opcional para demais)',
        border_color=ft.Colors.OUTLINE,
        max_length=500,
        multiline=True,
        min_lines=2,
        max_lines=5,
        hint_text="Descreva a carga em até 500 caracteres",
        expand=True,
    )

    container_carga_custom = ft.Container(
        content=txt_carga_customizada,
        visible=True,
        expand=True,
    )

    switch_docs = ft.Switch(
        label="Possui Documentos de Liberação Alfandegária?",
        value=False,
        active_color=ft.Colors.CYAN_700,
    )

    def _exibir_mensagem(mensagem: str, cor: str):
        page.snack_bar = ft.SnackBar(ft.Text(mensagem), bgcolor=cor)
        page.snack_bar.open = True

    def _limpar_formulario():
        txt_imo.value = ""
        txt_nome_navio.value = ""
        txt_capitao.value = ""
        txt_companhia.value = ""
        txt_peso.value = ""
        dd_produto_carga.value = None
        txt_carga_customizada.value = ""
        switch_docs.value = False

    def _atualizar_erros_ui(erros: dict):
        txt_imo.error_text = erros.get("imo")
        txt_nome_navio.error_text = erros.get("nome")
        txt_capitao.error_text = erros.get("capitao")
        txt_companhia.error_text = erros.get("companhia")
        txt_peso.error_text = erros.get("peso")
        dd_produto_carga.error_text = erros.get("categoria")

    def _validar_carga_custom(carga_custom_limpo: str, erros: dict):
        txt_carga_customizada.error_text = None
        if dd_produto_carga.value == "OUTROS_PENDENTE":
            if not carga_custom_limpo:
                txt_carga_customizada.error_text = (
                    "A descrição da carga é obrigatória para a categoria Outros."
                )
                erros["categoria"] = "A descrição da carga é obrigatória."
            elif len(carga_custom_limpo) > 500:
                txt_carga_customizada.error_text = (
                    "A descrição deve ter no máximo 500 caracteres."
                )
                erros["categoria"] = "Descrição muito longa."

    def _preparar_dados_carga(carga_custom_limpo: str):
        valor_dd = dd_produto_carga.value
        if valor_dd == "OUTROS_PENDENTE":
            return carga_custom_limpo, False, "OUTROS_PENDENTE"
        eh_perecivel = valor_dd in [
            "URGENTE_PERECIVEL",
            "ALTA_PERECIBILIDADE",
            "BAIXA_PERECIBILIDADE",
        ]
        return f"Carga: {valor_dd}", eh_perecivel, valor_dd

    async def _submeter_cadastro(
        imo_limpo,
        nome_limpo,
        capitao_limpo,
        companhia_limpo,
        peso_limpo,
        carga_custom_limpo,
    ):
        imo_formatado = f"IMO{imo_limpo}"
        peso = int(peso_limpo)
        carga_desc, eh_perecivel, categoria = _preparar_dados_carga(carga_custom_limpo)

        try:
            async with obter_sessao_async() as session:
                await solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=nome_limpo.upper(),
                    capitao=capitao_limpo,
                    companhia=companhia_limpo,
                    carga_desc=carga_desc,
                    categoria=categoria,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=switch_docs.value,
                )

            _exibir_mensagem(
                f"Sucesso! Navio {nome_limpo.upper()} ({imo_formatado}) registrado como PENDENTE.",
                ft.Colors.GREEN_700,
            )
            _limpar_formulario()

        except Exception as erro:
            _exibir_mensagem(
                f"Erro de persistência no banco: {erro}", ft.Colors.RED_700
            )

    async def processar_submissao_cadastro(e):
        imo_limpo = sanitizar_texto(txt_imo.value)
        nome_limpo = sanitizar_texto(txt_nome_navio.value)
        capitao_limpo = sanitizar_texto(txt_capitao.value)
        companhia_limpo = sanitizar_texto(txt_companhia.value)
        peso_limpo = sanitizar_texto(txt_peso.value)
        carga_custom_limpo = sanitizar_texto(txt_carga_customizada.value)
        categoria_selecionada = str(dd_produto_carga.value or "")

        erros = validar_formulario_navio(
            imo=imo_limpo,
            nome=nome_limpo,
            capitao=capitao_limpo,
            companhia=companhia_limpo,
            peso=peso_limpo,
            categoria=categoria_selecionada,
        )

        _validar_carga_custom(carga_custom_limpo, erros)
        _atualizar_erros_ui(erros)

        if erros:
            page.update()
            return

        await _submeter_cadastro(
            imo_limpo,
            nome_limpo,
            capitao_limpo,
            companhia_limpo,
            peso_limpo,
            carga_custom_limpo,
        )
        page.update()

    btn_enviar = ft.Button(
        "Enviar Declaração de Chegada",
        icon=ft.Icons.DOCK,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor="#0d2b4e",
            padding=22,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=processar_submissao_cadastro,
    )

    # Linha com dropdown (meia largura) + campo descrição "Outros" (meia largura, aparece dinamicamente)
    linha_categoria = ft.Row(
        controls=[
            ft.Container(content=dd_produto_carga, expand=True),
            container_carga_custom,
        ],
        spacing=20,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    # Linha do peso fica na mesma Row mas ocupa apenas metade via Container com largura fixa
    linha_peso = ft.Row(
        controls=[
            ft.Container(content=txt_peso, width=340),
        ],
        spacing=20,
    )

    return ft.Container(
        padding=40,
        expand=True,
        alignment=ft.Alignment(0, -1),
        content=ft.Container(
            width=800,
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=12,
            padding=40,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.ANCHOR, color=ft.Colors.ON_SURFACE, size=36
                            ),
                            ft.Text(
                                "Portal da Tripulação - Pré-Cadastro",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE,
                            ),
                        ],
                        spacing=12,
                    ),
                    ft.Text(
                        "Preencha as informações do manifesto de carga para dar "
                        "entrada na fila de auditoria.",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Divider(height=30, color=ft.Colors.OUTLINE_VARIANT),
                    ft.Row([txt_imo, txt_nome_navio], spacing=20),
                    ft.Row([txt_capitao, txt_companhia], spacing=20),
                    linha_categoria,
                    linha_peso,
                    ft.Container(
                        padding=ft.padding.only(top=15, bottom=15),
                        content=switch_docs,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        [ft.Container(content=btn_enviar, expand=True)],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=10,
            ),
        ),
    )
