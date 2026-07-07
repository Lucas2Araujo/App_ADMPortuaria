"""
Motor de Regras de Negócio e Fila de Atracação.

Possui as funções responsáveis por ordenar a fila de atracação dinamicamente
utilizando cálculos de pontuação baseados na perecibilidade e regras anti-starvation.

A pontuação (score) de cada navio é composta por dois componentes:

- **Score de carga**: peso em toneladas multiplicado pelo grau de perecibilidade
  da categoria, mais bônus fixo exponencial para cargas ultra-perecíveis.
- **Bônus de envelhecimento (anti-starvation)**: proporcional ao tempo de espera
  em horas, garantindo que navios sem carga perecível não aguardem indefinidamente.
"""

from datetime import datetime
from sqlalchemy import case, func, select, cast, Integer
from sqlalchemy.orm import joinedload, Session
from cad import Navio, Carga, StatusNavio

# Tabela de pesos por categoria de carga. Cargas sem perecibilidade recebem
# peso 0 e competem na fila apenas pelo bônus de envelhecimento por tempo de espera.
PESOS_CATEGORIA = {
    "URGENTE_PERECIVEL": 3,  # carnes, pescados, vacinas
    "ALTA_PERECIBILIDADE": 2,  # frutas, laticínios
    "BAIXA_PERECIBILIDADE": 1,  # grãos úmidos, Açucar
    "COMUM": 0,  # minério, maquinário, fertilizantes (não perecível)
}


def calcular_score(navio: Navio) -> float:
    """Calcula a pontuação de prioridade de um navio a partir de suas cargas.

    Args:
        navio (Navio): Instância ORM do navio com a relação ``cargas`` já carregada.

    Returns:
        float: Score total calculado. Valores mais altos indicam maior prioridade.
    """
    score_total = 0
    maior_grau_perecivel = 0

    for carga in navio.cargas:
        peso = PESOS_CATEGORIA.get(carga.categoria, 0)
        score_total += carga.quantidade_toneladas * peso

        # O bônus fixo é determinado pelo item mais urgente do manifesto.
        if carga.eh_perecivel and peso > maior_grau_perecivel:
            maior_grau_perecivel = peso

    if maior_grau_perecivel > 0:
        # Bônus de grandeza 10k garante prioridade absoluta para cargas perecíveis independentemente do volume.
        score_total += 10000 * maior_grau_perecivel

    if navio.data_solicitacao:
        tempo_espera = datetime.now() - navio.data_solicitacao
        horas_espera = tempo_espera.total_seconds() / 3600.0
        # Bônus de envelhecimento evita starvation de navios não-perecíveis.
        score_total += horas_espera * 1000

    return score_total


def criar_subquery_score_cargas():
    """Constrói a subquery SQL que agrega o score de cargas agrupado por navio.

    Returns:
        Subquery: Expressão SQLAlchemy contendo `navio_imo_id` e `score_cargas`.
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
    """Combina o score de cargas com o bônus de envelhecimento (anti-starvation) em SQL.

    Args:
        sq_cargas (Subquery): Resultado de `criar_subquery_score_cargas()`.
        agora (datetime): Timestamp do momento atual.

    Returns:
        ColumnElement: Expressão do score total do navio para `order_by()`.
    """
    segundos_espera = cast(func.strftime("%s", agora), Integer) - cast(
        func.strftime("%s", Navio.data_solicitacao), Integer
    )
    horas_espera = segundos_espera / 3600.0
    # Fator 1000 escala 1 hora de espera para 1000 pontos.
    bonus_tempo = horas_espera * 1000

    # coalesce protege cálculos contra valores nulos de navios sem cargas ou sem data.
    return func.coalesce(sq_cargas.c.score_cargas, 0) + func.coalesce(bonus_tempo, 0)


async def obter_proximo_da_fila(session):
    """(Co-rotina) Retorna a instância do navio com maior score da fila (status VALIDADO).

    Args:
        session (AsyncSession): Sessão assíncrona.

    Returns:
        Navio | None: Instância do navio mais prioritário ou None.
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
    """(Co-rotina) Retorna a fila completa de navios VALIDADOS, em ordem decrescente de score.

    Args:
        session (AsyncSession): Sessão assíncrona.

    Returns:
        list[NavioDTO]: Lista de DTOs da fila ordenada.
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
    # unique() desduplica resultados gerados pelo joinedload das cargas.
    resultados = result.unique().all()

    return [navio.to_dto(score=float(score)) for navio, score in resultados]
