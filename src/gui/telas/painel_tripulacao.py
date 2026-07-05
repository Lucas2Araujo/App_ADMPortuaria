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
from gui.telas.painel_adm import validar_formulario_navio



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
    )

    txt_nome_navio = ft.TextField(
        label="Nome da Embarcação",
        hint_text="Ex: ESTRELA DO MAR",
        prefix_icon=ft.Icons.DIRECTIONS_BOAT,
    )

    txt_capitao = ft.TextField(
        label="Nome do Capitão",
        hint_text="Ex: Cap. Amilcar Silva",
        prefix_icon=ft.Icons.PERSON,
    )

    txt_companhia = ft.TextField(
        label="Companhia / Armador",
        hint_text="Ex: Transatlântica Logística",
        prefix_icon=ft.Icons.BUSINESS,
    )

    txt_peso = ft.TextField(
        label="Peso Total (Toneladas)",
        hint_text="Ex: 45",
        prefix_icon=ft.Icons.SCALE,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    dd_produto_carga = ft.Dropdown(
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

    switch_docs = ft.Switch(
        label="Possui Documentos de Liberação Alfandegária?",
        value=False,
        active_color=ft.Colors.CYAN_700,
    )

    async def processar_submissao_cadastro(e):
        erros = validar_formulario_navio(
            imo=txt_imo.value or "",
            nome=txt_nome_navio.value or "",
            capitao=txt_capitao.value or "",
            companhia=txt_companhia.value or "",
            peso=txt_peso.value or "",
            categoria=dd_produto_carga.value or "",
        )

        txt_imo.error_text = erros.get("imo")
        txt_nome_navio.error_text = erros.get("nome")
        txt_capitao.error_text = erros.get("capitao")
        txt_companhia.error_text = erros.get("companhia")
        txt_peso.error_text = erros.get("peso")
        dd_produto_carga.error_text = erros.get("categoria")

        if erros:
            page.update()
            return

        imo_formatado = f"IMO{txt_imo.value.strip()}"
        peso = int(txt_peso.value.strip())

        try:
            eh_perecivel = dd_produto_carga.value in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
            ]
            async with obter_sessao_async() as session:
                await solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=(txt_nome_navio.value or "").strip().upper(),
                    capitao=(txt_capitao.value or "").strip(),
                    companhia=(txt_companhia.value or "").strip(),
                    carga_desc=f"Carga: {dd_produto_carga.value}",
                    categoria=dd_produto_carga.value,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=switch_docs.value,
                )

            page.snack_bar = ft.SnackBar(
                ft.Text(
                    f"Sucesso! Navio {(txt_nome_navio.value or '').upper()} "
                    f"({imo_formatado}) registrado como PENDENTE."
                ),
                bgcolor=ft.Colors.GREEN_700,
            )
            page.snack_bar.open = True

            txt_imo.value = ""
            txt_nome_navio.value = ""
            txt_capitao.value = ""
            txt_companhia.value = ""
            txt_peso.value = ""
            dd_produto_carga.value = None
            switch_docs.value = False

        except Exception as erro:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro de persistência no banco: {erro}"),
                bgcolor=ft.Colors.RED_700,
            )
            page.snack_bar.open = True

        page.update()

    btn_enviar = ft.ElevatedButton(
        "Enviar Declaração de Chegada",
        icon=ft.Icons.DOCK,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_900,
            padding=22,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=processar_submissao_cadastro,
    )

    return ft.Container(
        padding=30,
        expand=True,
        alignment=ft.Alignment.TOP_LEFT,
        content=ft.Card(
            elevation=4,
            shape=ft.RoundedRectangleBorder(radius=12),
            content=ft.Container(
                padding=40,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ANCHOR,
                                    color=ft.Colors.BLUE_900,
                                    size=36,
                                ),
                                ft.Text(
                                    "Portal da Tripulação - Pré-Cadastro",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Text(
                            "Preencha as informações do manifesto de carga para dar "
                            "entrada na fila de auditoria.",
                            size=14,
                        ),
                        ft.Divider(height=25, color=ft.Colors.CYAN_700),
                        ft.ResponsiveRow(
                            [
                                ft.Column(col={"sm": 12, "md": 6}, controls=[txt_imo]),
                                ft.Column(col={"sm": 12, "md": 6}, controls=[txt_nome_navio]),
                                ft.Column(col={"sm": 12, "md": 6}, controls=[txt_capitao]),
                                ft.Column(col={"sm": 12, "md": 6}, controls=[txt_companhia]),
                                ft.Column(col={"sm": 12, "md": 6}, controls=[dd_produto_carga]),
                                ft.Column(col={"sm": 12, "md": 6}, controls=[txt_peso]),
                            ],
                            run_spacing=15,
                        ),
                        ft.Container(
                            padding=ft.Padding(top=15, bottom=15, left=0, right=0),
                            content=switch_docs,
                        ),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        ft.Row(
                            [btn_enviar],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    spacing=10,
                ),
            ),
        ),
    )
