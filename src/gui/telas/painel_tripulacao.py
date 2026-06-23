"""
Tela do Portal da Tripulação — Pré-Cadastro de Navios.

Formulário para a tripulação (capitão) declarar a chegada de uma embarcação,
preenchendo os dados do manifesto de carga para dar entrada na fila de auditoria.
"""

import re
import os
import sys
import flet as ft
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Ajuste de sys.path idêntico ao painel_adm.py para resolver imports do src/
diretorio_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if diretorio_src not in sys.path:
    sys.path.append(diretorio_src)

from controller_cadastros import solicitar_pre_cadastro
from telas.painel_adm import validar_formulario_navio

# Engine compartilhado — mesmo padrão do painel_adm.py
db_path = os.path.join(diretorio_src, "porto.db")
engine = create_engine(f"sqlite:///{db_path}")


def obter_view(page: ft.Page):
    """
    Retorna o componente de formulário do Portal da Tripulação,
    aderente às assinaturas de função e modelos ORM do ecossistema.
    """

    # --- CONFIGURAÇÃO DOS INPUTS ---
    txt_imo = ft.TextField(
        label="Número IMO (7 dígitos numéricos)",
        hint_text="Ex: 9593505",
        max_length=7,
        icon=ft.Icons.NUMBERS,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=290,
    )

    txt_nome_navio = ft.TextField(
        label="Nome da Embarcação",
        hint_text="Ex: ESTRELA DO MAR",
        icon=ft.Icons.DIRECTIONS_BOAT,
        width=290,
    )

    txt_capitao = ft.TextField(
        label="Nome do Capitão",
        hint_text="Ex: Cap. Amilcar Silva",
        icon=ft.Icons.PERSON,
        width=290,
    )

    txt_companhia = ft.TextField(
        label="Companhia / Armador",
        hint_text="Ex: Transatlântica Logística",
        icon=ft.Icons.BUSINESS,
        width=290,
    )

    txt_peso = ft.TextField(
        label="Peso Total (Toneladas)",
        hint_text="Ex: 45",
        icon=ft.Icons.SCALE,
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
    )

    dd_produto_carga = ft.Dropdown(
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

    switch_docs = ft.Switch(
        label="Possui Documentos de Liberação Alfandegária?",
        value=False,
    )

    # --- PROCESSO DE VALIDAÇÃO E SUBMISSÃO ---
    def processar_submissao_cadastro(e):
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

        # --- PROCESSAMENTO COMPATÍVEL COM O BACKEND ---
        imo_formatado = f"IMO{txt_imo.value.strip()}"
        peso = int(txt_peso.value.strip())

        try:
            eh_perecivel = dd_produto_carga.value in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
            ]
            with Session(engine) as session:
                solicitar_pre_cadastro(
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

            # Reset de campos pós-sucesso
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
            bgcolor=ft.Colors.BLUE_700,
            padding=22,
            shape=ft.RoundedRectangleBorder(radius=6),
        ),
        on_click=processar_submissao_cadastro,
    )

    # --- MONTAGEM E RETORNO DO CONTAINER ---
    return ft.Container(
        padding=30,
        content=ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ANCHOR,
                                    color=ft.Colors.BLUE_GREY_800,
                                    size=32,
                                ),
                                ft.Text(
                                    "Portal da Tripulação - Pré-Cadastro",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Text(
                            "Preencha as informações do manifesto de carga para dar "
                            "entrada na fila de auditoria.",
                            color=ft.Colors.GREY_400,
                            size=13,
                        ),
                        ft.Divider(height=15, color=ft.Colors.BLUE_900),
                        ft.Row(
                            [txt_imo, txt_nome_navio],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [txt_capitao, txt_companhia],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [dd_produto_carga, txt_peso],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(
                            padding=ft.Padding(0, 5, 0, 5),
                            content=switch_docs,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Row(
                            [btn_enviar],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    spacing=12,
                ),
                padding=24,
            ),
            elevation=10,
        ),
        width=630,
    )
