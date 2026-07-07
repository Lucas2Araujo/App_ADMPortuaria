import unittest
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from cad import Base, Navio
import app


class TestCLIApp(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        AsyncSessionFactory = async_sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session = AsyncSessionFactory()

    async def asyncTearDown(self):
        await self.session.close()

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
    async def test_coletar_dados_cadastro_cli(self, mock_input):
        """Testa se o formulário do CLI capta os dados corretamente e salva no banco"""

        await app.coletar_dados_cadastro(self.session)

        # Verifica no banco de dados isolado se o registro foi criado corretamente
        result = await self.session.execute(select(Navio).filter_by(imo_id="IMO1234567"))
        navio_salvo = result.scalar_one_or_none()

        self.assertIsNotNone(navio_salvo, "O navio não foi salvo no banco de dados.")
        self.assertEqual(navio_salvo.nome, "Estrela do Mar")
        self.assertEqual(navio_salvo.status.name, "PENDENTE")
        self.assertEqual(len(navio_salvo.cargas), 1)
        self.assertEqual(navio_salvo.cargas[0].categoria, "COMUM")

if __name__ == "__main__":
    unittest.main()
