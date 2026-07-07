"""
Motor de Regras de Negócio e Fila de Atracação.

Possui as funções responsáveis por ordenar a fila de atracação dinamicamente
utilizando cálculos de pontuação baseados na perecibilidade e regras anti-starvation.
"""

from datetime import datetime
from sqlalchemy import case, func, select, cast, Integer
from sqlalchemy.orm import joinedload, Session
from cad import Navio, Carga, StatusNavio

PESOS_CATEGORIA = {
    "URGENTE_PERECIVEL": 3,  # carnes, pescados, vacinas
    "ALTA_PERECIBILIDADE": 2,  # frutas, laticínios
    "BAIXA_PERECIBILIDADE": 1,  # grãos úmidos, Açucar
    "COMUM": 0,  # minério, maquinário, fertilizantes (não perecível)
}


def calcular_score(navio: Navio) -> float:
    """
    Calcula matematicamente a pontuação de prioridade de um navio em Python.

    Args:
        navio (Navio): A instância da classe `Navio` a ter a pontuação calculada.

    Returns:
        float: Score calculado a partir dos multiplicadores de carga e envelhecimento.
    """
    score_total = 0
    maior_grau_perecivel = 0

    for carga in navio.cargas:
        peso = PESOS_CATEGORIA.get(carga.categoria, 0)
        score_total += carga.quantidade_toneladas * peso

        if carga.eh_perecivel and peso > maior_grau_perecivel:
            maior_grau_perecivel = peso

    if maior_grau_perecivel > 0:
        score_total += 10000 * maior_grau_perecivel

    if navio.data_solicitacao:
        tempo_espera = datetime.now() - navio.data_solicitacao
        horas_espera = tempo_espera.total_seconds() / 3600.0
        score_total += horas_espera * 1000

    return score_total


def criar_subquery_score_cargas():
    """
    Delega a lógica do bônus de perecibilidade como uma Subquery no SQL.

    Returns:
        Subquery: Expressão em SQLAlchemy Select otimizada para o banco SQLite contendo
        o ID do navio e a coluna virtual 'score_cargas'.
    """

    peso_categoria = case(
        (Carga.categoria == "URGENTE_PERECIVEL", 3),
        (Carga.categoria == "ALTA_PERECIBILIDADE", 2),
        (Carga.categoria == "BAIXA_PERECIBILIDADE", 1),
        else_=0,
    )

    score_base = func.sum(Carga.quantidade_toneladas * peso_categoria)

    grau_perecivel = case((Carga.eh_perecivel == True, peso_categoria), else_=0)
    maior_grau = func.max(grau_perecivel)
    bonus_perecivel = case((maior_grau > 0, maior_grau * 10000), else_=0)

    return (
        select(
            Carga.navio_imo_id.label("navio_imo_id"),
            (func.coalesce(score_base, 0) + func.coalesce(bonus_perecivel, 0)).label(
                "score_cargas"
            ),
        )
        .group_by(Carga.navio_imo_id)
        .subquery()
    )


def obter_expressao_score_total(sq_cargas, agora):
    """
    Gera a expressão SQL final combinando as cargas com o envelhecimento (Anti-starvation).

    Args:
        sq_cargas (Subquery): O resultado da função `criar_subquery_score_cargas()`.
        agora (datetime): Um timestamp representando o momento atual.

    Returns:
        ColumnElement: A expressão algébrica em SQLAlchemy mesclando peso de cargas e espera na fila.
    """

    segundos_espera = cast(func.strftime("%s", agora), Integer) - cast(
        func.strftime("%s", Navio.data_solicitacao), Integer
    )
    horas_espera = segundos_espera / 3600.0
    bonus_tempo = horas_espera * 1000

    return func.coalesce(sq_cargas.c.score_cargas, 0) + func.coalesce(bonus_tempo, 0)


async def obter_proximo_da_fila(session):
    """
    Obtém em tempo ótimo O(1) o navio que tem mais prioridade (Maior Score).

    Args:
        session (Session): Conexão aberta com o banco.

    Returns:
        Navio | None: Apenas a instância do navio prioritário.
    """
    sq = criar_subquery_score_cargas()
    score_total = obter_expressao_score_total(sq, datetime.now())

    stmt = (
        select(Navio)
        .outerjoin(sq, Navio.imo_id == sq.c.navio_imo_id)
        .filter(Navio.status == StatusNavio.VALIDADO)
        .order_by(score_total.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def obter_fila_atracacao_dto(session) -> list:
    """
    Obtém a lista ordenada de navios na fila (status VALIDADO) como DTOs.
    """
    agora = datetime.now()
    sq = criar_subquery_score_cargas()
    score_total = obter_expressao_score_total(sq, agora)

    stmt = (
        select(Navio, score_total.label("score"))
        .options(joinedload(Navio.cargas))
        .outerjoin(sq, Navio.imo_id == sq.c.navio_imo_id)
        .filter(Navio.status == StatusNavio.VALIDADO)
        .order_by(score_total.desc())
    )

    result = await session.execute(stmt)
    resultados = result.unique().all()

    return [navio.to_dto(score=float(score)) for navio, score in resultados]
