import flet as ft
def main(page: ft.Page):
    try:
        txt_imo = ft.TextField(
            label="Número IMO",
            hint_text="Ex: 9593505",
            max_length=7,
            icon=ft.Icons.NUMBERS,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=290,
        )
        print("txt_imo OK")
    except Exception as e:
        print("txt_imo Error:", e)

    try:
        txt_descricao_manual = ft.TextField(
            label="Especifique a Carga",
            hint_text="Ex: Maquinário Industrial Agrícola",
            visible=False,
            icon=ft.Icons.DESCRIPTION,
            multiline=True,
            min_lines=2,
        )
        print("txt_descricao_manual OK")
    except Exception as e:
        print("txt_descricao_manual Error:", e)

    try:
        dd_produto_carga = ft.Dropdown(
            label="Carga Principal Declarada",
            options=[ft.dropdown.Option("Teste")],
            icon=ft.Icons.LAYERS,
            width=380,
        )
        print("dd_produto_carga OK")
    except Exception as e:
        print("dd_produto_carga Error:", e)

    try:
        switch_docs = ft.Switch(
            label="Possui Documentos de Liberação Alfandegária?",
            value=False,
        )
        print("switch_docs OK")
    except Exception as e:
        print("switch_docs Error:", e)

    try:
        btn_enviar = ft.ElevatedButton(
            text="Enviar Declaração de Chegada",
            icon=ft.Icons.DOCK,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
                padding=22,
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
        )
        print("btn_enviar OK")
    except Exception as e:
        print("btn_enviar Error:", e)

ft.app(target=main)
