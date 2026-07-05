"""
Módulo de Controladores de Cadastro e Auditoria.

Responsável pelas funções que interagem com a base de dados para pré-cadastro
de navios, classificação de cargas e processos de auditoria documental.
"""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from cad import Navio, Carga, StatusNavio
from dto import NavioDTO


class CargaNaoClassificadaError(Exception):
    """Exceção levantada quando uma carga precisa ser classificada interativamente pela apresentação."""
    def __init__(self, imo_id: str, navio_nome: str, carga_id: int, carga_descricao: str):
        self.imo_id = imo_id
        self.navio_nome = navio_nome
        self.carga_id = carga_id
        self.carga_descricao = carga_descricao
        super().__init__(f"A carga '{carga_descricao}' (ID: {carga_id}) do navio {navio_nome} ({imo_id}) precisa de classificação.")


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
    """
    Realiza o pré-cadastro de um navio informando os dados da embarcação e o seu manifesto de carga.
    """
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
    """
    Classifica uma carga específica com a categoria e perecibilidade fornecidas.
    """
    result = await session.execute(select(Carga).filter(Carga.id == carga_id))
    carga = result.scalars().first()
    if not carga:
        raise ValueError("Carga não encontrada.")
    carga.categoria = categoria
    carga.eh_perecivel = eh_perecivel
    await session.commit()


def _auditar_documentacao_navio(navio):
    """
    Audita e verifica a documentação de um navio.
    """
    if any(not carga.documento_alfandega for carga in navio.cargas):
        navio.status = StatusNavio.REJEITADO
    else:
        navio.status = StatusNavio.VALIDADO


async def auditar_solicitacoes_pendentes(session) -> list[NavioDTO]:
    """
    Audita todos os navios PENDENTES.
    Altera o status para VALIDADO ou REJEITADO baseado na documentação aduaneira.
    Se encontrar cargas não classificadas, lança CargaNaoClassificadaError para ser resolvido na camada superior.
    """
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
        for carga in navio.cargas:
            if carga.categoria == "OUTROS_PENDENTE":
                raise CargaNaoClassificadaError(
                    imo_id=navio.imo_id,
                    navio_nome=navio.nome,
                    carga_id=carga.id,
                    carga_descricao=carga.descricao
                )

        _auditar_documentacao_navio(navio)
        auditos.append(navio.to_dto())

    await session.commit()
    return auditos


async def excluir_registro_navio(session, imo_id: str):
    """
    Exclui o registro de um navio e suas cargas associadas do banco de dados.
    """
    result = await session.execute(select(Navio).filter(Navio.imo_id == imo_id))
    navio = result.scalars().first()
    if not navio:
        raise ValueError(f"Nenhum navio encontrado com o IMO ID '{imo_id}'.")

    if navio.status == StatusNavio.ATRACADO:
        raise ValueError(f"Não é possível excluir o navio '{navio.nome}' pois ele está atualmente ATRACADO.")

    await session.delete(navio)
    await session.commit()


async def editar_registro_navio(session, imo_id: str, nome: str, capitao: str, companhia: str) -> NavioDTO:
    """
    Edita os dados cadastrais básicos de um navio.
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
    """
    Retorna uma lista de DTOs dos navios com status PENDENTE.
    """
    stmt = (
        select(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.status == StatusNavio.PENDENTE)
    )
    result = await session.execute(stmt)
    pendentes = result.scalars().unique().all()
    return [navio.to_dto() for navio in pendentes]


async def obter_todos_navios_dto(session) -> list[NavioDTO]:
    """
    Retorna todos os navios cadastrados como DTOs.
    """
    stmt = (
        select(Navio)
        .options(joinedload(Navio.cargas))
    )
    result = await session.execute(stmt)
    navios = result.scalars().unique().all()
    return [navio.to_dto() for navio in navios]


async def auditar_navio_individual(session, imo_id: str, acao: str) -> NavioDTO:
    """
    Aprova ou rejeita uma solicitação individual de navio.
    """
    stmt = (
        select(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.imo_id == imo_id)
    )
    result = await session.execute(stmt)
    navio = result.scalars().first()
    if not navio:
        raise ValueError("Navio não encontrado.")

    if acao == "APROVAR":

        if any(not c.documento_alfandega for c in navio.cargas):
            navio.status = StatusNavio.REJEITADO
        else:
            navio.status = StatusNavio.VALIDADO
    elif acao == "REJEITAR":
        navio.status = StatusNavio.REJEITADO

    await session.commit()
    return navio.to_dto()



