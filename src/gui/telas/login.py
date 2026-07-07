import flet as ft


class LoginViewManager:
    def __init__(self, page: ft.Page, on_login_success):
        self.page = page
        self.on_login_success = on_login_success
        self.eh_escuro = page.theme_mode == ft.ThemeMode.DARK
        self._build()

    def verificar_senha(self, e=None):
        if self.senha_field.value == "admin123":
            self.dialogo_senha.open = False
            self.page.update()
            self.on_login_success("admin")
        else:
            self.senha_field.error_text = "Senha incorreta!"
            self.page.update()

    def fechar_dialogo(self, e=None):
        self.dialogo_senha.open = False
        self.senha_field.value = ""
        self.senha_field.error_text = None
        self.page.update()

    def abrir_dialogo_admin(self, e):
        self.page.overlay.append(self.dialogo_senha)
        self.dialogo_senha.open = True
        self.page.update()

    def alternar_tema(self, e):
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.btn_tema.icon = ft.Icons.WB_SUNNY
            self.btn_tema.icon_color = ft.Colors.WHITE

            self.container_fundo.bgcolor = "#0f172a"
            self.card_fundo.bgcolor = "#1e293b"
            self.card_fundo.border = ft.border.all(1, "#334155")
            self.texto_titulo.color = "#f8fafc"

            self.dialogo_senha.bgcolor = "#1e293b"
            self.titulo_dialogo.color = "#e2e8f0"
            self.senha_field.color = "#e2e8f0"
            self.senha_field.cursor_color = "#e2e8f0"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.btn_tema.icon = ft.Icons.NIGHTS_STAY
            self.btn_tema.icon_color = ft.Colors.BLUE_GREY_900

            self.container_fundo.bgcolor = ft.Colors.BLUE_GREY_50
            self.card_fundo.bgcolor = ft.Colors.WHITE
            self.card_fundo.border = ft.border.all(1, "#e2e8f0")
            self.texto_titulo.color = ft.Colors.BLUE_GREY_900

            self.dialogo_senha.bgcolor = ft.Colors.WHITE
            self.titulo_dialogo.color = ft.Colors.BLUE_GREY_900
            self.senha_field.color = ft.Colors.BLACK
            self.senha_field.cursor_color = ft.Colors.BLACK

        self.page.update()

    def _build(self):
        self.senha_field = ft.TextField(
            label="Código de Acesso ADM",
            password=True,
            can_reveal_password=True,
            width=300,
            prefix_icon=ft.Icons.LOCK,
            border_color="#cbd5e1",
            color="#e2e8f0" if self.eh_escuro else ft.Colors.BLACK,
            cursor_color="#e2e8f0" if self.eh_escuro else ft.Colors.BLACK,
            label_style=ft.TextStyle(color="#94a3b8"),
            on_submit=self.verificar_senha,
        )

        self.titulo_dialogo = ft.Text(
            "Acesso Administrativo",
            color="#e2e8f0" if self.eh_escuro else ft.Colors.BLUE_GREY_900,
        )

        self.dialogo_senha = ft.AlertDialog(
            bgcolor="#1e293b" if self.eh_escuro else ft.Colors.WHITE,
            title=self.titulo_dialogo,
            content=self.senha_field,
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=self.fechar_dialogo,
                    style=ft.ButtonStyle(color="#94a3b8"),
                ),
                ft.Button(
                    "Entrar",
                    on_click=self.verificar_senha,
                    bgcolor="#3b82f6",
                    color=ft.Colors.WHITE,
                ),
            ],
        )

        self.texto_titulo = ft.Text(
            "Terminal Portuário S/A",
            size=24,
            weight=ft.FontWeight.BOLD,
            color="#f8fafc" if self.eh_escuro else ft.Colors.BLUE_GREY_900,
        )

        self.card_fundo = ft.Container(
            bgcolor="#1e293b" if self.eh_escuro else ft.Colors.WHITE,
            border=ft.border.all(1, "#334155" if self.eh_escuro else "#e2e8f0"),
            border_radius=16,
            padding=40,
            width=420,
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.DIRECTIONS_BOAT_FILLED, size=80, color="#3b82f6"),
                    self.texto_titulo,
                    ft.Text("Selecione seu perfil de acesso", size=14, color="#94a3b8"),
                    ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                    ft.Button(
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
                        on_click=lambda e: self.on_login_success("tripulacao"),
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
                        on_click=self.abrir_dialogo_admin,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
        )

        self.container_fundo = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            bgcolor="#0f172a" if self.eh_escuro else ft.Colors.BLUE_GREY_50,
            content=self.card_fundo,
        )

        self.btn_tema = ft.IconButton(
            icon=ft.Icons.WB_SUNNY if self.eh_escuro else ft.Icons.NIGHTS_STAY,
            icon_color=ft.Colors.WHITE if self.eh_escuro else ft.Colors.BLUE_GREY_900,
            on_click=self.alternar_tema,
            tooltip="Alternar Tema",
        )

        self.view = ft.Stack(
            [
                self.container_fundo,
                ft.Container(content=self.btn_tema, top=20, right=20),
            ],
            expand=True,
        )


def obter_view(page: ft.Page, on_login_success):
    manager = LoginViewManager(page, on_login_success)
    return manager.view
