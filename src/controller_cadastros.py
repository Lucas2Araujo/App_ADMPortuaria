"""
Módulo de Controladores de Cadastro e Auditoria.

Responsável pelas funções que interagem com a base de dados para pré-cadastro
de navios, classificação de cargas e processos de auditoria documental.
"""

from datetime import datetime
from sqlalchemy.orm import joinedload
from cad import Navio, Carga, StatusNavio


def solicitar_pre_cadastro(
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
):
    """
    Simula a ação do Capitão. Realiza o pré-cadastro de um navio informando
    os dados da embarcação e o seu manifesto de carga.

    Args:
        session (Session): Sessão ativa do SQLAlchemy.
        imo (str): O ID IMO único do navio.
        nome (str): Nome do navio.
        capitao (str): Nome do responsável pelo navio.
        companhia (str): Empresa proprietária da frota.
        carga_desc (str): Descrição do manifesto de carga.
        categoria (str): Classificação predefinida da carga.
        peso (int): Quantidade total em toneladas.
        eh_perecivel (bool): Define se o multiplicador de perecibilidade será aplicado.
        possui_documentos (bool): Define se a carga possui liberação alfandegária.

    Returns:
        Navio: O objeto `Navio` recém-cadastrado na base de dados com status `PENDENTE`.
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
    session.commit()

    print(
        f"[CAPITÃO] Pré-cadastro realizado: Navio '{nome}' ({imo}) adicionado com status PENDENTE."
    )
    return novo_navio


def _solicitar_classificacao_carga(carga, nome_navio):
    """
    Solicita interativamente a classificação de uma carga com categoria 'OUTROS_PENDENTE' no terminal.

    Args:
        carga (Carga): Objeto carga que não possui categoria definida (Outros).
        nome_navio (str): Nome do navio, usado apenas para log no terminal.
    """
    print(
        f"Atenção: O navio {nome_navio} possui uma carga não classificada: [{carga.descricao}]."
    )
    print(
        "[1] Ultra Perecível | [2] Alta Perecibilidade | [3] Baixa Perecibilidade | [4] Comum"
    )

    opcoes = {
        "1": ("URGENTE_PERECIVEL", True),
        "2": ("ALTA_PERECIBILIDADE", True),
        "3": ("BAIXA_PERECIBILIDADE", True),
        "4": ("COMUM", False),
    }

    while True:
        escolha = input("Classifique a carga (1-4): ").strip()
        if escolha in opcoes:
            carga.categoria, carga.eh_perecivel = opcoes[escolha]
            break
        print("Opção inválida. Tente novamente.")


def _auditar_documentacao_navio(navio):
    """
    Audita e verifica a documentação de um navio.

    Args:
        navio (Navio): A instância do navio sendo analisada. Altera o status para `VALIDADO` se possuir documentos ou `REJEITADO` caso falte de alguma carga.
        Após a auditoria, o navio é definido como `VALIDADO` (se todos os documentos estiverem ok) ou `REJEITADO` (se houver pendências).
    """
    # Regra de Negócio: A ausência de documentação aduaneira de qualquer carga bloqueia a entrada do navio na fila de atracação.
    if any(not carga.documento_alfandega for carga in navio.cargas):
        navio.status = StatusNavio.REJEITADO
        print(
            f"[ADMIN] AVISO: Navio '{navio.nome}' ({navio.imo_id}) REJEITADO. Documentação da carga incompleta."
        )
    else:
        navio.status = StatusNavio.VALIDADO
        print(
            f"[ADMIN] SUCESSO: Navio '{navio.nome}' ({navio.imo_id}) VALIDADO. Aprovado para entrar na Fila de Atracação."
        )


def auditar_solicitacoes_pendentes(session):
    """
    Simula a ação do Administrador do Porto auditando todos os navios PENDENTES.
    Altera o status para VALIDADO ou REJEITADO baseado na documentação aduaneira.

    Args:
        session (Session): Sessão ativa do SQLAlchemy conectada ao banco de dados.
    """
    navios_pendentes = (
        session.query(Navio)
        .options(joinedload(Navio.cargas))
        .filter(Navio.status == StatusNavio.PENDENTE)
        .all()
    )

    if not navios_pendentes:
        print("[ADMIN] Não há solicitações pendentes para auditoria no momento.")
        return

    for navio in navios_pendentes:
        for carga in navio.cargas:
            if carga.categoria == "OUTROS_PENDENTE":
                _solicitar_classificacao_carga(carga, navio.nome)
                session.commit()

        _auditar_documentacao_navio(navio)

    session.commit()


def excluir_registro_navio(session, imo_id: str):
    """
    Exclui o registro de um navio e suas cargas associadas do banco de dados.

    Args:
        session (Session): Sessão ativa do banco de dados.
        imo_id (str): Identificador IMO do Navio alvo da exclusão.
    """
    navio = session.query(Navio).filter(Navio.imo_id == imo_id).first()
    if navio:
        if navio.status == StatusNavio.ATRACADO:
            print(
                f"[ADMIN] Erro: Não é possível excluir o navio '{navio.nome}' ({imo_id}) pois ele está atualmente ATRACADO. Desatraque-o primeiro."
            )
            return

        nome_navio = navio.nome
        session.delete(navio)
        session.commit()
        print(
            f"[ADMIN] Sucesso: Registro do navio '{nome_navio}' ({imo_id}) foi excluído definitivamente."
        )
    else:
        print(f"[ADMIN] Erro: Nenhum navio encontrado com o IMO ID '{imo_id}'.")
