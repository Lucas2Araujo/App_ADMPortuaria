"""
=============================================================================
TESTES DE INTEGRAÇÃO — controller_operacao.py & controller_cadastros.py
=============================================================================

OBJETIVO
--------
Testar as funções dos controllers verificando se elas realmente ESCREVEM e
ALTERAM os dados no banco de dados (SQLite em memória), de ponta a ponta.

DIFERENÇA ENTRE TESTE UNITÁRIO E TESTE DE INTEGRAÇÃO
-----------------------------------------------------
- Testes Unitários (test_ord_propriety.py): testam uma função ISOLADA, sem
  banco de dados nem dependências externas. Usam objetos Python simples.

- Testes de Integração (este ficheiro): testam a CADEIA COMPLETA, incluindo
  a sessão SQLAlchemy, os modelos ORM e os commits no banco. Verificam se
  os dados realmente persistiram e se os status foram alterados.

FIXTURES DO PYTEST
------------------
Uma *fixture* é uma função decorada com @pytest.fixture que prepara e
fornece recursos para os testes. O Pytest as injeta automaticamente como
argumentos nos métodos de teste.

Neste ficheiro há duas fixtures encadeadas:
 1. ``engine_memoria``: cria o banco SQLite :memory: e as tabelas (escopo
    de módulo — criado uma vez para todos os testes do ficheiro).
 2. ``sessao_bd`` (escopo de função): abre uma sessão, executa o teste e
    limpa TODAS as tabelas no teardown. Isso garante isolamento total:
    cada teste começa com um banco limpo, sem dependência de ordem.

ESTRATÉGIA DE ISOLAMENTO: DELETE POR TESTE
------------------------------------------
O SQLite :memory: não suporta SAVEPOINT aninhado como o PostgreSQL. A
estratégia mais robusta e portável é:
  - Cada teste recebe uma sessão.
  - No teardown (cláusula finally), deletamos os registos de todas as
    tabelas na ordem correta (respeitando FK: filhos antes de pais).
  - Isso faz o banco voltar ao estado vazio antes do próximo teste.

COMO EXECUTAR
-------------
  cd /home/lucas/Documentos/ufMA/App_ADMPortuaria
  python -m pytest src/testes/test_integracao_operacao.py -v

COMO REPLICAR PARA OUTROS CONTROLLERS
--------------------------------------
1. Copie este ficheiro e renomeie (ex: test_integracao_cadastros.py).
2. Importe as funções do controller desejado.
3. Escreva os testes seguindo o padrão ARRANGE → ACT → ASSERT.
=============================================================================
"""

import sys
import os
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------------------------
# Ajuste do sys.path para que os módulos src/ sejam encontrados ao rodar com
# `python -m pytest src/` a partir da raiz do projeto.
# ---------------------------------------------------------------------------
_DIR_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # → src/
if _DIR_SRC not in sys.path:
    sys.path.insert(0, _DIR_SRC)

# ---------------------------------------------------------------------------
# Imports dos módulos do projeto (somente após o ajuste do path)
# ---------------------------------------------------------------------------
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


# ===========================================================================
# FIXTURES — O "esqueleto" de todos os testes de integração
# ===========================================================================

@pytest.fixture(scope="module")
def engine_memoria():
    """
    FIXTURE DE MÓDULO (executada UMA VEZ para todos os testes do ficheiro).

    Cria uma engine SQLAlchemy apontada para um banco SQLite exclusivamente
    na RAM (:memory:). Não toca no ficheiro porto.db de produção.

    O parâmetro ``connect_args={"check_same_thread": False}`` é necessário
    pois o SQLite em modo :memory: pode ser usado por diferentes contextos
    dentro do mesmo processo de testes.

    Ao final do módulo, a engine é descartada automaticamente pelo Pytest.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        # echo=True,  # Descomente para ver o SQL gerado durante o debug
    )
    # Cria todas as tabelas definidas nos modelos ORM (Navio, Vaga, etc.)
    Base.metadata.create_all(engine)
    yield engine
    # Teardown: destrói as tabelas ao final de todos os testes do módulo
    Base.metadata.drop_all(engine)


@pytest.fixture
def sessao_bd(engine_memoria):
    """
    FIXTURE DE FUNÇÃO (executada uma vez para CADA teste).

    Estratégia de Isolamento via DELETE por Teste:
    -----------------------------------------------
    O SQLite :memory: não suporta SAVEPOINT aninhado de forma fiável.
    A estratégia mais robusta é:

    1. Cada teste recebe uma sessão limpa (banco vazio do ponto de vista
       do que os testes anteriores gravaram).
    2. No teardown (finally), deletamos os registos de TODAS as tabelas
       na ordem correta (filhos antes de pais para respeitar FK):
         Atracacao → Carga → Navio → Vaga
    3. O banco fica vazio para o próximo teste.

    Como usar nos testes:
        def test_meu_teste(sessao_bd):
            # sessao_bd já está pronto para uso — banco vazio
            resultado = minha_funcao(sessao_bd)
            assert ...
    """
    SessionFactory = sessionmaker(bind=engine_memoria)
    sessao = SessionFactory()

    try:
        yield sessao  # ← O teste é executado aqui
    finally:
        # Teardown: limpa todas as tabelas na ordem correta (FK: filhos primeiro)
        # Isso garante isolamento total entre testes.
        try:
            sessao.rollback()  # Desfaz qualquer transação pendente com erro
            sessao.query(Atracacao).delete()   # Filha de Navio e Vaga
            sessao.query(Carga).delete()       # Filha de Navio
            sessao.query(Navio).delete()
            sessao.query(Vaga).delete()
            sessao.commit()
        finally:
            sessao.close()


# ---------------------------------------------------------------------------
# Função auxiliar (Factory) — Reduz duplicação (DRY) ao criar dados de teste
# ---------------------------------------------------------------------------

def _criar_navio_validado(
    sessao,
    imo_id: str = "IMO1111111",
    nome: str = "Navio Teste",
    horas_espera: float = 1.0,
    categoria: str = "COMUM",
    peso: int = 500,
    eh_perecivel: bool = False,
    possui_doc: bool = True,
) -> Navio:
    """
    Fábrica de navios com status VALIDADO, prontos para entrar na fila de atracação.
    Centraliza a criação de dados de teste, facilitando a manutenção futura.
    """
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
    sessao.flush()  # Persiste na transação sem commit, para que o ID seja gerado
    return navio


def _criar_vaga(sessao, tipo: str = "CONTAINER", status: StatusVaga = StatusVaga.LIVRE) -> Vaga:
    """Fábrica de vagas do cais para os testes."""
    vaga = Vaga(tipo_vaga=tipo, status=status)
    sessao.add(vaga)
    sessao.flush()
    return vaga


# ===========================================================================
# SUITE 1: Testes para controller_cadastros.py — solicitar_pre_cadastro()
# ===========================================================================

class TestSolicitarPreCadastro:
    """
    Verifica se a função solicitar_pre_cadastro() persiste corretamente
    um Navio e uma Carga no banco de dados, retornando o DTO esperado.
    """

    def test_navio_e_carga_sao_salvos_no_banco(self, sessao_bd):
        """
        INTEGRAÇÃO: Após chamar solicitar_pre_cadastro(), o banco deve conter
        exatamente 1 Navio e 1 Carga com os dados fornecidos.

        ARRANGE → ACT → ASSERT é o padrão de leitura recomendado.
        """
        # ARRANGE: Define os parâmetros do formulário
        imo_teste = "IMO9999001"

        # ACT: Chama a função real que escreve no banco
        dto_retornado = solicitar_pre_cadastro(
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

        # ASSERT 1: O DTO retornado tem os dados corretos (teste da camada de saída)
        assert dto_retornado.imo_id == imo_teste
        assert dto_retornado.nome == "Estrela do Nordeste"
        assert dto_retornado.status == "PENDENTE"  # Padrão inicial

        # ASSERT 2: O banco de dados realmente tem o registro (teste da camada de persistência)
        navio_no_bd = sessao_bd.query(Navio).filter_by(imo_id=imo_teste).first()
        assert navio_no_bd is not None, "O navio não foi salvo no banco de dados!"
        assert navio_no_bd.nome == "Estrela do Nordeste"
        assert navio_no_bd.status == StatusNavio.PENDENTE

        # ASSERT 3: A carga associada foi salva corretamente
        assert len(navio_no_bd.cargas) == 1
        carga_salva = navio_no_bd.cargas[0]
        assert carga_salva.categoria == "BAIXA_PERECIBILIDADE"
        assert carga_salva.quantidade_toneladas == 1200
        assert carga_salva.eh_perecivel is True
        assert carga_salva.documento_alfandega is True

    def test_imo_duplicado_levanta_excecao(self, sessao_bd):
        """
        O banco deve rejeitar dois navios com o mesmo IMO (chave primária única).
        Verificamos se a exceção de integridade é propagada corretamente.
        """
        from sqlalchemy.exc import IntegrityError

        imo_duplicado = "IMO9999002"
        solicitar_pre_cadastro(
            session=sessao_bd, imo=imo_duplicado, nome="Primeiro Navio",
            capitao="Cap A", companhia="Cia A", carga_desc="Aço",
            categoria="COMUM", peso=100, eh_perecivel=False, possui_documentos=True,
        )

        with pytest.raises(IntegrityError):
            solicitar_pre_cadastro(
                session=sessao_bd, imo=imo_duplicado, nome="Segundo Navio",
                capitao="Cap B", companhia="Cia B", carga_desc="Ferro",
                categoria="COMUM", peso=200, eh_perecivel=False, possui_documentos=True,
            )


# ===========================================================================
# SUITE 2: Testes para controller_operacao.py — atracar_navio()
# ===========================================================================

class TestAtracarNavio:
    """
    Verifica se atracar_navio() orquestra corretamente a mudança de status do
    Navio, da Vaga e a criação do registo de Atracacao no banco.
    """

    def test_atracar_navio_altera_status_e_cria_atracacao(self, sessao_bd):
        """
        CENÁRIO FELIZ: Há 1 navio VALIDADO e 1 vaga LIVRE.
        Após chamar atracar_navio(), esperamos:
          - Navio.status == ATRACADO
          - Vaga.status == OCUPADA
          - 1 registo em Atracacao com data_hora_fim == None (em aberto)
        """
        # ARRANGE: Prepara o estado inicial do banco para este teste
        navio = _criar_navio_validado(sessao_bd, imo_id="IMO0000001", nome="Bravura dos Mares")
        vaga = _criar_vaga(sessao_bd, tipo="GRANELEIRO")

        # ACT: Executa a operação de atracação
        log_dto = atracar_navio(sessao_bd)

        # ASSERT 1: A função retornou o DTO correto
        assert log_dto is not None, "atracar_navio() retornou None, mas deveria ter atracado!"
        assert log_dto.tipo == "ATRACAO"
        assert log_dto.navio_imo_id == navio.imo_id
        assert log_dto.vaga_id == vaga.id

        # ASSERT 2: Recarrega os objetos do banco para verificar as mudanças persistidas
        sessao_bd.refresh(navio)
        sessao_bd.refresh(vaga)

        assert navio.status == StatusNavio.ATRACADO, \
            f"Esperado ATRACADO, mas status é {navio.status}"
        assert vaga.status == StatusVaga.OCUPADA, \
            f"Esperado OCUPADA, mas status é {vaga.status}"

        # ASSERT 3: Verifica se o registo de Atracacao foi criado no banco
        atracacao_no_bd = sessao_bd.query(Atracacao).filter_by(
            navio_imo_id=navio.imo_id
        ).first()
        assert atracacao_no_bd is not None, "Nenhum registo de Atracacao foi criado!"
        assert atracacao_no_bd.data_hora_inicio is not None
        assert atracacao_no_bd.data_hora_fim is None, \
            "data_hora_fim deveria ser None numa atracação recém-criada"

    def test_atracar_sem_navio_validado_retorna_none(self, sessao_bd):
        """
        CENÁRIO DE BORDA: Se não há navios com status VALIDADO na fila,
        atracar_navio() deve retornar None sem criar nenhum registo.
        """
        # ARRANGE: Cria apenas uma vaga (sem navios validados)
        _criar_vaga(sessao_bd, tipo="CONTAINER")

        # ACT
        resultado = atracar_navio(sessao_bd)

        # ASSERT
        assert resultado is None
        assert sessao_bd.query(Atracacao).count() == 0

    def test_atracar_sem_vaga_livre_retorna_none(self, sessao_bd):
        """
        CENÁRIO DE BORDA: Se há navio VALIDADO mas todas as vagas estão OCUPADAS,
        a função deve retornar None e não alterar o status do navio.
        """
        # ARRANGE
        navio = _criar_navio_validado(sessao_bd, imo_id="IMO0000003", nome="Aguardando Vaga")
        _criar_vaga(sessao_bd, tipo="GRANELEIRO", status=StatusVaga.OCUPADA)

        # ACT
        resultado = atracar_navio(sessao_bd)

        # ASSERT
        assert resultado is None
        sessao_bd.refresh(navio)
        # O status do navio não deve ter sido alterado
        assert navio.status == StatusNavio.VALIDADO


# ===========================================================================
# SUITE 3: Testes para controller_operacao.py — registrar_desatracacao()
# ===========================================================================

class TestRegistrarDesatracacao:
    """
    Verifica o ciclo completo de vida de uma atracação:
    Atracação → Desatracação, conferindo cada mudança de estado.
    """

    def test_desatracacao_libera_vaga_e_finaliza_navio(self, sessao_bd):
        """
        Após registrar_desatracacao(), o sistema deve:
          - Definir Atracacao.data_hora_fim (fechar o registo)
          - Libertar a Vaga (OCUPADA → LIVRE)
          - Finalizar o Navio (ATRACADO → FINALIZADO)
        """
        # ARRANGE: Cria manualmente um estado "já atracado"
        navio = _criar_navio_validado(sessao_bd, imo_id="IMO0000004", nome="Guerreiro Portuário")
        navio.status = StatusNavio.ATRACADO

        vaga = _criar_vaga(sessao_bd, tipo="CONTAINER", status=StatusVaga.OCUPADA)

        atracacao = Atracacao(
            navio_imo_id=navio.imo_id,
            vaga_id=vaga.id,
            data_hora_inicio=datetime.now() - timedelta(hours=2),
            data_hora_fim=None,  # Atracação ainda em aberto
        )
        sessao_bd.add(atracacao)
        sessao_bd.flush()

        # ACT
        log_dto = registrar_desatracacao(sessao_bd, imo_id=navio.imo_id)

        # ASSERT 1: DTO retornado
        assert log_dto is not None
        assert log_dto.tipo == "DESATRACAO"
        assert log_dto.navio_imo_id == navio.imo_id

        # ASSERT 2: Mudanças persistidas no banco
        sessao_bd.refresh(navio)
        sessao_bd.refresh(vaga)
        sessao_bd.refresh(atracacao)

        assert navio.status == StatusNavio.FINALIZADO
        assert vaga.status == StatusVaga.LIVRE
        assert atracacao.data_hora_fim is not None, "data_hora_fim deveria ter sido preenchida!"

    def test_desatracacao_imo_inexistente_retorna_none(self, sessao_bd):
        """
        Se o IMO não possui atracação ativa, a função deve retornar None
        sem levantar exceção.
        """
        resultado = registrar_desatracacao(sessao_bd, imo_id="IMO_NAO_EXISTE")
        assert resultado is None


# ===========================================================================
# SUITE 4: Testes para controller_cadastros.py — auditar_solicitacoes_pendentes()
# ===========================================================================

class TestAuditarSolicitacoesPendentes:
    """
    Verifica se o processo de auditoria documental classifica os navios
    corretamente (VALIDADO ou REJEITADO) com base na documentação de alfândega.
    """

    def test_navio_com_docs_completos_e_validado(self, sessao_bd):
        """
        Um navio com todas as cargas com documento_alfandega=True
        deve ser promovido para VALIDADO.
        """
        # ARRANGE: Cria navio PENDENTE com documentação completa
        navio = Navio(
            imo_id="IMO0000010", nome="Documentado", nome_capitao="Cap X",
            companhia="Cia X", status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Eletrônicos", categoria="COMUM",
            quantidade_toneladas=300, eh_perecivel=False,
            documento_alfandega=True,  # ← Doc OK
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        sessao_bd.flush()

        # ACT
        dtos_auditados = auditar_solicitacoes_pendentes(sessao_bd)

        # ASSERT: somente este navio estava PENDENTE (banco limpo por fixture)
        assert len(dtos_auditados) == 1
        sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.VALIDADO, \
            f"Navio com docs completos deveria ser VALIDADO, mas está {navio.status}"

    def test_navio_com_docs_incompletos_e_rejeitado(self, sessao_bd):
        """
        Um navio com alguma carga sem documento_alfandega deve ser REJEITADO.
        """
        navio = Navio(
            imo_id="IMO0000011", nome="Sem Papel", nome_capitao="Cap Y",
            companhia="Cia Y", status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Contrabando?", categoria="COMUM",
            quantidade_toneladas=50, eh_perecivel=False,
            documento_alfandega=False,  # ← Doc FALTANDO
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        sessao_bd.flush()

        auditar_solicitacoes_pendentes(sessao_bd)

        sessao_bd.refresh(navio)
        assert navio.status == StatusNavio.REJEITADO

    def test_carga_nao_classificada_levanta_excecao(self, sessao_bd):
        """
        Se uma carga tem categoria 'OUTROS_PENDENTE', a função deve lançar
        CargaNaoClassificadaError antes de prosseguir com a auditoria.
        """
        navio = Navio(
            imo_id="IMO0000012", nome="Carga Misteriosa", nome_capitao="Cap Z",
            companhia="Cia Z", status=StatusNavio.PENDENTE,
        )
        carga = Carga(
            descricao="Caixa Lacrada", categoria="OUTROS_PENDENTE",  # ← Não classificada
            quantidade_toneladas=100, eh_perecivel=False, documento_alfandega=True,
        )
        navio.cargas.append(carga)
        sessao_bd.add(navio)
        sessao_bd.flush()

        with pytest.raises(CargaNaoClassificadaError) as exc_info:
            auditar_solicitacoes_pendentes(sessao_bd)

        # Verifica se a exceção contém os dados corretos para o formulário de classificação
        assert exc_info.value.imo_id == "IMO0000012"
        assert exc_info.value.carga_descricao == "Caixa Lacrada"


# ===========================================================================
# SUITE 5: Testes para controller_operacao.py — obter_contadores_dashboard()
# ===========================================================================

class TestContadoresDashboard:
    """
    Verifica se as estatísticas do dashboard refletem corretamente
    o estado atual do banco de dados.
    """

    def test_contadores_refletem_estado_real_do_banco(self, sessao_bd):
        """
        Cria um cenário controlado (2 vagas livres, 1 navio validado, 1 pendente)
        e verifica se os contadores batem exatamente.
        """
        # ARRANGE
        _criar_vaga(sessao_bd, tipo="GRANELEIRO", status=StatusVaga.LIVRE)
        _criar_vaga(sessao_bd, tipo="CONTAINER", status=StatusVaga.LIVRE)

        _criar_navio_validado(sessao_bd, imo_id="IMO0000020", nome="Já Aprovado")
        navio_pendente = Navio(
            imo_id="IMO0000021", nome="Aguardando", nome_capitao="Cap P",
            companhia="Cia P", status=StatusNavio.PENDENTE,
        )
        sessao_bd.add(navio_pendente)
        sessao_bd.flush()

        # ACT
        contadores = obter_contadores_dashboard(sessao_bd)

        # ASSERT
        assert contadores["vagas_livres"] == 2
        assert contadores["total_vagas"] == 2
        assert contadores["total_validado"] == 1
        assert contadores["total_pendente"] == 1
        assert contadores["total_finalizado"] == 0

    def test_banco_vazio_retorna_zeros(self, sessao_bd):
        """
        Com o banco completamente vazio, todos os contadores devem ser zero.
        Valida que o fixture de limpeza funciona corretamente entre testes.
        """
        # ARRANGE: Banco vazio (fixture garantiu limpeza)

        # ACT
        contadores = obter_contadores_dashboard(sessao_bd)

        # ASSERT
        assert contadores["vagas_livres"] == 0
        assert contadores["total_vagas"] == 0
        assert contadores["total_validado"] == 0
        assert contadores["total_pendente"] == 0
        assert contadores["total_finalizado"] == 0
