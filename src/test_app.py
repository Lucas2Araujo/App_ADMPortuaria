import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Navio
import app


class TestCLIApp(unittest.TestCase):
    def setUp(self):
        # 1. Cria um banco SQLite apenas na memória RAM (ultrarrápido e descartável)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()

    # O 'patch' injeta respostas automáticas sempre que o código original chamar input()
    # Ordem dos inputs: IMO, Nome, Capitão, Cia, Categoria(9=Containers), Peso, Alfândega(S)
    @patch(
        "builtins.input",
        side_effect=[
            "1234567",
            "Estrela do Mar",
            "Capitao Lucas",
            "Navegantes SA",
            "9",
            "500",
            "S",
        ],
    )
    def test_coletar_dados_cadastro_cli(self, mock_input):
        """Testa se o formulário do CLI capta os dados corretamente e salva no banco"""

        # Executa a função do CLI que contém vários input()
        app.coletar_dados_cadastro(self.session)

        # Verifica no banco de dados isolado se o registro foi criado corretamente
        navio_salvo = self.session.query(Navio).filter_by(imo_id="IMO1234567").first()

        self.assertIsNotNone(navio_salvo, "O navio não foi salvo no banco de dados.")
        self.assertEqual(navio_salvo.nome, "Estrela do Mar")
        self.assertEqual(navio_salvo.status.name, "PENDENTE")
        self.assertEqual(len(navio_salvo.cargas), 1)
        self.assertEqual(navio_salvo.cargas[0].categoria, "COMUM")


if __name__ == "__main__":
    unittest.main()
