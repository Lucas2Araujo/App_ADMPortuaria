import flet as ft
import gui.compat


def obter_view(page: ft.Page, on_login_success):
    # Definindo tema inicial com base na página (persistência)
    eh_escuro = page.theme_mode == ft.ThemeMode.DARK

    senha_field = ft.TextField(
        label="Código de Acesso ADM",
        password=True,
        can_reveal_password=True,
        width=300,
        prefix_icon=ft.Icons.LOCK,
        border_color="#cbd5e1",
        color="#e2e8f0" if eh_escuro else ft.Colors.BLACK,
        cursor_color="#e2e8f0" if eh_escuro else ft.Colors.BLACK,
        label_style=ft.TextStyle(color="#94a3b8"),
        on_submit=lambda e: verificar_senha(),
    )

    def verificar_senha(e=None):
        if senha_field.value == "admin123":
            dialogo_senha.open = False
            page.update()
            on_login_success("admin")
        else:
            senha_field.error_text = "Senha incorreta!"
            page.update()

    titulo_dialogo = ft.Text(
        "Acesso Administrativo",
        color="#e2e8f0" if eh_escuro else ft.Colors.BLUE_GREY_900,
    )

    dialogo_senha = ft.AlertDialog(
        bgcolor="#1e293b" if eh_escuro else ft.Colors.WHITE,
        title=titulo_dialogo,
        content=senha_field,
        actions=[
            ft.TextButton(
                "Cancelar",
                on_click=lambda e: fechar_dialogo(),
                style=ft.ButtonStyle(color="#94a3b8"),
            ),
            ft.ElevatedButton(
                "Entrar",
                on_click=verificar_senha,
                bgcolor="#3b82f6",
                color=ft.Colors.WHITE,
            ),
        ],
    )

    def fechar_dialogo():
        dialogo_senha.open = False
        senha_field.value = ""
        senha_field.error_text = None
        page.update()

    def abrir_dialogo_admin(e):
        page.overlay.append(dialogo_senha)
        dialogo_senha.open = True
        page.update()

    texto_titulo = ft.Text(
        "Terminal Portuário S/A",
        size=24,
        weight=ft.FontWeight.BOLD,
        color="#f8fafc" if eh_escuro else ft.Colors.BLUE_GREY_900,
    )

    card_fundo = ft.Container(
        bgcolor="#1e293b" if eh_escuro else ft.Colors.WHITE,
        border=ft.border.all(1, "#334155" if eh_escuro else "#e2e8f0"),
        border_radius=16,
        padding=40,
        width=420,
        content=ft.Column(
            [
                ft.Icon(ft.Icons.DIRECTIONS_BOAT_FILLED, size=80, color="#3b82f6"),
                texto_titulo,
                ft.Text("Selecione seu perfil de acesso", size=14, color="#94a3b8"),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "Representante / Tripulação",
                    icon=ft.Icons.ANCHOR,
                    width=320,
                    style=ft.ButtonStyle(
                        padding=20,
                        bgcolor={
                            ft.ControlState.HOVERED: "#2563eb",
                            ft.ControlState.DEFAULT: "#3b82f6",
                        },
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        mouse_cursor=ft.MouseCursor.CLICK,
                    ),
                    on_click=lambda e: on_login_success("tripulacao"),
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.OutlinedButton(
                    "Administração do Porto",
                    icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                    width=320,
                    style=ft.ButtonStyle(
                        padding=20,
                        color={
                            ft.ControlState.HOVERED: "#cbd5e1",
                            ft.ControlState.DEFAULT: "#94a3b8",
                        },
                        side={
                            ft.ControlState.HOVERED: ft.BorderSide(1, "#cbd5e1"),
                            ft.ControlState.DEFAULT: ft.BorderSide(1, "#94a3b8"),
                        },
                        shape=ft.RoundedRectangleBorder(radius=8),
                        mouse_cursor=ft.MouseCursor.CLICK,
                    ),
                    on_click=abrir_dialogo_admin,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
    )

    container_fundo = ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor="#0f172a" if eh_escuro else ft.Colors.BLUE_GREY_50,
        content=card_fundo,
    )

    def alternar_tema(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            btn_tema.icon = ft.Icons.WB_SUNNY
            btn_tema.icon_color = ft.Colors.WHITE

            # Atualiza cores pro Dark Mode
            container_fundo.bgcolor = "#0f172a"
            card_fundo.bgcolor = "#1e293b"
            card_fundo.border = ft.border.all(1, "#334155")
            texto_titulo.color = "#f8fafc"

            dialogo_senha.bgcolor = "#1e293b"
            titulo_dialogo.color = "#e2e8f0"
            senha_field.color = "#e2e8f0"
            senha_field.cursor_color = "#e2e8f0"
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            btn_tema.icon = ft.Icons.NIGHTS_STAY
            btn_tema.icon_color = ft.Colors.BLUE_GREY_900

            # Atualiza cores pro Light Mode
            container_fundo.bgcolor = ft.Colors.BLUE_GREY_50
            card_fundo.bgcolor = ft.Colors.WHITE
            card_fundo.border = ft.border.all(1, "#e2e8f0")
            texto_titulo.color = ft.Colors.BLUE_GREY_900

            dialogo_senha.bgcolor = ft.Colors.WHITE
            titulo_dialogo.color = ft.Colors.BLUE_GREY_900
            senha_field.color = ft.Colors.BLACK
            senha_field.cursor_color = ft.Colors.BLACK

        page.update()

    btn_tema = ft.IconButton(
        icon=ft.Icons.WB_SUNNY if eh_escuro else ft.Icons.NIGHTS_STAY,
        icon_color=ft.Colors.WHITE if eh_escuro else ft.Colors.BLUE_GREY_900,
        on_click=alternar_tema,
        tooltip="Alternar Tema",
    )

    login_view = ft.Stack(
        [container_fundo, ft.Container(content=btn_tema, top=20, right=20)], expand=True
    )

    return login_view
