"""Testes automatizados para o frontend Flet (AdminPort).

Organizado em duas suítes:

1. ``TestImportacaoModulos``  — smoke tests que verificam se todos os
   módulos GUI importam sem erros de sintaxe ou dependência ausente.

2. ``TestValidacaoFormularioNavio`` — testes unitários da função pura
   ``validar_formulario_navio`` extraída de ``painel_adm.py``.
   Não precisam de display gráfico nem de banco de dados.
"""

import sys
import os
import unittest

# ---------------------------------------------------------------------------
# Ajuste de sys.path para funcionar tanto ao rodar com `pytest src/` quanto
# diretamente com `python src/test_gui.py`.
# ---------------------------------------------------------------------------
_DIR_TEST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
_DIR_GUI = os.path.join(_DIR_TEST, "gui")  # src/gui/
_DIR_TELAS = os.path.join(_DIR_GUI, "telas")  # src/gui/telas/

for _path in (_DIR_TEST, _DIR_GUI, _DIR_TELAS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ---------------------------------------------------------------------------
# Import da função pura de validação — feito APÓS o ajuste do sys.path para
# que o pyrefly e outros analisadores estáticos consigam resolver o módulo.
# ---------------------------------------------------------------------------
from painel_adm import validar_formulario_navio  # noqa: E402

# ===========================================================================
# 1. Smoke tests de importação
# ===========================================================================


class TestImportacaoModulos(unittest.TestCase):
    """Verifica que todos os módulos do frontend importam sem exceção.

    Se um colega introduzir um erro de sintaxe, import inválido ou remover
    uma dependência, esses testes falharão imediatamente no CI.
    """

    def test_importa_flet(self):
        """O pacote flet deve estar instalado e importável."""
        import flet  # noqa: F401

    def test_importa_painel_adm(self):
        """painel_adm.py deve importar sem erros."""
        import painel_adm  # noqa: F401

    def test_importa_fila_view(self):
        """fila_view.py deve importar sem erros."""
        import fila_view  # noqa: F401

    def test_importa_painel_tripulacao(self):
        """painel_tripulacao.py deve importar sem erros."""
        import painel_tripulacao  # noqa: F401

    def test_importa_main_gui(self):
        """main_gui.py deve importar sem erros (sem executar ft.run)."""
        # Substitui ft.run por um no-op para evitar que a janela abra
        import flet as ft

        _run_original = ft.run
        ft.run = lambda *args, **kwargs: None
        try:
            import main_gui  # noqa: F401
        finally:
            ft.run = _run_original


# ===========================================================================
# 2. Testes unitários da lógica de validação (sem UI, sem DB)
# ===========================================================================


class TestValidacaoFormularioNavio(unittest.TestCase):
    """Testa a função pura ``validar_formulario_navio``.

    Cada método de teste cobre um cenário específico de validação,
    isolado de qualquer dependência de UI ou banco de dados.
    """

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _dados_validos(self, **overrides) -> dict:
        """Retorna um conjunto base de dados válidos, com overrides opcionais."""
        base = dict(
            imo="1234567",
            nome="Estrela do Mar",
            capitao="Capitao Lucas",
            companhia="Navegantes SA",
            peso="500",
            categoria="COMUM",
        )
        base.update(overrides)
        return base

    def _validar(self, **overrides) -> dict:
        return validar_formulario_navio(**self._dados_validos(**overrides))

    # -----------------------------------------------------------------------
    # Cenário feliz
    # -----------------------------------------------------------------------

    def test_dados_validos_sem_erros(self):
        """Dados completamente válidos não devem gerar nenhum erro."""
        erros = self._validar()
        self.assertEqual(erros, {}, f"Erros inesperados: {erros}")

    def test_todas_categorias_validas(self):
        """Todas as opções de categoria permitidas devem ser aceitas."""
        categorias_validas = [
            "URGENTE_PERECIVEL",
            "ALTA_PERECIBILIDADE",
            "BAIXA_PERECIBILIDADE",
            "COMUM",
        ]
        for cat in categorias_validas:
            with self.subTest(categoria=cat):
                erros = self._validar(categoria=cat)
                self.assertNotIn("categoria", erros)

    # -----------------------------------------------------------------------
    # Validação do IMO
    # -----------------------------------------------------------------------

    def test_imo_vazio_e_obrigatorio(self):
        erros = self._validar(imo="")
        self.assertIn("imo", erros)

    def test_imo_com_espacos_e_obrigatorio(self):
        """IMO com apenas espaços deve ser tratado como vazio."""
        erros = self._validar(imo="   ")
        self.assertIn("imo", erros)

    def test_imo_com_menos_de_7_digitos(self):
        erros = self._validar(imo="12345")
        self.assertIn("imo", erros)

    def test_imo_com_mais_de_7_digitos(self):
        erros = self._validar(imo="12345678")
        self.assertIn("imo", erros)

    def test_imo_com_letras_invalido(self):
        erros = self._validar(imo="ABC1234")
        self.assertIn("imo", erros)

    def test_imo_exatamente_7_digitos_valido(self):
        erros = self._validar(imo="1234567")
        self.assertNotIn("imo", erros)

    # -----------------------------------------------------------------------
    # Validação do Nome do Navio
    # -----------------------------------------------------------------------

    def test_nome_vazio_e_obrigatorio(self):
        erros = self._validar(nome="")
        self.assertIn("nome", erros)

    def test_nome_com_caracteres_especiais_invalido(self):
        erros = self._validar(nome="Navio@#$%")
        self.assertIn("nome", erros)

    def test_nome_com_acentos_valido(self):
        erros = self._validar(nome="São Pedro")
        self.assertNotIn("nome", erros)

    def test_nome_com_hifen_e_apostrofo_valido(self):
        erros = self._validar(nome="D'Artagnan-II")
        self.assertNotIn("nome", erros)

    # -----------------------------------------------------------------------
    # Validação do Capitão
    # -----------------------------------------------------------------------

    def test_capitao_vazio_e_obrigatorio(self):
        erros = self._validar(capitao="")
        self.assertIn("capitao", erros)

    def test_capitao_com_caracteres_especiais_invalido(self):
        erros = self._validar(capitao="Cap!@#")
        self.assertIn("capitao", erros)

    def test_capitao_nome_composto_valido(self):
        erros = self._validar(capitao="João da Silva")
        self.assertNotIn("capitao", erros)

    # -----------------------------------------------------------------------
    # Validação da Companhia
    # -----------------------------------------------------------------------

    def test_companhia_vazia_e_obrigatoria(self):
        erros = self._validar(companhia="")
        self.assertIn("companhia", erros)

    def test_companhia_com_caracteres_especiais_invalida(self):
        erros = self._validar(companhia="Cia & Filhos")
        self.assertIn("companhia", erros)

    def test_companhia_alfanumerica_valida(self):
        erros = self._validar(companhia="Navegantes SA")
        self.assertNotIn("companhia", erros)

    # -----------------------------------------------------------------------
    # Validação do Peso
    # -----------------------------------------------------------------------

    def test_peso_vazio_e_obrigatorio(self):
        erros = self._validar(peso="")
        self.assertIn("peso", erros)

    def test_peso_zero_invalido(self):
        erros = self._validar(peso="0")
        self.assertIn("peso", erros)

    def test_peso_negativo_invalido(self):
        erros = self._validar(peso="-10")
        self.assertIn("peso", erros)

    def test_peso_nao_numerico_invalido(self):
        erros = self._validar(peso="abc")
        self.assertIn("peso", erros)

    def test_peso_decimal_invalido(self):
        """O campo espera inteiro; strings decimais devem ser rejeitadas."""
        erros = self._validar(peso="100.5")
        self.assertIn("peso", erros)

    def test_peso_positivo_valido(self):
        erros = self._validar(peso="1000")
        self.assertNotIn("peso", erros)

    # -----------------------------------------------------------------------
    # Validação da Categoria
    # -----------------------------------------------------------------------

    def test_categoria_vazia_obrigatoria(self):
        erros = self._validar(categoria="")
        self.assertIn("categoria", erros)

    def test_categoria_none_obrigatoria(self):
        """Categoria vazia representa 'nenhum item selecionado' no Dropdown."""
        # None é o valor padrão do Dropdown antes de qualquer seleção;
        # convertemos para string vazia antes de chamar a função de validação,
        # exatamente como a UI faz em salvar_navio().
        categoria_sem_selecao: str = ""
        erros = validar_formulario_navio(
            **{**self._dados_validos(), "categoria": categoria_sem_selecao}
        )
        self.assertIn("categoria", erros)

    # -----------------------------------------------------------------------
    # Múltiplos erros simultâneos
    # -----------------------------------------------------------------------

    def test_todos_campos_vazios_retorna_todos_os_erros(self):
        """Formulário completamente vazio deve reportar erro em todos os campos."""
        erros = validar_formulario_navio(
            imo="", nome="", capitao="", companhia="", peso="", categoria=""
        )
        campos_esperados = {"imo", "nome", "capitao", "companhia", "peso", "categoria"}
        self.assertEqual(campos_esperados, set(erros.keys()))

    def test_apenas_imo_invalido_nao_contamina_outros_campos(self):
        """Um erro em IMO não deve gerar erros nos demais campos válidos."""
        erros = self._validar(imo="ABC")
        self.assertIn("imo", erros)
        self.assertNotIn("nome", erros)
        self.assertNotIn("capitao", erros)
        self.assertNotIn("companhia", erros)
        self.assertNotIn("peso", erros)
        self.assertNotIn("categoria", erros)


if __name__ == "__main__":
    unittest.main()
