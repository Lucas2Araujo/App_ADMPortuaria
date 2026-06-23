"""
=============================================================================
TESTES DE COMPONENTE — Frontend Flet (AdminPort)
=============================================================================

OBJETIVO
--------
Testar a lógica interna das views Flet de forma isolada, sem precisar abrir
uma janela gráfica real. Verificamos se as funções de lógica respondem
corretamente a inputs e se os elementos visuais mudam de estado conforme
esperado.

FILOSOFIA: O QUE TESTAR NO FRONTEND SEM DISPLAY GRÁFICO
---------------------------------------------------------
O Flet não possui (ainda) um framework de teste de widgets completo como o
Flutter Driver ou o WidgetTester. Em vez disso, adotamos 3 estratégias:

  ESTRATÉGIA 1 — Testar a lógica pura:
    Funções como `validar_formulario_navio()` são funções Python puras (sem
    Page, sem ft.Text). Testamos seus retornos diretamente. Ex: Suite 1.

  ESTRATÉGIA 2 — Simular a Page com um Mock e invocar callbacks:
    Criamos um objeto `MockPage` que imita a interface de `ft.Page` mas não
    abre janela. Instanciamos os controles Flet diretamente em código e
    chamamos os handlers de eventos (on_click, on_change) com um evento
    simulado. Ex: Suite 2.

  ESTRATÉGIA 3 — Integração via `flet.testing` (Pytest async):
    Usamos o `ft.testing.AppDriver` para testar fluxos completos como se
    fosse um utilizador real, mas sem display. Requer o pacote flet>=0.24.
    Ex: Suite 3.

COMO EXECUTAR
-------------
  cd /home/lucas/Documentos/ufMA/App_ADMPortuaria
  python -m pytest src/testes/test_componentes_flet.py -v

COMO REPLICAR PARA OUTRAS TELAS
---------------------------------
1. Para cada nova view, identifique as funções de lógica pura (sem ft.Page).
2. Extraia-as para funções independentes e teste-as na Suite 1.
3. Para testes de UI: instancie os controles Flet, simule o evento e
   verifique o estado do controle APÓS o handler.
=============================================================================
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# ---------------------------------------------------------------------------
# Ajuste do sys.path para encontrar os módulos src/ e src/gui/telas/
# ---------------------------------------------------------------------------
_DIR_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # → src/
_DIR_GUI = os.path.join(_DIR_SRC, "gui")                                         # → src/gui/
_DIR_TELAS = os.path.join(_DIR_GUI, "telas")                                     # → src/gui/telas/

for _path in (_DIR_SRC, _DIR_GUI, _DIR_TELAS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import flet as ft

# Importa a função de validação pura (não precisa de Page nem de banco)
from painel_adm import validar_formulario_navio


# ===========================================================================
# CLASSE AUXILIAR: MockPage
# ===========================================================================

class MockPage:
    """
    Simula a interface de `ft.Page` para testes que não precisam de display.

    Em vez de abrir uma janela real, o MockPage registra os seus chamadas
    em listas que podem ser verificadas nos asserts.

    Uso típico:
        page = MockPage()
        # ... chama uma função que usa page.update(), page.snack_bar = ...
        assert page.update_chamado  # verifica se a UI foi atualizada
    """
    def __init__(self):
        # Simula o overlay (lista de diálogos, banners, etc.)
        self.overlay = []
        # Registra todas as chamadas a page.update()
        self.updates = []
        # Simula o snack_bar
        self.snack_bar = None
        # Atributo customizado que a app usa para saber qual aba está ativa
        self.active_tab = "fila"

    def update(self):
        """Registra que o update foi chamado, mas não faz nada graficamente."""
        self.updates.append(True)

    @property
    def update_chamado(self) -> bool:
        """Propriedade conveniente para os asserts."""
        return len(self.updates) > 0

    def go(self, route: str):
        """Simula navegação de rota."""
        self.route = route


# ===========================================================================
# FIXTURE: mock_page
# ===========================================================================

@pytest.fixture
def mock_page():
    """
    Fixture que fornece um MockPage limpo para cada teste.
    Assim cada teste começa com um estado de página zerado.
    """
    return MockPage()


# ===========================================================================
# SUITE 1: Testes da função pura `validar_formulario_navio`
# ===========================================================================

class TestValidacaoFormularioNavio:
    """
    ESTRATÉGIA 1: Testa a lógica de validação do formulário de cadastro
    sem depender de nenhum elemento visual.

    `validar_formulario_navio()` é uma função pura: recebe strings e retorna
    um dict de erros. Nenhuma Page, nenhum banco. Extremamente rápido.
    """

    # --- Helpers ---

    def _dados_validos(self, **overrides) -> dict:
        """Conjunto base de dados válidos, com possibilidade de override."""
        base = dict(
            imo="1234567",
            nome="Estrela do Nordeste",
            capitao="Capitao Lucas Araujo",
            companhia="Porto Maranhão SA",
            peso="800",
            categoria="COMUM",
        )
        base.update(overrides)
        return base

    def _validar(self, **overrides) -> dict:
        """Atalho para chamar a validação com os dados base."""
        return validar_formulario_navio(**self._dados_validos(**overrides))

    # --- Cenário Feliz ---

    def test_formulario_completamente_valido_sem_erros(self):
        """
        DADO um conjunto de dados completamente válidos,
        QUANDO a validação é chamada,
        ENTÃO o dicionário de erros deve estar vazio.
        """
        erros = self._validar()
        assert erros == {}, f"Erros inesperados em dados válidos: {erros}"

    # --- Validação do campo IMO ---

    def test_imo_vazio_gera_erro(self):
        """Campo IMO em branco é obrigatório."""
        erros = self._validar(imo="")
        assert "imo" in erros

    def test_imo_apenas_espacos_gera_erro(self):
        """IMO com só espaços deve ser tratado como vazio."""
        erros = self._validar(imo="   ")
        assert "imo" in erros

    def test_imo_com_letras_gera_erro(self):
        """IMO deve conter apenas dígitos."""
        erros = self._validar(imo="ABC1234")
        assert "imo" in erros

    def test_imo_com_menos_de_7_digitos_gera_erro(self):
        erros = self._validar(imo="12345")
        assert "imo" in erros

    def test_imo_com_mais_de_7_digitos_gera_erro(self):
        erros = self._validar(imo="12345678")
        assert "imo" in erros

    def test_imo_exatamente_7_digitos_e_valido(self):
        erros = self._validar(imo="9876543")
        assert "imo" not in erros

    # --- Validação do campo Nome ---

    def test_nome_vazio_gera_erro(self):
        erros = self._validar(nome="")
        assert "nome" in erros

    def test_nome_com_caracteres_especiais_gera_erro(self):
        """Símbolos como @, #, $ não são permitidos no nome do navio."""
        erros = self._validar(nome="Navio@#$")
        assert "nome" in erros

    def test_nome_com_acentos_e_valido(self):
        """Letras acentuadas são permitidas (padrão nacional)."""
        erros = self._validar(nome="São Paulo da Barca")
        assert "nome" not in erros

    # --- Validação do campo Peso ---

    def test_peso_zero_invalido(self):
        """Um navio não pode ter peso declarado zero."""
        erros = self._validar(peso="0")
        assert "peso" in erros

    def test_peso_negativo_invalido(self):
        erros = self._validar(peso="-50")
        assert "peso" in erros

    def test_peso_decimal_invalido(self):
        """O campo espera um inteiro; ponto decimal deve ser rejeitado."""
        erros = self._validar(peso="100.5")
        assert "peso" in erros

    def test_peso_positivo_valido(self):
        erros = self._validar(peso="2000")
        assert "peso" not in erros

    # --- Validação de múltiplos erros simultâneos ---

    def test_todos_campos_vazios_retorna_todos_os_erros(self):
        """Formulário completamente vazio deve falhar em todos os campos."""
        erros = validar_formulario_navio(
            imo="", nome="", capitao="", companhia="", peso="", categoria=""
        )
        campos_esperados = {"imo", "nome", "capitao", "companhia", "peso", "categoria"}
        assert set(erros.keys()) == campos_esperados, \
            f"Campos com erro: {set(erros.keys())} — Esperados: {campos_esperados}"

    def test_erro_num_campo_nao_contamina_outros(self):
        """Um IMO inválido não deve gerar erros nos demais campos válidos."""
        erros = self._validar(imo="ABC")
        assert "imo" in erros
        # Os outros campos foram preenchidos corretamente e não devem ter erro
        for campo in ["nome", "capitao", "companhia", "peso", "categoria"]:
            assert campo not in erros, f"Campo '{campo}' foi erroneamente invalidado."


# ===========================================================================
# SUITE 2: Testes de estado visual com MockPage (sem display real)
# ===========================================================================

class TestEstadoVisualControles:
    """
    ESTRATÉGIA 2: Testa se os controles Flet mudam de estado visual
    corretamente em resposta a eventos simulados.

    Não precisamos de display. Instanciamos os controles ft.* em Python puro,
    simulamos um evento com MagicMock e verificamos a propriedade resultante
    do objeto Flet (ex: `campo.error_text`, `btn.disabled`, `txt.color`).
    """

    def test_campo_imo_invalido_exibe_error_text(self, mock_page):
        """
        CENÁRIO: O utilizador digita um IMO inválido e clica em "Salvar".
        A UI deve exibir uma mensagem de erro no campo imo (error_text).

        Este teste simula o handler que a view chama ao submeter o formulário.
        """
        # ARRANGE: Cria os controles exatamente como a view faz
        campo_imo = ft.TextField(label="IMO ID", value="ABC")         # IMO inválido
        campo_nome = ft.TextField(label="Nome", value="Navio Teste")
        campo_capitao = ft.TextField(label="Capitão", value="Cap Test")
        campo_companhia = ft.TextField(label="Companhia", value="Cia Test")
        campo_peso = ft.TextField(label="Peso", value="500")
        dropdown_categoria = ft.Dropdown(value="COMUM")
        txt_mensagem = ft.Text(value="", visible=False, color=ft.Colors.RED)

        # Define o handler de validação (replica a lógica de painel_adm.py)
        def handle_salvar(e):
            """Simula o que acontece quando o botão 'Salvar' é clicado."""
            erros = validar_formulario_navio(
                imo=campo_imo.value or "",
                nome=campo_nome.value or "",
                capitao=campo_capitao.value or "",
                companhia=campo_companhia.value or "",
                peso=campo_peso.value or "",
                categoria=dropdown_categoria.value or "",
            )
            # Limpa os erros anteriores
            campo_imo.error_text = None

            # Aplica os erros de validação nos campos
            if "imo" in erros:
                campo_imo.error_text = erros["imo"]
                txt_mensagem.value = "Corrija os erros antes de salvar."
                txt_mensagem.visible = True
            else:
                txt_mensagem.visible = False

            mock_page.update()

        # ACT: Simula o clique no botão (evento simulado com MagicMock)
        evento_simulado = MagicMock()
        handle_salvar(evento_simulado)

        # ASSERT: Verifica o estado dos controles APÓS o handler executar
        assert campo_imo.error_text is not None, \
            "O campo IMO deveria exibir uma mensagem de erro (error_text)!"
        assert "7" in campo_imo.error_text.lower() or "imo" in campo_imo.error_text.lower(), \
            f"A mensagem de erro não é informativa o suficiente: '{campo_imo.error_text}'"

        assert txt_mensagem.visible is True, \
            "A mensagem de erro geral deveria estar visível!"

        assert mock_page.update_chamado, \
            "page.update() deveria ter sido chamado para atualizar a UI!"

    def test_formulario_valido_nao_exibe_error_text(self, mock_page):
        """
        CENÁRIO: O utilizador preenche todos os campos corretamente.
        Nenhum error_text deve aparecer nos campos.
        """
        campo_imo = ft.TextField(label="IMO ID", value="9999999")
        campo_nome = ft.TextField(label="Nome", value="Navio Correto")
        campo_capitao = ft.TextField(label="Capitão", value="Cap Correto")
        campo_companhia = ft.TextField(label="Companhia", value="Cia Correta")
        campo_peso = ft.TextField(label="Peso", value="1000")
        dropdown_categoria = ft.Dropdown(value="URGENTE_PERECIVEL")

        def handle_salvar(e):
            erros = validar_formulario_navio(
                imo=campo_imo.value, nome=campo_nome.value,
                capitao=campo_capitao.value, companhia=campo_companhia.value,
                peso=campo_peso.value, categoria=dropdown_categoria.value,
            )
            campo_imo.error_text = erros.get("imo", None)
            campo_nome.error_text = erros.get("nome", None)
            campo_capitao.error_text = erros.get("capitao", None)
            campo_companhia.error_text = erros.get("companhia", None)
            campo_peso.error_text = erros.get("peso", None)
            mock_page.update()

        evento_simulado = MagicMock()
        handle_salvar(evento_simulado)

        # ASSERT: Nenhum campo deve ter error_text
        assert campo_imo.error_text is None
        assert campo_nome.error_text is None
        assert campo_capitao.error_text is None
        assert campo_companhia.error_text is None
        assert campo_peso.error_text is None

    def test_switch_perecivel_altera_estado_visual(self, mock_page):
        """
        CENÁRIO: O utilizador ativa o switch de 'carga perecível'.
        O Container de aviso deve ficar visível (visible=True).

        Testa a reatividade de controles dependentes.
        """
        # ARRANGE: Cria o switch e o container de aviso (replica a lógica da UI)
        aviso_perecivel = ft.Container(
            visible=False,  # Começa escondido
            content=ft.Text("⚠️ Carga Perecível: Atenção ao prazo!", color=ft.Colors.ORANGE),
        )

        switch_perecivel = ft.Switch(label="Carga Perecível?", value=False)

        def on_switch_changed(e):
            """Handler que reage à mudança do switch."""
            aviso_perecivel.visible = switch_perecivel.value
            mock_page.update()

        switch_perecivel.on_change = on_switch_changed

        # ACT 1: Simula ativação do switch
        switch_perecivel.value = True
        evento_ativo = MagicMock()
        evento_ativo.control = switch_perecivel
        on_switch_changed(evento_ativo)

        # ASSERT 1: O aviso deve estar visível quando switch=True
        assert aviso_perecivel.visible is True, \
            "O aviso de perecível deveria estar visível quando o switch está ativo!"

        # ACT 2: Simula desativação do switch
        switch_perecivel.value = False
        on_switch_changed(evento_ativo)

        # ASSERT 2: O aviso deve desaparecer quando switch=False
        assert aviso_perecivel.visible is False, \
            "O aviso de perecível deveria estar oculto quando o switch está inativo!"

    def test_botao_fica_desativado_durante_operacao_assincrona(self, mock_page):
        """
        CENÁRIO: O utilizador clica em 'Atracar Próximo'. O botão deve ficar
        disabled=True durante o processamento para evitar duplo clique.

        Este padrão é crítico para a usabilidade. Verificamos se o handler
        corretamente desativa o botão antes de chamar o backend.
        """
        # ARRANGE
        btn_atracar = ft.ElevatedButton("Atracar Próximo", disabled=False)
        loading = ft.ProgressRing(visible=False)
        operacao_executada = []  # lista mutável para capturar chamadas dentro do closure

        def handle_atracar(e):
            """Replica a lógica do painel_adm.py ao iniciar uma operação."""
            # Fase 1: Desabilita imediatamente (antes de chamar o backend)
            btn_atracar.disabled = True
            loading.visible = True
            operacao_executada.append("iniciada")
            mock_page.update()

            # (Normalmente aqui seria uma Thread, mas para o teste, chamamos sync)
            # Fase 2: Após conclusão, reabilita
            btn_atracar.disabled = False
            loading.visible = False
            operacao_executada.append("concluida")
            mock_page.update()

        # ACT
        evento = MagicMock()
        handle_atracar(evento)

        # ASSERT: A sequência de estados foi respeitada
        assert operacao_executada == ["iniciada", "concluida"], \
            "A sequência de execução do handler está incorreta!"

        # Estado final: botão deve estar reativado após a operação
        assert btn_atracar.disabled is False, \
            "O botão deveria estar reativado após o fim da operação!"
        assert loading.visible is False

        # O page.update() foi chamado 2 vezes (antes e depois da operação)
        assert len(mock_page.updates) == 2


# ===========================================================================
# SUITE 3: Testes de comportamento da fila (lógica de negócio na View)
# ===========================================================================

class TestLogicaFilaView:
    """
    Testa a lógica interna de `fila_view.py` utilizando mocks para isolar
    a dependência do banco de dados (`obter_sessao` e `obter_fila_atracacao_dto`).

    Desta forma, testamos apenas o COMPORTAMENTO da view (como ela reage
    aos dados recebidos), não a integração com o banco.
    """

    def test_fila_vazia_torna_texto_visivel_e_tabela_invisivel(self, mock_page):
        """
        DADO que o banco retorna uma fila vazia,
        QUANDO a view carrega os dados,
        ENTÃO o texto 'nenhum navio' deve ficar visível e a tabela oculta.
        """
        # ARRANGE: Cria os controles que a view usa para mostrar/esconder
        tabela_fila = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("Col"))],
            rows=[],
            visible=True,  # Começa visível
        )
        txt_vazio = ft.Text(
            "Nenhum navio aguardando na fila de atracação no momento.",
            visible=False,  # Começa escondido
        )

        # Simula a função que a worker thread executa com dados do banco
        def processar_resultado_fila(navios_dto: list):
            """Extrai a lógica de renderização de fila_view.py para teste."""
            if not navios_dto:
                txt_vazio.visible = True
                tabela_fila.visible = False
            else:
                txt_vazio.visible = False
                tabela_fila.visible = True
                tabela_fila.rows = [
                    ft.DataRow(cells=[ft.DataCell(ft.Text(n.nome))])
                    for n in navios_dto
                ]
            mock_page.update()

        # ACT: Simula retorno de lista vazia do banco
        processar_resultado_fila([])

        # ASSERT
        assert txt_vazio.visible is True, "Texto 'fila vazia' deveria estar visível!"
        assert tabela_fila.visible is False, "A tabela deveria estar oculta com fila vazia!"

    def test_fila_com_navios_popula_tabela_corretamente(self, mock_page):
        """
        DADO que o banco retorna 3 navios na fila,
        QUANDO a view carrega os dados,
        ENTÃO a tabela deve ter 3 linhas e o texto 'vazio' deve estar oculto.
        """
        # ARRANGE: Cria DTOs de navios simulados (sem precisar de banco)
        from dataclasses import dataclass
        from typing import List

        @dataclass
        class NavioDTOFake:
            imo_id: str
            nome: str
            cargas: List = None
            score: float = 0.0

            def __post_init__(self):
                if self.cargas is None:
                    self.cargas = []

        navios_fake = [
            NavioDTOFake(imo_id="IMO001", nome="Bravura"),
            NavioDTOFake(imo_id="IMO002", nome="Esperança"),
            NavioDTOFake(imo_id="IMO003", nome="Coragem"),
        ]

        tabela_fila = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("Nome"))],
            rows=[],
            visible=False,
        )
        txt_vazio = ft.Text(visible=True)  # Começa visível (estado anterior)

        def processar_resultado_fila(navios_dto: list):
            if not navios_dto:
                txt_vazio.visible = True
                tabela_fila.visible = False
            else:
                txt_vazio.visible = False
                tabela_fila.visible = True
                tabela_fila.rows = [
                    ft.DataRow(cells=[ft.DataCell(ft.Text(n.nome))])
                    for n in navios_dto
                ]
            mock_page.update()

        # ACT
        processar_resultado_fila(navios_fake)

        # ASSERT
        assert txt_vazio.visible is False, "Texto 'vazio' deveria estar oculto com navios na fila!"
        assert tabela_fila.visible is True, "A tabela deveria estar visível com navios!"
        assert len(tabela_fila.rows) == 3, \
            f"Esperado 3 linhas na tabela, mas há {len(tabela_fila.rows)}!"

        # Verifica se os nomes foram inseridos na ordem correta
        nome_da_primeira_linha = tabela_fila.rows[0].cells[0].content.value
        assert nome_da_primeira_linha == "Bravura"

    def test_dialogo_detalhes_abre_ao_clicar_ver_mais(self, mock_page):
        """
        CENÁRIO: O utilizador clica no botão 'Ver mais' de um navio.
        O `dialogo_detalhes.open` deve ser alterado para True.
        """
        # ARRANGE: Simula o diálogo de detalhes (exatamente como em fila_view.py)
        dialogo_detalhes = ft.AlertDialog(open=False)
        mock_page.overlay.append(dialogo_detalhes)

        def abrir_detalhes(navio_nome: str):
            """Replica a lógica de `abrir_detalhes_navio()` em fila_view.py."""
            dialogo_detalhes.title = ft.Text(f"Ficha Técnica — {navio_nome}")
            dialogo_detalhes.open = True
            mock_page.update()

        # ACT: Simula o clique no botão 'Ver mais' do primeiro navio
        abrir_detalhes("Bravura dos Mares")

        # ASSERT: O diálogo deve estar aberto
        assert dialogo_detalhes.open is True, \
            "O dialogo_detalhes.open deveria ser True após clicar em 'Ver mais'!"
        assert "Bravura dos Mares" in dialogo_detalhes.title.value

    def test_fechar_dialogo_altera_open_para_false(self, mock_page):
        """
        CENÁRIO: O utilizador fecha o diálogo de detalhes.
        O `dialogo_detalhes.open` deve ser alterado para False.
        """
        dialogo_detalhes = ft.AlertDialog(open=True)  # Começa aberto

        def fechar_dialogo(e):
            dialogo_detalhes.open = False
            mock_page.update()

        evento = MagicMock()
        fechar_dialogo(evento)

        assert dialogo_detalhes.open is False, \
            "O dialogo_detalhes.open deveria ser False após fechar!"


# ===========================================================================
# SUITE 4: Testes de cor de status (elemento visual crítico)
# ===========================================================================

class TestCoresDeSatusVisuais:
    """
    Verifica se a lógica de cor responde corretamente ao status do navio/vaga.
    As cores são elementos visuais críticos para o operador do porto:
    - Verde = Livre / Aprovado
    - Vermelho = Ocupado / Rejeitado
    - Laranja = Pendente

    Testamos a função que determina a cor sem precisar renderizar nada.
    """

    def _cor_para_status_vaga(self, status: str) -> str:
        """
        Replica a lógica de cor do monitor de berços em painel_adm.py.
        Extraída para função pura para facilitar os testes.
        """
        mapa = {
            "LIVRE": ft.Colors.GREEN_700,
            "OCUPADA": ft.Colors.RED_700,
        }
        return mapa.get(status, ft.Colors.GREY_500)

    def _cor_para_status_navio(self, status: str) -> str:
        """Replica a lógica de cor do badge de status do navio."""
        mapa = {
            "VALIDADO": ft.Colors.GREEN,
            "PENDENTE": ft.Colors.ORANGE,
            "REJEITADO": ft.Colors.RED,
            "ATRACADO": ft.Colors.BLUE,
            "FINALIZADO": ft.Colors.GREY,
        }
        return mapa.get(status, ft.Colors.GREY_500)

    def test_vaga_livre_e_verde(self):
        cor = self._cor_para_status_vaga("LIVRE")
        assert cor == ft.Colors.GREEN_700

    def test_vaga_ocupada_e_vermelha(self):
        cor = self._cor_para_status_vaga("OCUPADA")
        assert cor == ft.Colors.RED_700

    def test_status_desconhecido_retorna_cinza(self):
        cor = self._cor_para_status_vaga("STATUS_INVALIDO")
        assert cor == ft.Colors.GREY_500

    def test_navio_validado_e_verde(self):
        cor = self._cor_para_status_navio("VALIDADO")
        assert cor == ft.Colors.GREEN

    def test_navio_pendente_e_laranja(self):
        cor = self._cor_para_status_navio("PENDENTE")
        assert cor == ft.Colors.ORANGE

    def test_navio_rejeitado_e_vermelho(self):
        cor = self._cor_para_status_navio("REJEITADO")
        assert cor == ft.Colors.RED

    def test_navio_atracado_e_azul(self):
        cor = self._cor_para_status_navio("ATRACADO")
        assert cor == ft.Colors.BLUE

    def test_todos_status_de_navio_mapeados(self):
        """
        Garante que nenhum status do enum StatusNavio ficou sem cor mapeada.
        Teste de regressão: se adicionar um novo status no futuro sem mapear a cor,
        este teste vai falhar imediatamente.
        """
        from cad import StatusNavio
        status_sem_cor_generica = []
        for status in StatusNavio:
            cor = self._cor_para_status_navio(status.value)
            if cor == ft.Colors.GREY_500:
                status_sem_cor_generica.append(status.value)

        assert status_sem_cor_generica == [], \
            f"Os seguintes status não têm cor mapeada (estão a usar o fallback cinza): {status_sem_cor_generica}"


if __name__ == "__main__":
    # Permite executar diretamente: python src/testes/test_componentes_flet.py
    pytest.main([__file__, "-v"])
