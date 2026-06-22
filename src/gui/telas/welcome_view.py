import flet as ft

def obter_view(page: ft.Page, navigate=None):
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.DIRECTIONS_BOAT_FILLED, size=80, color=ft.Colors.BLUE_GREY_700),
                ft.Text("Bem-vindo ao AdminPort", size=32, weight=ft.FontWeight.BOLD),
                ft.Text("Selecione uma opção abaixo ou no menu lateral para começar.", size=16),
                ft.Divider(color=ft.Colors.TRANSPARENT, height=20),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Painel ADM", 
                            icon=ft.Icons.DASHBOARD, 
                            on_click=lambda _: navigate("adm") if navigate else None
                        ),
                        ft.ElevatedButton(
                            "Fila de Atracação", 
                            icon=ft.Icons.FORMAT_LIST_NUMBERED, 
                            on_click=lambda _: navigate("fila") if navigate else None
                        ),
                        ft.ElevatedButton(
                            "Tripulação", 
                            icon=ft.Icons.ADD_CIRCLE, 
                            on_click=lambda _: navigate("tripulacao") if navigate else None
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True
    )