import flet as ft
import gui.compat
import re
from cad import obter_sessao_async
from controller_cadastros import (
    solicitar_pre_cadastro,
    editar_registro_navio,
    excluir_registro_navio,
    obter_todos_navios_dto,
)


def _validar_texto_comum(valor: str, msg_obrigatorio: str) -> str:
    valor = valor.strip()
    if not valor:
        return msg_obrigatorio
    if not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", valor):
        return "Contém caracteres inválidos."
    return ""


def _validar_peso(peso: str) -> str:
    peso = peso.strip()
    if not peso:
        return "O peso é obrigatório."
    try:
        if int(peso) <= 0:
            return "O peso deve ser maior que zero."
    except ValueError:
        return "Insira um número inteiro válido."
    return ""


def validar_formulario_navio(
    imo: str, nome: str, capitao: str, companhia: str, peso: str, categoria: str
) -> dict[str, str]:
    erros: dict[str, str] = {}

    imo = imo.strip()
    if not imo:
        erros["imo"] = "O IMO é obrigatório."
    elif not imo.isdigit() or len(imo) != 7:
        erros["imo"] = "O IMO deve conter exatamente 7 números."

    if erro_nome := _validar_texto_comum(nome, "O nome do navio é obrigatório."):
        erros["nome"] = erro_nome

    if erro_capitao := _validar_texto_comum(
        capitao, "O nome do capitão é obrigatório."
    ):
        erros["capitao"] = erro_capitao

    if erro_companhia := _validar_texto_comum(companhia, "A companhia é obrigatória."):
        erros["companhia"] = erro_companhia

    if erro_peso := _validar_peso(peso):
        erros["peso"] = erro_peso

    if not categoria:
        erros["categoria"] = "Selecione uma categoria de carga."

    return erros


class GerenciarView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self._page = page

        # State fields
        self.navio_selecionado = None
        self._todos_navios_cache = []
        self._last_navios_hash = None

        self.edit_nome = ft.TextField(label="Nome do Navio", width=300)
        self.edit_capitao = ft.TextField(label="Nome do Capitão", width=300)
        self.edit_companhia = ft.TextField(label="Companhia", width=300)
        self.btn_salvar_edicao = ft.ElevatedButton(
            "Salvar Alterações",
            icon=ft.Icons.SAVE,
            on_click=lambda e: self._page.run_task(self.submit_edicao_navio),
        )
        self.loading_indicator = ft.ProgressRing(visible=False)

        self.tabela_navios = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text(
                        "ID Navio (IMO)",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Nome",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Capitão",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Companhia",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Status",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Ações",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                ),
            ],
            rows=[],
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGH,
            data_row_min_height=60,
            data_row_max_height=60,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            horizontal_margin=20,
            column_spacing=30,
        )

        self.imo_para_excluir = None
        self.txt_msg_exclusao = ft.Text("")

        self.dialogo_confirmar_exclusao = ft.AlertDialog(
            modal=True,
            title=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.DELETE, color="#dc2626", size=24),
                        width=48,
                        height=48,
                        bgcolor="#fee2e2",
                        border_radius=24,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        "Confirmar Exclusão",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=self.txt_msg_exclusao,
                alignment=ft.alignment.center,
                padding=ft.padding.all(10),
            ),
            actions=[
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "Cancelar", color="#5a7494", weight=ft.FontWeight.W_600
                            ),
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            border=ft.border.all(1, "#dde3ec"),
                            ink=True,
                            on_click=self.fechar_modal_exclusao,
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#f0f4f8" if e.data == "true" else "transparent",
                                ),
                                e.control.update(),
                            ),
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Excluir", color="white", weight=ft.FontWeight.W_600
                            ),
                            bgcolor="#dc2626",
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            ink=True,
                            on_click=lambda e: self._page.run_task(
                                self.processar_exclusao_backend
                            ),
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#b91c1c" if e.data == "true" else "#dc2626",
                                ),
                                e.control.update(),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.txt_msg_exclusao.color = ft.Colors.ON_SURFACE_VARIANT
        self.txt_msg_exclusao.size = 14
        self.txt_msg_exclusao.text_align = ft.TextAlign.CENTER

        self.campo_imo = ft.TextField(
            label="Número IMO (ex: 1234567)",
            max_length=7,
            prefix_icon=ft.Icons.NUMBERS,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        self.campo_nome = ft.TextField(
            label="Nome do Navio", prefix_icon=ft.Icons.DIRECTIONS_BOAT
        )
        self.campo_capitao = ft.TextField(
            label="Nome do Capitão", prefix_icon=ft.Icons.PERSON
        )
        self.campo_companhia = ft.TextField(
            label="Companhia", prefix_icon=ft.Icons.BUSINESS
        )
        self.campo_peso = ft.TextField(
            label="Peso Total (Toneladas)",
            prefix_icon=ft.Icons.SCALE,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        self.campo_categoria = ft.Dropdown(
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
        self.campo_docs = ft.Switch(
            label="Possui Documentos Alfandegários?", value=False
        )

        self.campo_limite_navios = ft.Dropdown(
            label="Limite de Exibição",
            value="100",
            options=[
                ft.dropdown.Option(key="25", text="25 Navios"),
                ft.dropdown.Option(key="50", text="50 Navios"),
                ft.dropdown.Option(key="100", text="100 Navios"),
                ft.dropdown.Option(key="TODOS", text="Todos os Navios"),
            ],
            width=200,
        )
        self.campo_limite_navios.on_change = (
            lambda e: self._aplicar_filtro_navios_local()
        )

        self.txt_busca_navio = ft.TextField(
            hint_text="Buscar por nome, IMO ou companhia...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            bgcolor="#f8fafc",
            border_color="#dde3ec",
            color="#0d1f35",
            height=40,
            content_padding=ft.padding.all(10),
            expand=True,
            on_change=lambda e: self._aplicar_filtro_navios_local(),
        )

        for campo in [
            self.campo_imo,
            self.campo_nome,
            self.campo_capitao,
            self.campo_companhia,
            self.campo_peso,
            self.campo_categoria,
            self.edit_nome,
            self.edit_capitao,
            self.edit_companhia,
        ]:
            if isinstance(campo, (ft.TextField, ft.Dropdown)):
                campo.border_radius = 8

        self.modal_novo_navio = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.DIRECTIONS_BOAT, color="white", size=20
                        ),
                        width=36,
                        height=36,
                        bgcolor="#0d2b4e",
                        border_radius=8,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        "Novo Navio",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ]
            ),
            content=ft.Container(
                width=560,
                content=ft.Column(
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Column(col={"sm": 6}, controls=[self.campo_imo]),
                                ft.Column(col={"sm": 6}, controls=[self.campo_nome]),
                                ft.Column(
                                    col={"sm": 6}, controls=[self.campo_companhia]
                                ),
                                ft.Column(col={"sm": 6}, controls=[self.campo_capitao]),
                                ft.Column(
                                    col={"sm": 6}, controls=[self.campo_categoria]
                                ),
                                ft.Column(col={"sm": 6}, controls=[self.campo_peso]),
                                ft.Column(col={"sm": 12}, controls=[self.campo_docs]),
                            ],
                            run_spacing=15,
                        )
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "Cancelar", color="#5a7494", weight=ft.FontWeight.W_600
                            ),
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            border=ft.border.all(1, "#dde3ec"),
                            ink=True,
                            on_click=lambda e: self.fechar_modal_novo(),
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#f0f4f8" if e.data == "true" else "transparent",
                                ),
                                e.control.update(),
                            ),
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Salvar", color="white", weight=ft.FontWeight.W_600
                            ),
                            bgcolor="#0d2b4e",
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            ink=True,
                            on_click=lambda e: self._page.run_task(self.salvar_navio),
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#163d6e" if e.data == "true" else "#0d2b4e",
                                ),
                                e.control.update(),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                )
            ],
        )

        self.modal_editar_navio = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.EDIT, color="white", size=20),
                        width=36,
                        height=36,
                        bgcolor="#0d2b4e",
                        border_radius=8,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        "Editar Navio",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ]
            ),
            content=ft.Container(
                width=560,
                content=ft.Column(
                    [self.edit_nome, self.edit_capitao, self.edit_companhia], spacing=16
                ),
            ),
            actions=[
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "Cancelar", color="#5a7494", weight=ft.FontWeight.W_600
                            ),
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            border=ft.border.all(1, "#dde3ec"),
                            ink=True,
                            on_click=lambda e: self.fechar_edicao(),
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#f0f4f8" if e.data == "true" else "transparent",
                                ),
                                e.control.update(),
                            ),
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Salvar", color="white", weight=ft.FontWeight.W_600
                            ),
                            bgcolor="#0d2b4e",
                            padding=ft.padding.symmetric(horizontal=20, vertical=10),
                            border_radius=12,
                            ink=True,
                            on_click=lambda e: self._page.run_task(
                                self.submit_edicao_navio
                            ),
                            on_hover=lambda e: (
                                setattr(
                                    e.control,
                                    "bgcolor",
                                    "#163d6e" if e.data == "true" else "#0d2b4e",
                                ),
                                e.control.update(),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                )
            ],
        )

        self.content = ft.Container(
            padding=ft.padding.all(30),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.DIRECTIONS_BOAT_FILLED,
                                        size=32,
                                        color=ft.Colors.ON_SURFACE,
                                    ),
                                    ft.Text(
                                        "Gestão de Navios",
                                        size=26,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.ON_SURFACE,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.IconButton(
                                ft.Icons.REFRESH,
                                tooltip="Atualizar",
                                on_click=lambda e: self._page.run_task(self.atualizar),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.Container(
                                content=self.txt_busca_navio,
                                width=320,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.ADD, size=16, color="#ffffff"),
                                        ft.Text(
                                            "Novo Registro",
                                            size=14,
                                            weight=ft.FontWeight.W_600,
                                            color="#ffffff",
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                bgcolor="#0d2b4e",
                                padding=ft.padding.symmetric(
                                    horizontal=20, vertical=10
                                ),
                                border_radius=8,
                                ink=True,
                                on_click=lambda e: self.abrir_modal_novo(),
                                on_hover=lambda e: (
                                    setattr(
                                        e.control,
                                        "bgcolor",
                                        "#163d6e" if e.data == "true" else "#0d2b4e",
                                    ),
                                    e.control.update(),
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=16),
                    ft.ListView(
                        controls=[self.tabela_navios],
                        expand=True,
                    ),
                ],
                expand=True,
            ),
        )

        self._page.overlay.append(self.modal_novo_navio)
        self._page.overlay.append(self.modal_editar_navio)
        self._page.overlay.append(self.dialogo_confirmar_exclusao)

    def did_mount(self):
        """Called by Flet after this control is added to the page tree."""
        self._page.run_task(self.atualizar)

    def fechar_modal_exclusao(self, e=None):
        self.dialogo_confirmar_exclusao.open = False
        self._page.update()

    def abrir_confirmacao_exclusao(self, imo, nome):
        self.imo_para_excluir = imo
        self.txt_msg_exclusao.value = (
            f"Tem certeza que deseja excluir permanentemente o navio {nome} ({imo})?"
        )
        self.dialogo_confirmar_exclusao.open = True
        self._page.update()

    async def processar_exclusao_backend(self, e=None):
        print(f"[DEBUG] Iniciando exclusão do imo: {self.imo_para_excluir}")
        self.dialogo_confirmar_exclusao.open = False
        self._page.update()

        msg = ""
        status_cor = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                await excluir_registro_navio(session, self.imo_para_excluir)
                msg = f"Sucesso: Registro do navio ({self.imo_para_excluir}) foi excluído definitivamente."
                status_cor = ft.Colors.GREEN
                print("[DEBUG] Exclusão concluída com sucesso.")
        except Exception as err:
            msg = f"{err}"
            status_cor = ft.Colors.ORANGE
            print(f"[DEBUG] Erro na exclusão: {err}")
        finally:
            self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status_cor)
            self._page.snack_bar.open = True
            await self.atualizar()
            self._page.update()

    def fechar_edicao(self):
        self.modal_editar_navio.open = False
        self.edit_nome.value = self.edit_capitao.value = self.edit_companhia.value = ""
        self._page.update()

    def abrir_modal_novo(self):
        self.campo_imo.value = ""
        self.campo_nome.value = ""
        self.campo_capitao.value = ""
        self.campo_companhia.value = ""
        self.campo_peso.value = ""
        self.campo_categoria.value = None
        self.campo_docs.value = False
        self.modal_novo_navio.open = True
        self._page.update()

    def fechar_modal_novo(self):
        self.modal_novo_navio.open = False
        self._page.update()

    def abrir_edicao_navio(self, navio):
        self.navio_selecionado = navio
        self.edit_nome.value = navio.nome
        self.edit_capitao.value = (
            navio.nome_capitao
            if hasattr(navio, "nome_capitao")
            else getattr(navio, "capitao", "")
        )
        self.edit_companhia.value = navio.companhia
        self.modal_editar_navio.open = True
        self._page.update()

    async def submit_edicao_navio(self):
        if (
            not self.edit_nome.value
            or not self.edit_capitao.value
            or not self.edit_companhia.value
        ):
            self._page.snack_bar = ft.SnackBar(
                ft.Text("Preencha todos os campos obrigatórios!"), bgcolor=ft.Colors.RED
            )
            self._page.snack_bar.open = True
            self._page.update()
            return

        self.btn_salvar_edicao.disabled = True
        self.loading_indicator.visible = True
        self._page.update()

        msg = ""
        status = ft.Colors.RED
        try:
            async with obter_sessao_async() as session:
                await editar_registro_navio(
                    session,
                    self.navio_selecionado.imo_id,
                    self.edit_nome.value,
                    self.edit_capitao.value,
                    self.edit_companhia.value,
                )
                msg = f"Navio {self.edit_nome.value} atualizado com sucesso!"
                status = ft.Colors.GREEN
        except Exception as e:
            msg = f"Erro ao atualizar navio: {e}"
        finally:
            self._page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=status)
            self._page.snack_bar.open = True
            self.btn_salvar_edicao.disabled = False
            self.loading_indicator.visible = False
            self.modal_editar_navio.open = False
            await self.atualizar()
            self._page.update()

    async def salvar_navio(self, e=None):
        erros = validar_formulario_navio(
            imo=self.campo_imo.value or "",
            nome=self.campo_nome.value or "",
            capitao=self.campo_capitao.value or "",
            companhia=self.campo_companhia.value or "",
            peso=self.campo_peso.value or "",
            categoria=self.campo_categoria.value or "",
        )
        self.campo_imo.error_text = erros.get("imo")
        self.campo_nome.error_text = erros.get("nome")
        self.campo_capitao.error_text = erros.get("capitao")
        self.campo_companhia.error_text = erros.get("companhia")
        self.campo_peso.error_text = erros.get("peso")
        self.campo_categoria.error_text = erros.get("categoria")

        if erros:
            self._page.update()
            return

        imo_formatado = f"IMO{self.campo_imo.value.strip()}"
        peso = int(self.campo_peso.value.strip())

        try:
            eh_perecivel = self.campo_categoria.value in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
            ]
            async with obter_sessao_async() as session:
                await solicitar_pre_cadastro(
                    session=session,
                    imo=imo_formatado,
                    nome=self.campo_nome.value.strip(),
                    capitao=self.campo_capitao.value.strip(),
                    companhia=self.campo_companhia.value.strip(),
                    carga_desc=f"Carga: {self.campo_categoria.value}",
                    categoria=self.campo_categoria.value,
                    peso=peso,
                    eh_perecivel=eh_perecivel,
                    possui_documentos=self.campo_docs.value,
                )
            self._page.snack_bar = ft.SnackBar(
                ft.Text(f"Sucesso! Navio {self.campo_nome.value.strip()} registrado!"),
                bgcolor=ft.Colors.GREEN,
            )
            self._page.snack_bar.open = True

            self.campo_imo.value = self.campo_nome.value = self.campo_capitao.value = (
                self.campo_companhia.value
            ) = self.campo_peso.value = ""
            self.campo_categoria.value = None
            self.campo_docs.value = False
            self.modal_novo_navio.open = False
            await self.atualizar()
        except Exception as erro:
            self._page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro ao salvar: {erro}"), bgcolor=ft.Colors.RED
            )
            self._page.snack_bar.open = True
        self._page.update()

    def _aplicar_filtro_navios_local(self):
        if not hasattr(self, "_todos_navios_cache"):
            return

        navios = self._todos_navios_cache

        if self.campo_limite_navios.value != "TODOS":
            try:
                limite = int(self.campo_limite_navios.value)
                navios = navios[:limite]
            except ValueError:
                navios = navios[:100]

        if hasattr(self, "txt_busca_navio") and self.txt_busca_navio.value:
            busca = self.txt_busca_navio.value.lower()
            navios = [
                n
                for n in navios
                if busca in n.nome.lower()
                or busca in n.imo_id.lower()
                or busca in getattr(n, "companhia", "").lower()
            ]

        # Check if rebuild is necessary
        current_hash = hash(
            tuple(
                (
                    n.imo_id,
                    n.status,
                    n.nome,
                    getattr(n, "companhia", ""),
                    n.nome_capitao,
                )
                for n in navios
            )
        )
        if getattr(self, "_last_navios_hash", None) == current_hash:
            return

        self._last_navios_hash = current_hash

        novas_linhas_navios = []
        for navio in navios:
            capitao_nome = navio.nome_capitao

            btn_editar = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.EDIT, size=14, color="#163d6e"),
                        ft.Text(
                            "Editar",
                            size=12,
                            color="#163d6e",
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                bgcolor="transparent",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                ink=True,
                on_click=lambda e, n=navio: self.abrir_edicao_navio(n),
                on_hover=lambda e: (
                    setattr(
                        e.control,
                        "bgcolor",
                        "#e8eef6" if e.data == "true" else "transparent",
                    ),
                    e.control.update(),
                ),
            )

            btn_excluir = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.DELETE_OUTLINE, size=14, color="#dc2626"),
                        ft.Text(
                            "Excluir",
                            size=12,
                            color="#dc2626",
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                bgcolor="transparent",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                ink=True,
                on_click=lambda e, imo=navio.imo_id, nome=navio.nome: self.abrir_confirmacao_exclusao(
                    imo, nome
                ),
                on_hover=lambda e: (
                    setattr(
                        e.control,
                        "bgcolor",
                        "#fee2e2" if e.data == "true" else "transparent",
                    ),
                    e.control.update(),
                ),
            )

            if navio.status == "VALIDADO":
                status_bg = "#f0fdf4"
                status_color = "#16a34a"
            elif navio.status == "PENDENTE":
                status_bg = "#fffbeb"
                status_color = "#d97706"
            else:
                status_bg = "#f5f5f5"
                status_color = "#757575"

            novas_linhas_navios.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(
                                navio.imo_id,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                size=12,
                                weight=ft.FontWeight.W_600,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    navio.nome,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                    color=ft.Colors.ON_SURFACE,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                width=150,
                                tooltip=navio.nome,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    capitao_nome,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    size=14,
                                ),
                                width=130,
                                tooltip=capitao_nome,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    getattr(navio, "companhia", "N/A"),
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    size=14,
                                ),
                                width=160,
                                tooltip=getattr(navio, "companhia", "N/A"),
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    navio.status,
                                    color=status_color,
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                bgcolor=status_bg,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                border_radius=4,
                            )
                        ),
                        ft.DataCell(ft.Row([btn_editar, btn_excluir], spacing=8)),
                    ]
                )
            )
        self.tabela_navios.rows = novas_linhas_navios
        self._page.update()

    async def atualizar(self, e=None):
        try:
            async with obter_sessao_async() as session:
                navios = await obter_todos_navios_dto(session)
                navios.sort(key=lambda x: x.data_solicitacao, reverse=True)
                self._todos_navios_cache = navios
                self._aplicar_filtro_navios_local()
        except Exception as err:
            print(f"Erro ao carregar navios: {err}")


def obter_view(page: ft.Page):
    return GerenciarView(page)
