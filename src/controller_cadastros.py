"""
Módulo de Controladores de Cadastro e Auditoria.

Responsável pelas funções que interagem com a base de dados para pré-cadastro
de navios, classificação de cargas e processos de auditoria documental.

Todas as funções públicas deste módulo são co-rotinas (``async def``) e
operam sobre uma ``AsyncSession`` do SQLAlchemy com ``aiosqlite``.
"""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from cad import Navio, Carga, StatusNavio
from dto import NavioDTO


class CargaNaoClassificadaError(Exception):
    """Exceção levantada quando uma carga requer classificação manual interativa.

    Attributes:
        imo_id (str): Código IMO do navio.
        navio_nome (str): Nome da embarcação.
        carga_id (int): ID da carga.
        carga_descricao (str): Descrição da carga.
    """

    def __init__(
        self, imo_id: str, navio_nome: str, carga_id: int, carga_descricao: str
    ):
        self.imo_id = imo_id
        self.navio_nome = navio_nome
        self.carga_id = carga_id
        self.carga_descricao = carga_descricao
        super().__init__(
            f"A carga '{carga_descricao}' (ID: {carga_id}) do navio {navio_nome} ({imo_id}) precisa de classificação."
        )


async def solicitar_pre_cadastro(
    session,
    imo: str,
    nome: str,
    capitao: str,
    companhia: str,
    carga_desc: str,
    categoria: str,
    peso: int,
    eh_perecivel: bool,
    possui_documentos: bool,
) -> NavioDTO:
    """(Co-rotina) Registra um novo navio e seu manifesto inicial.

    Args:
        session (AsyncSession): Sessão assíncrona.
        imo (str): Código IMO.
        nome (str): Nome da embarcação.
        capitao (str): Capitão responsável.
        companhia (str): Companhia de navegação.
        carga_desc (str): Descrição da carga.
        categoria (str): Categoria de perecibilidade.
        peso (int): Peso total (t).
        eh_perecivel (bool): Indica se recebe bônus de prioridade.
        possui_documentos (bool): Indica se a documentação está em ordem.

    Returns:
        NavioDTO: Objeto do navio recém-cadastrado.
    """
    # Timestamp exato é necessário para o cálculo do bônus anti-starvation.
    novo_navio = Navio(
        imo_id=imo,
        nome=nome,
        nome_capitao=capitao,
        companhia=companhia,
        status=StatusNavio.PENDENTE,
        data_solicitacao=datetime.now(),
    )

    nova_carga = Carga(
        descricao=carga_desc,
        categoria=categoria,
        quantidade_toneladas=peso,
        eh_perecivel=eh_perecivel,
        documento_alfandega=possui_documentos,
    )

    novo_navio.cargas.append(nova_carga)
    session.add(novo_navio)
    await session.commit()

    return novo_navio.to_dto()


async def classificar_carga(session, carga_id: int, categoria: str, eh_perecivel: bool):
    """(Co-rotina) Atualiza a categoria e a perecibilidade de uma carga.

    Args:
        session (AsyncSession): Sessão assíncrona.
        carga_id (int): ID da carga a ser classificada.
        categoria (str): Nova categoria.
        eh_perecivel (bool): Novo valor de perecibilidade.

    Raises:
        ValueError: Se a carga não for encontrada.
    """
    result = await session.execute(select(Carga).filter(Carga.id == carga_id))
    carga = result.scalars().first()
    if not carga:
        raise ValueError("Carga não encontrada.")
    carga.categoria = categoria
    carga.eh_perecivel = eh_perecivel
    await session.commit()


def _auditar_documentacao_navio(navio):
    """Avalia a documentação de um navio e altera seu status em memória.

    Args:
        navio (Navio): Instância ORM do navio a ser auditado.
    """
    # Regra de negócio: basta UMA carga sem documentação para rejeitar o navio inteiro.
    if any(not carga.documento_alfandega for carga in navio.cargas):
        navio.status = StatusNavio.REJEITADO
    else:
        navio.status = StatusNavio.VALIDADO


async def auditar_solicitacoes_pendentes(session) -> list[NavioDTO]:
    """(Co-rotina) Processa em lote navios PENDENTES, validando ou rejeitando cada um.

    Args:
        session (AsyncSession): Sessão assíncrona.

    Returns:
        list[NavioDTO]: Navios auditados.

    Raises:
        CargaNaoClassificadaError: Se houver cargas pendentes de classificação.
    """
    # joinedload evita N+1 queries.
    stmt = (
        select(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.status == StatusNavio.PENDENTE)
    )
    result = await session.execute(stmt)
    navios_pendentes = result.scalars().unique().all()

    if not navios_pendentes:
        return []

    auditos = []
    for navio in navios_pendentes:
        # Decisão arquitetural: documentação pendente sempre resulta em rejeição.
        # Ignoramos a classificação manual nesses casos para não interromper o lote em vão.
        possui_docs_pendentes = any(
            not carga.documento_alfandega for carga in navio.cargas
        )
        if not possui_docs_pendentes:
            for carga in navio.cargas:
                if carga.categoria == "OUTROS_PENDENTE":
                    # Interrompe o lote para classificação manual pelo operador.
                    raise CargaNaoClassificadaError(
                        imo_id=navio.imo_id,
                        navio_nome=navio.nome,
                        carga_id=carga.id,
                        carga_descricao=carga.descricao,
                    )

        _auditar_documentacao_navio(navio)
        auditos.append(navio.to_dto())

    await session.commit()
    return auditos


async def excluir_registro_navio(session, imo_id: str):
    """(Co-rotina) Remove permanentemente o registro de um navio e suas cargas.

    Args:
        session (AsyncSession): Sessão assíncrona.
        imo_id (str): Código IMO.

    Raises:
        ValueError: Se o navio não for encontrado ou estiver atracado.
    """
    result = await session.execute(select(Navio).filter(Navio.imo_id == imo_id))
    navio = result.scalars().first()
    if not navio:
        raise ValueError(f"Nenhum navio encontrado com o IMO ID '{imo_id}'.")

    # Guarda de negócio: exclusão de navio atracado corromperia o painel de vagas (vaga ficaria ocupada e órfã).
    if navio.status == StatusNavio.ATRACADO:
        raise ValueError(
            f"Não é possível excluir o navio '{navio.nome}' pois ele está atualmente ATRACADO."
        )

    await session.delete(navio)
    await session.commit()


async def editar_registro_navio(
    session, imo_id: str, nome: str, capitao: str, companhia: str
) -> NavioDTO:
    """(Co-rotina) Atualiza os dados cadastrais básicos de um navio.

    Args:
        session (AsyncSession): Sessão assíncrona.
        imo_id (str): Código IMO (chave de busca).
        nome (str): Novo nome.
        capitao (str): Novo capitão.
        companhia (str): Nova companhia.

    Returns:
        NavioDTO: DTO do navio com os dados atualizados.

    Raises:
        ValueError: Se o navio não for encontrado.
    """
    result = await session.execute(select(Navio).filter(Navio.imo_id == imo_id))
    navio = result.scalars().first()
    if not navio:
        raise ValueError("Navio não encontrado.")
    navio.nome = nome
    navio.nome_capitao = capitao
    navio.companhia = companhia
    await session.commit()
    return navio.to_dto()


async def obter_solicitacoes_pendentes_dto(session) -> list[NavioDTO]:
    """(Co-rotina) Retorna a lista de navios aguardando auditoria.

    Args:
        session (AsyncSession): Sessão assíncrona.

    Returns:
        list[NavioDTO]: Navios pendentes.
    """
    # joinedload evita erro de "session não disponível" ao acessar navio.cargas de forma lazy.
    stmt = (
        select(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.status == StatusNavio.PENDENTE)
    )
    result = await session.execute(stmt)
    pendentes = result.scalars().unique().all()
    return [navio.to_dto() for navio in pendentes]


async def obter_todos_navios_dto(session) -> list[NavioDTO]:
    """(Co-rotina) Retorna todos os navios cadastrados no sistema.

    Args:
        session (AsyncSession): Sessão assíncrona.

    Returns:
        list[NavioDTO]: Lista completa de navios.
    """
    stmt = select(Navio).options(joinedload(Navio.cargas))
    result = await session.execute(stmt)
    navios = result.scalars().unique().all()
    return [navio.to_dto() for navio in navios]


async def auditar_navio_individual(session, imo_id: str, acao: str) -> NavioDTO:
    """(Co-rotina) Aprova ou rejeita manualmente a solicitação de um único navio.

    Args:
        session (AsyncSession): Sessão assíncrona.
        imo_id (str): Código IMO.
        acao (str): Ação (``'APROVAR'`` ou ``'REJEITAR'``).

    Returns:
        NavioDTO: DTO do navio atualizado.

    Raises:
        ValueError: Se o navio não for encontrado.
        CargaNaoClassificadaError: Se houver cargas indefinidas e ação for APROVAR.
    """
    stmt = (
        select(Navio).options(joinedload(Navio.cargas)).filter(Navio.imo_id == imo_id)
    )
    result = await session.execute(stmt)
    navio = result.scalars().first()
    if not navio:
        raise ValueError("Navio não encontrado.")

    if acao == "APROVAR":
        # Aprovação com categoria indefinida corromperia o cálculo de score da fila.
        for carga in navio.cargas:
            if carga.categoria == "OUTROS_PENDENTE":
                raise CargaNaoClassificadaError(
                    imo_id=navio.imo_id,
                    navio_nome=navio.nome,
                    carga_id=carga.id,
                    carga_descricao=carga.descricao,
                )

        # Regra aduaneira prevalece: documentação incompleta força a rejeição independentemente da ação.
        if any(not c.documento_alfandega for c in navio.cargas):
            navio.status = StatusNavio.REJEITADO
        else:
            navio.status = StatusNavio.VALIDADO
    elif acao == "REJEITAR":
        navio.status = StatusNavio.REJEITADO

    await session.commit()
    return navio.to_dto()
