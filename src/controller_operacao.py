"""
Módulo Controlador de Operações de Fila e Atracação.

Este módulo processa a movimentação de navios, atracação em vagas livres e
a geração de histórico (logs) das operações em tempo real.
"""

from datetime import datetime
from sqlalchemy.orm import joinedload
from cad import Vaga, Atracacao, StatusVaga, StatusNavio, Navio
from ord_propriety import obter_proximo_da_fila
from dto import OperacaoLogDTO, VagaDTO


def atracar_navio(session) -> Optional[OperacaoLogDTO]:
    """
    Busca o próximo navio da fila e o aloca na primeira vaga disponível.
    Altera o status do navio, da vaga e gera o histórico de atracação.

    Args:
        session (Session): Sessão ativa do SQLAlchemy conectada ao banco de dados.

    Returns:
        OperacaoLogDTO | None: O log da atracação recém-registrada, ou `None` se falhar.
    """
    navio = obter_proximo_da_fila(session)
    if not navio:
        return None

    vaga = session.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).first()
    if not vaga:
        return None

    navio.status = StatusNavio.ATRACADO
    vaga.status = StatusVaga.OCUPADA

    nova_atracacao = Atracacao(
        navio_imo_id=navio.imo_id, vaga_id=vaga.id, data_hora_inicio=datetime.now()
    )

    session.add(nova_atracacao)
    session.commit()

    return OperacaoLogDTO(
        id=nova_atracacao.id,
        tipo="ATRACAO",
        navio_imo_id=nova_atracacao.navio_imo_id,
        vaga_id=nova_atracacao.vaga_id,
        data_hora=nova_atracacao.data_hora_inicio
    )


def registrar_desatracacao(session, imo_id: str) -> Optional[OperacaoLogDTO]:
    """
    Busca a atracação em aberto para o navio, registra o fim da operação
    e libera a vaga, mudando o status do navio para finalizado.

    Args:
        session (Session): Sessão ativa do SQLAlchemy.
        imo_id (str): O código IMO do navio que deve realizar a desatracação.

    Returns:
        OperacaoLogDTO | None: O log finalizado, ou `None` caso não encontre atracação ativa.
    """
    atracacao = (
        session.query(Atracacao)
        .filter(Atracacao.navio_imo_id == imo_id, Atracacao.data_hora_fim.is_(None))
        .first()
    )

    if not atracacao:
        return None

    atracacao.data_hora_fim = datetime.now()

    vaga = session.query(Vaga).filter(Vaga.id == atracacao.vaga_id).first()
    if vaga:
        vaga.status = StatusVaga.LIVRE

    navio = session.query(Navio).filter(Navio.imo_id == imo_id).first()
    if navio:
        navio.status = StatusNavio.FINALIZADO

    session.commit()

    return OperacaoLogDTO(
        id=atracacao.id,
        tipo="DESATRACAO",
        navio_imo_id=atracacao.navio_imo_id,
        vaga_id=atracacao.vaga_id,
        data_hora=atracacao.data_hora_fim
    )


def obter_painel_vagas_dto(session) -> list[VagaDTO]:
    """
    Retorna uma lista de DTOs contendo o status de cada vaga e o navio
    atracado nela, se houver.
    """
    vagas = session.query(Vaga).all()
    if not vagas:
        return []

    atracacoes_ativas = (
        session.query(Atracacao).filter(Atracacao.data_hora_fim.is_(None)).all()
    )
    mapa_atracacoes = {a.vaga_id: a for a in atracacoes_ativas}
    imos_ativos = [a.navio_imo_id for a in atracacoes_ativas]

    navios = (
        session.query(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.imo_id.in_(imos_ativos))
        .all()
        if imos_ativos
        else []
    )
    mapa_navios = {n.imo_id: n for n in navios}

    vagas_dto = []
    for vaga in vagas:
        if vaga.status == StatusVaga.OCUPADA:
            atracacao = mapa_atracacoes.get(vaga.id)
            if atracacao:
                navio = mapa_navios.get(atracacao.navio_imo_id)
                navio_dto = navio.to_dto() if navio else None
                vagas_dto.append(vaga.to_dto(navio_atracado=navio_dto, data_hora_inicio=atracacao.data_hora_inicio))
            else:
                vagas_dto.append(vaga.to_dto())
        else:
            vagas_dto.append(vaga.to_dto())

    return vagas_dto


def obter_log_operacoes_dto(session) -> list[OperacaoLogDTO]:
    """
    Retorna a lista cronológica de eventos de operações ocorridos no porto.
    """
    atracacoes = (
        session.query(Atracacao, Navio.nome)
        .outerjoin(Navio, Atracacao.navio_imo_id == Navio.imo_id)
        .all()
    )
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


def obter_contagem_atracacoes_dia(session, dias: int = 7) -> dict[str, int]:
    """
    Retorna a contagem de atracações por dia para os últimos `dias`.
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta
    hoje_date = datetime.now().date()
    resultados_grafico = (
        session.query(
            func.date(Atracacao.data_hora_inicio).label("dia"),
            func.count().label("total"),
        )
        .filter(
            func.date(Atracacao.data_hora_inicio)
            >= (hoje_date - timedelta(days=dias-1)).isoformat()
        )
        .group_by(func.date(Atracacao.data_hora_inicio))
        .all()
    )
    return {row.dia: row.total for row in resultados_grafico}


def liberar_vaga_individual(session, vaga_id: int):
    """
    Libera uma vaga específica, desatracando o navio atual se houver.
    """
    vaga = session.query(Vaga).filter(Vaga.id == vaga_id).first()
    if vaga and vaga.status == StatusVaga.OCUPADA:
        atracacao = session.query(Atracacao).filter(
            Atracacao.vaga_id == vaga.id,
            Atracacao.data_hora_fim.is_(None)
        ).first()
        if atracacao:
            atracacao.data_hora_fim = datetime.now()
            navio = session.query(Navio).filter(Navio.imo_id == atracacao.navio_imo_id).first()
            if navio:
                navio.status = StatusNavio.FINALIZADO
        vaga.status = StatusVaga.LIVRE
        session.commit()


def obter_contadores_dashboard(session) -> dict:
    """
    Retorna estatísticas rápidas sobre vagas e navios.
    """
    total_vagas = session.query(Vaga).count()
    vagas_ocupadas = session.query(Vaga).filter(Vaga.status == StatusVaga.OCUPADA).count()
    vagas_livres = total_vagas - vagas_ocupadas
    total_validado = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).count()
    total_pendente = session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).count()
    total_finalizado = session.query(Navio).filter(Navio.status == StatusNavio.FINALIZADO).count()
    return {
        "vagas_livres": vagas_livres,
        "total_vagas": total_vagas,
        "total_validado": total_validado,
        "total_pendente": total_pendente,
        "total_finalizado": total_finalizado
    }



