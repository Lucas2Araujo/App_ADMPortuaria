"""
Módulo Controlador de Operações de Fila e Atracação.

Este módulo processa a movimentação de navios, atracação em vagas livres e
a geração de histórico (logs) das operações em tempo real.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from cad import Vaga, Atracacao, StatusVaga, StatusNavio, Navio
from ord_propriety import obter_proximo_da_fila
from dto import OperacaoLogDTO, VagaDTO


async def atracar_navio(session) -> Optional[OperacaoLogDTO]:
    """
    Busca o próximo navio da fila e o aloca na primeira vaga disponível.
    Altera o status do navio, da vaga e gera o histórico de atracação.

    Args:
        session (Session): Sessão ativa do SQLAlchemy conectada ao banco de dados.

    Returns:
        OperacaoLogDTO | None: O log da atracação recém-registrada, ou `None` se falhar.
    """
    navio = await obter_proximo_da_fila(session)
    if not navio:
        return None

    result = await session.execute(select(Vaga).filter(Vaga.status == StatusVaga.LIVRE))
    vaga = result.scalars().first()
    if not vaga:
        return None

    navio.status = StatusNavio.ATRACADO
    vaga.status = StatusVaga.OCUPADA

    nova_atracacao = Atracacao(
        navio_imo_id=navio.imo_id, vaga_id=vaga.id, data_hora_inicio=datetime.now()
    )

    session.add(nova_atracacao)
    await session.commit()

    return OperacaoLogDTO(
        id=nova_atracacao.id,
        tipo="ATRACAO",
        navio_imo_id=nova_atracacao.navio_imo_id,
        vaga_id=nova_atracacao.vaga_id,
        data_hora=nova_atracacao.data_hora_inicio,
    )


async def registrar_desatracacao(session, imo_id: str) -> Optional[OperacaoLogDTO]:
    """
    Busca a atracação em aberto para o navio, registra o fim da operação
    e libera a vaga, mudando o status do navio para finalizado.

    Args:
        session (Session): Sessão ativa do SQLAlchemy.
        imo_id (str): O código IMO do navio que deve realizar a desatracação.

    Returns:
        OperacaoLogDTO | None: O log finalizado, ou `None` caso não encontre atracação ativa.
    """
    stmt = select(Atracacao).filter(
        Atracacao.navio_imo_id == imo_id, Atracacao.data_hora_fim.is_(None)
    )
    result = await session.execute(stmt)
    atracacao = result.scalars().first()

    if not atracacao:
        return None

    atracacao.data_hora_fim = datetime.now()

    result_vaga = await session.execute(
        select(Vaga).filter(Vaga.id == atracacao.vaga_id)
    )
    vaga = result_vaga.scalars().first()
    if vaga:
        vaga.status = StatusVaga.LIVRE

    result_navio = await session.execute(select(Navio).filter(Navio.imo_id == imo_id))
    navio = result_navio.scalars().first()
    if navio:
        navio.status = StatusNavio.FINALIZADO

    await session.commit()

    return OperacaoLogDTO(
        id=atracacao.id,
        tipo="DESATRACAO",
        navio_imo_id=atracacao.navio_imo_id,
        vaga_id=atracacao.vaga_id,
        data_hora=atracacao.data_hora_fim,
    )


async def obter_painel_vagas_dto(session) -> list[VagaDTO]:
    """
    Retorna uma lista de DTOs contendo o status de cada vaga e o navio
    atracado nela, se houver.
    """
    result = await session.execute(select(Vaga))
    vagas = result.scalars().all()
    if not vagas:
        return []

    result_atracacoes = await session.execute(
        select(Atracacao).filter(Atracacao.data_hora_fim.is_(None))
    )
    atracacoes_ativas = result_atracacoes.scalars().all()
    mapa_atracacoes = {a.vaga_id: a for a in atracacoes_ativas}
    imos_ativos = [a.navio_imo_id for a in atracacoes_ativas]

    if imos_ativos:
        stmt = (
            select(Navio)
            .options(joinedload(Navio.cargas))
            .filter(Navio.imo_id.in_(imos_ativos))
        )
        result_navios = await session.execute(stmt)
        navios = result_navios.scalars().unique().all()
    else:
        navios = []

    mapa_navios = {n.imo_id: n for n in navios}

    vagas_dto = []
    for vaga in vagas:
        if vaga.status == StatusVaga.OCUPADA:
            atracacao = mapa_atracacoes.get(vaga.id)
            if atracacao:
                navio = mapa_navios.get(atracacao.navio_imo_id)
                navio_dto = navio.to_dto() if navio else None
                vagas_dto.append(
                    vaga.to_dto(
                        navio_atracado=navio_dto,
                        data_hora_inicio=atracacao.data_hora_inicio,
                    )
                )
            else:
                vagas_dto.append(vaga.to_dto())
        else:
            vagas_dto.append(vaga.to_dto())

    return vagas_dto


async def obter_log_operacoes_dto(session) -> list[OperacaoLogDTO]:
    """
    Retorna a lista cronológica de eventos de operações ocorridos no porto.
    """
    stmt = select(Atracacao, Navio.nome).outerjoin(
        Navio, Atracacao.navio_imo_id == Navio.imo_id
    )
    result = await session.execute(stmt)
    atracacoes = result.all()
    eventos = []

    for op, nome in atracacoes:
        eventos.append(
            OperacaoLogDTO(
                id=op.id,
                tipo="ATRACAO",
                navio_imo_id=op.navio_imo_id,
                navio_nome=nome or "Desconhecido",
                vaga_id=op.vaga_id,
                data_hora=op.data_hora_inicio,
            )
        )
        if op.data_hora_fim:
            eventos.append(
                OperacaoLogDTO(
                    id=op.id,
                    tipo="DESATRACAO",
                    navio_imo_id=op.navio_imo_id,
                    navio_nome=nome or "Desconhecido",
                    vaga_id=op.vaga_id,
                    data_hora=op.data_hora_fim,
                )
            )

    eventos.sort(key=lambda x: x.data_hora, reverse=True)
    return eventos


async def obter_contagem_atracacoes_dia(session, dias: int = 7) -> dict[str, int]:
    """
    Retorna a contagem de atracações por dia para os últimos `dias`.
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta

    hoje_date = datetime.now().date()
    stmt = (
        select(
            func.date(Atracacao.data_hora_inicio).label("dia"),
            func.count().label("total"),
        )
        .filter(
            func.date(Atracacao.data_hora_inicio)
            >= (hoje_date - timedelta(days=dias - 1)).isoformat()
        )
        .group_by(func.date(Atracacao.data_hora_inicio))
    )
    result = await session.execute(stmt)
    resultados_grafico = result.all()
    return {row.dia: row.total for row in resultados_grafico}


async def liberar_vaga_individual(session, vaga_id: int):
    """
    Libera uma vaga específica, desatracando o navio atual se houver.
    """
    result = await session.execute(select(Vaga).filter(Vaga.id == vaga_id))
    vaga = result.scalars().first()
    if vaga and vaga.status == StatusVaga.OCUPADA:
        result_atracacao = await session.execute(
            select(Atracacao).filter(
                Atracacao.vaga_id == vaga.id, Atracacao.data_hora_fim.is_(None)
            )
        )
        atracacao = result_atracacao.scalars().first()
        if atracacao:
            atracacao.data_hora_fim = datetime.now()
            result_navio = await session.execute(
                select(Navio).filter(Navio.imo_id == atracacao.navio_imo_id)
            )
            navio = result_navio.scalars().first()
            if navio:
                navio.status = StatusNavio.FINALIZADO
        vaga.status = StatusVaga.LIVRE
        await session.commit()


async def obter_contadores_dashboard(session) -> dict:
    """
    Retorna estatísticas rápidas sobre vagas e navios.
    """
    from sqlalchemy import func

    total_vagas_res = await session.execute(select(func.count(Vaga.id)))
    total_vagas = total_vagas_res.scalar()

    vagas_ocupadas_res = await session.execute(
        select(func.count(Vaga.id)).filter(Vaga.status == StatusVaga.OCUPADA)
    )
    vagas_ocupadas = vagas_ocupadas_res.scalar()

    vagas_livres = total_vagas - vagas_ocupadas

    total_validado_res = await session.execute(
        select(func.count(Navio.imo_id)).filter(Navio.status == StatusNavio.VALIDADO)
    )
    total_validado = total_validado_res.scalar()

    total_pendente_res = await session.execute(
        select(func.count(Navio.imo_id)).filter(Navio.status == StatusNavio.PENDENTE)
    )
    total_pendente = total_pendente_res.scalar()

    total_finalizado_res = await session.execute(
        select(func.count(Navio.imo_id)).filter(Navio.status == StatusNavio.FINALIZADO)
    )
    total_finalizado = total_finalizado_res.scalar()

    return {
        "vagas_livres": vagas_livres,
        "total_vagas": total_vagas,
        "total_validado": total_validado,
        "total_pendente": total_pendente,
        "total_finalizado": total_finalizado,
    }
