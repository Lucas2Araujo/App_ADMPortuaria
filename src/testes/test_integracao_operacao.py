import sys
import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, delete

_DIR_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIR_SRC not in sys.path:
    sys.path.insert(0, _DIR_SRC)

from cad import Base, Navio, Carga, Vaga, Atracacao, StatusNavio, StatusVaga
from controller_operacao import (
    atracar_navio,
    registrar_desatracacao,
    obter_painel_vagas_dto,
    obter_contadores_dashboard,
    liberar_vaga_individual,
)
from controller_cadastros import (
    solicitar_pre_cadastro,
    auditar_solicitacoes_pendentes,
    auditar_navio_individual,
    excluir_registro_navio,
    CargaNaoClassificadaError,
)


@pytest_asyncio.fixture(scope="module")
async def engine_memoria():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def sessao_bd(engine_memoria):
    AsyncSessionFactory = async_sessionmaker(
        bind=engine_memoria, class_=AsyncSession, expire_on_commit=False
    )
    sessao = AsyncSessionFactory()
    try:
        yield sessao
    finally:
        try:
            await sessao.rollback()
            await sessao.execute(delete(Atracacao))
            await sessao.execute(delete(Carga))
            await sessao.execute(delete(Navio))
            await sessao.execute(delete(Vaga))
            await sessao.commit()
        finally:
            await sessao.close()


async def _criar_navio_validado(
    sessao,
    imo_id: str = "IMO1111111",
    nome: str = "Navio Teste",
    horas_espera: float = 1.0,
    categoria: str = "COMUM",
    peso: int = 500,
    eh_perecivel: bool = False,
    possui_doc: bool = True,
) -> Navio:
    navio = Navio(
        imo_id=imo_id,
        nome=nome,
        nome_capitao="Capitão Genérico",
        companhia="Cia. de Testes Ltda.",
        status=StatusNavio.VALIDADO,
        data_solicitacao=datetime.now() - timedelta(hours=horas_espera),
    )
    carga = Carga(
        descricao="Carga de Teste",
        categoria=categoria,
        quantidade_toneladas=peso,
        eh_perecivel=eh_perecivel,
        documento_alfandega=possui_doc,
    )
    navio.cargas.append(carga)
    sessao.add(navio)
    await sessao.flush()
    return navio


async def _criar_vaga(
    sessao, tipo: str = "CONTAINER", status: StatusVaga = StatusVaga.LIVRE
) -> Vaga:
    vaga = Vaga(tipo_vaga=tipo, status=status)
    sessao.add(vaga)
    await sessao.flush()
    return vaga


class TestSolicitarPreCadastro:
    @pytest.mark.asyncio
    async def test_navio_e_carga_sao_salvos_no_banco(self, sessao_bd):
        imo_teste = "IMO9999001"
        dto_retornado = await solicitar_pre_cadastro(
            session=sessao_bd,
            imo=imo_teste,
            nome="Estrela do Nordeste",
            capitao="Capitao Araujo",
            companhia="Porto Maranhão S.A.",
            carga_desc="Soja Especial",
            categoria="BAIXA_PERECIBILIDADE",
            peso=1200,
            eh_perecivel=True,
            possui_documentos=True,
        )
        assert dto_retornado.imo_id == imo_teste
        assert dto_retornado.nome == "Estrela do Nordeste"
        assert dto_retornado.status == "PENDENTE"

        res = await sessao_bd.execute(select(Navio).filter_by(imo_id=imo_teste))
        navio_no_bd = res.scalar_one_or_none()
        assert navio_no_bd is not None, "O navio não foi salvo no banco de dados!"
        assert navio_no_bd.nome == "Estrela do Nordeste"
        assert navio_no_bd.status == StatusNavio.PENDENTE

        assert len(navio_no_bd.cargas) == 1
        carga_salva = navio_no_bd.cargas[0]
        assert carga_salva.categoria == "BAIXA_PERECIBILIDADE"
        assert carga_salva.quantidade_toneladas == 1200
        assert carga_salva.eh_perecivel is True
        assert carga_salva.documento_alfandega is True

    @pytest.mark.asyncio
    async def test_imo_duplicado_levanta_excecao(self, sessao_bd):
        from sqlalchemy.exc import IntegrityError

        imo_duplicado = "IMO9999002"
        await solicitar_pre_cadastro(
            session=sessao_bd,
            imo=imo_duplicado,
            nome="Primeiro Navio",
            capitao="Cap A",
            companhia="Cia A",
            carga_desc="Aço",
            categoria="COMUM",
            peso=100,
            eh_perecivel=False,
            possui_documentos=True,
        )
        with pytest.raises(IntegrityError):
            await solicitar_pre_cadastro(
                session=sessao_bd,
                imo=imo_duplicado,
                nome="Segundo Navio",
                capitao="Cap B",
                companhia="Cia B",
                carga_desc="Ferro",
                categoria="COMUM",
                peso=200,
                eh_perecivel=False,
                possui_documentos=True,
            )


class TestAtracarNavio:
    @pytest.mark.asyncio
    async def test_atracar_navio_altera_status_e_cria_atracacao(self, sessao_bd):
        navio = await _criar_navio_validado(
            sessao_bd, imo_id="IMO0000001", nome="Bravura dos Mares"
        )
        vaga = await _criar_vaga(sessao_bd, tipo="GRANELEIRO")

        log_dto = await atracar_navio(sessao_bd)
        assert (
            log_dto is not None
        ), "atracar_navio() retornou None, mas deveria ter atracado!"
        assert log_dto.tipo == "ATRACAO"
        assert log_dto.navio_imo_id == navio.imo_id
        assert log_dto.vaga_id == vaga.id

        await sessao_bd.refresh(navio)
        await sessao_bd.refresh(vaga)

        assert (
            navio.status == StatusNavio.ATRACADO
        ), f"Esperado ATRACADO, mas status é {navio.status}"
        assert (
            vaga.status == StatusVaga.OCUPADA
        ), f"Esperado OCUPADA, mas status é {vaga.status}"

        res = await sessao_bd.execute(
            select(Atracacao).filter_by(navio_imo_id=navio.imo_id)
        )
        atracacao_no_bd = res.scalar_one_or_none()
        assert atracacao_no_bd is not None, "Nenhum registo de Atracacao foi criado!"
        assert atracacao_no_bd.data_hora_inicio is not None
        assert (
            atracacao_no_bd.data_hora_fim is None
        ), "data_hora_fim deveria ser None numa atracação recém-criada"

    @pytest.mark.asyncio
    async def test_atracar_sem_navio_validado_retorna_none(self, sessao_bd):
        await _criar_vaga(sessao_bd, tipo="CONTAINER")
        resultado = await atracar_navio(sessao_bd)
        assert resultado is None
        from sqlalchemy import func

        res = await sessao_bd.execute(select(func.count(Atracacao.id)))
        assert res.scalar() == 0

    @pytest.mark.asyncio
    async def test_atracar_sem_vaga_livre_retorna_none(self, sessao_bd):
        navio = await _criar_navio_validado(
            sessao_bd, imo_id="IMO0000003", nome="Aguardando Vaga"
        )
        await _criar_vaga(sessao_bd, tipo="GRANELEIRO", status=StatusVaga.OCUPADA)
        resultado = await atracar_navio(sessao_bd)
        assert resultado is None
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.VALIDADO


class TestRegistrarDesatracacao:
    @pytest.mark.asyncio
    async def test_desatracacao_libera_vaga_e_finaliza_navio(self, sessao_bd):
        navio = await _criar_navio_validado(
            sessao_bd, imo_id="IMO0000004", nome="Guerreiro Portuário"
        )
        navio.status = StatusNavio.ATRACADO

        vaga = await _criar_vaga(sessao_bd, tipo="CONTAINER", status=StatusVaga.OCUPADA)

        atracacao = Atracacao(
            navio_imo_id=navio.imo_id,
            vaga_id=vaga.id,
            data_hora_inicio=datetime.now() - timedelta(hours=2),
            data_hora_fim=None,
        )
        sessao_bd.add(atracacao)
        await sessao_bd.flush()

        log_dto = await registrar_desatracacao(sessao_bd, imo_id=navio.imo_id)
        assert log_dto is not None
        assert log_dto.tipo == "DESATRACAO"
        assert log_dto.navio_imo_id == navio.imo_id

        await sessao_bd.refresh(navio)
        await sessao_bd.refresh(vaga)
        await sessao_bd.refresh(atracacao)

        assert navio.status == StatusNavio.FINALIZADO
        assert vaga.status == StatusVaga.LIVRE
        assert (
            atracacao.data_hora_fim is not None
        ), "data_hora_fim deveria ter sido preenchida!"

    @pytest.mark.asyncio
    async def test_desatracacao_imo_inexistente_retorna_none(self, sessao_bd):
        resultado = await registrar_desatracacao(sessao_bd, imo_id="IMO_NAO_EXISTE")
        assert resultado is None


class TestAuditarSolicitacoesPendentes:
    @pytest.mark.asyncio
    async def test_navio_com_docs_completos_e_validado(self, sessao_bd):
        navio = Navio(
            imo_id="IMO0000010",
            nome="Documentado",
            nome_capitao="Cap X",
            companhia="Cia X",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Eletrônicos",
            categoria="COMUM",
            quantidade_toneladas=300,
            eh_perecivel=False,
            documento_alfandega=True,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        dtos_auditados = await auditar_solicitacoes_pendentes(sessao_bd)
        assert len(dtos_auditados) == 1
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.VALIDADO

    @pytest.mark.asyncio
    async def test_navio_com_docs_incompletos_e_rejeitado(self, sessao_bd):
        navio = Navio(
            imo_id="IMO0000011",
            nome="Sem Papel",
            nome_capitao="Cap Y",
            companhia="Cia Y",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Contrabando?",
            categoria="COMUM",
            quantidade_toneladas=50,
            eh_perecivel=False,
            documento_alfandega=False,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        await auditar_solicitacoes_pendentes(sessao_bd)
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.REJEITADO

    @pytest.mark.asyncio
    async def test_carga_nao_classificada_levanta_excecao(self, sessao_bd):
        navio = Navio(
            imo_id="IMO0000012",
            nome="Carga Misteriosa",
            nome_capitao="Cap Z",
            companhia="Cia Z",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Caixa Lacrada",
            categoria="OUTROS_PENDENTE",
            quantidade_toneladas=100,
            eh_perecivel=False,
            documento_alfandega=True,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        with pytest.raises(CargaNaoClassificadaError) as exc_info:
            await auditar_solicitacoes_pendentes(sessao_bd)
        assert exc_info.value.imo_id == "IMO0000012"
        assert exc_info.value.carga_descricao == "Caixa Lacrada"

    @pytest.mark.asyncio
    async def test_carga_nao_classificada_mas_docs_pendentes_nao_levanta_excecao_e_rejeita(
        self, sessao_bd
    ):
        navio = Navio(
            imo_id="IMO0000013",
            nome="Sem Docs Outros",
            nome_capitao="Cap W",
            companhia="Cia W",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Outra Carga",
            categoria="OUTROS_PENDENTE",
            quantidade_toneladas=80,
            eh_perecivel=False,
            documento_alfandega=False,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        # Não deve levantar CargaNaoClassificadaError porque a documentação está pendente.
        # Deve concluir a auditoria e rejeitar o navio.
        dtos_auditados = await auditar_solicitacoes_pendentes(sessao_bd)
        assert len(dtos_auditados) == 1
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.REJEITADO


class TestContadoresDashboard:
    @pytest.mark.asyncio
    async def test_contadores_refletem_estado_real_do_banco(self, sessao_bd):
        await _criar_vaga(sessao_bd, tipo="GRANELEIRO", status=StatusVaga.LIVRE)
        await _criar_vaga(sessao_bd, tipo="CONTAINER", status=StatusVaga.LIVRE)
        await _criar_navio_validado(sessao_bd, imo_id="IMO0000020", nome="Já Aprovado")
        navio_pendente = Navio(
            imo_id="IMO0000021",
            nome="Aguardando",
            nome_capitao="Cap P",
            companhia="Cia P",
            status=StatusNavio.PENDENTE,
        )
        sessao_bd.add(navio_pendente)
        await sessao_bd.flush()

        contadores = await obter_contadores_dashboard(sessao_bd)
        assert contadores["vagas_livres"] == 2
        assert contadores["total_vagas"] == 2
        assert contadores["total_validado"] == 1
        assert contadores["total_pendente"] == 1
        assert contadores["total_finalizado"] == 0

    @pytest.mark.asyncio
    async def test_banco_vazio_retorna_zeros(self, sessao_bd):
        contadores = await obter_contadores_dashboard(sessao_bd)
        assert contadores["vagas_livres"] == 0
        assert contadores["total_vagas"] == 0
        assert contadores["total_validado"] == 0
        assert contadores["total_pendente"] == 0
        assert contadores["total_finalizado"] == 0


class TestExcluirRegistroNavio:
    @pytest.mark.asyncio
    async def test_exclui_navio_corretamente(self, sessao_bd):
        navio = await _criar_navio_validado(
            sessao_bd, imo_id="IMO_DEL_1", nome="Navio a Deletar"
        )
        await excluir_registro_navio(sessao_bd, "IMO_DEL_1")
        res = await sessao_bd.execute(select(Navio).filter_by(imo_id="IMO_DEL_1"))
        assert res.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_exclui_navio_atracado_falha(self, sessao_bd):
        navio = await _criar_navio_validado(
            sessao_bd, imo_id="IMO_DEL_2", nome="Navio Atracado"
        )
        navio.status = StatusNavio.ATRACADO
        await sessao_bd.commit()
        with pytest.raises(ValueError, match="Não é possível excluir o navio"):
            await excluir_registro_navio(sessao_bd, "IMO_DEL_2")


class TestAuditarNavioIndividual:
    @pytest.mark.asyncio
    async def test_audita_navio_aprovar_com_docs(self, sessao_bd):
        navio = Navio(
            imo_id="IMO_AUD_1",
            nome="Doc OK",
            nome_capitao="Cap A",
            companhia="Cia A",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="X",
            categoria="COMUM",
            quantidade_toneladas=10,
            eh_perecivel=False,
            documento_alfandega=True,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        await auditar_navio_individual(sessao_bd, "IMO_AUD_1", "APROVAR")
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.VALIDADO

    @pytest.mark.asyncio
    async def test_audita_navio_aprovar_sem_docs(self, sessao_bd):
        navio = Navio(
            imo_id="IMO_AUD_2",
            nome="Doc Faltante",
            nome_capitao="Cap B",
            companhia="Cia B",
            status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Y",
            categoria="COMUM",
            quantidade_toneladas=10,
            eh_perecivel=False,
            documento_alfandega=False,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        await sessao_bd.flush()

        await auditar_navio_individual(sessao_bd, "IMO_AUD_2", "APROVAR")
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.REJEITADO

    @pytest.mark.asyncio
    async def test_audita_navio_rejeitar(self, sessao_bd):
        navio = Navio(
            imo_id="IMO_AUD_3",
            nome="Para Rejeitar",
            nome_capitao="Cap C",
            companhia="Cia C",
            status=StatusNavio.PENDENTE,
        )
        sessao_bd.add(navio)
        await sessao_bd.flush()

        await auditar_navio_individual(sessao_bd, "IMO_AUD_3", "REJEITAR")
        await sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.REJEITADO
