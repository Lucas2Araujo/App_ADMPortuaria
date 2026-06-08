from datetime import datetime
from sqlalchemy.orm import joinedload
from cad import Navio, Carga, StatusNavio

def solicitar_pre_cadastro(session, imo: str, nome: str, capitao: str, companhia: str, carga_desc: str, categoria: str, peso: int, eh_perecivel: bool, possui_documentos: bool):
    """
    Simula a ação do Capitão. Realiza o pré-cadastro de um navio informando 
    os dados da embarcação e o seu manifesto de carga.
    """
    novo_navio = Navio(
        imo_id=imo,
        nome=nome,
        nome_capitao=capitao,
        companhia=companhia,
        status=StatusNavio.PENDENTE,
        data_solicitacao=datetime.now()
    )
    
    nova_carga = Carga(
        descricao=carga_desc,
        categoria=categoria,
        quantidade_toneladas=peso,
        eh_perecivel=eh_perecivel,
        documento_alfandega=possui_documentos
    )
    
    novo_navio.cargas.append(nova_carga)
    session.add(novo_navio)
    session.commit()
    
    print(f"[CAPITÃO] Pré-cadastro realizado: Navio '{nome}' ({imo}) adicionado com status PENDENTE.")
    return novo_navio

def _solicitar_classificacao_carga(carga, nome_navio):
    """Solicita interativamente a classificação de uma carga não categorizada."""
    print(f"Atenção: O navio {nome_navio} possui uma carga não classificada: [{carga.descricao}].")
    print("[1] Ultra Perecível | [2] Alta Perecibilidade | [3] Baixa Perecibilidade | [4] Comum")
    
    opcoes = {
        '1': ('URGENTE_PERECIVEL', True),
        '2': ('ALTA_PERECIBILIDADE', True),
        '3': ('BAIXA_PERECIBILIDADE', True),
        '4': ('COMUM', False)
    }
    
    while True:
        escolha = input("Classifique a carga (1-4): ").strip()
        if escolha in opcoes:
            carga.categoria, carga.eh_perecivel = opcoes[escolha]
            break
        print("Opção inválida. Tente novamente.")

def _auditar_documentacao_navio(navio):
    """Verifica a documentação do navio e atualiza seu status."""
    # Regra de Negócio: A ausência de documentação aduaneira de qualquer carga bloqueia a entrada do navio na fila de atracação.
    if any(not carga.documento_alfandega for carga in navio.cargas):
        navio.status = StatusNavio.REJEITADO
        print(f"[ADMIN] AVISO: Navio '{navio.nome}' ({navio.imo_id}) REJEITADO. Documentação da carga incompleta.")
    else:
        navio.status = StatusNavio.VALIDADO
        print(f"[ADMIN] SUCESSO: Navio '{navio.nome}' ({navio.imo_id}) VALIDADO. Aprovado para entrar na Fila de Atracação.")

def auditar_solicitacoes_pendentes(session):
    """
    Simula a ação do Admin do Porto. Audita navios pendentes e altera o status
    para VALIDADO ou REJEITADO baseado na documentação da carga.
    """
    navios_pendentes = session.query(Navio).options(joinedload(Navio.cargas)).filter(Navio.status == StatusNavio.PENDENTE).all()
    
    if not navios_pendentes:
        print("[ADMIN] Não há solicitações pendentes para auditoria no momento.")
        return
        
    for navio in navios_pendentes:
        for carga in navio.cargas:
            if carga.categoria == 'OUTROS_PENDENTE':
                _solicitar_classificacao_carga(carga, navio.nome)
                session.commit()

        _auditar_documentacao_navio(navio)
            
    session.commit()

def excluir_registro_navio(session, imo_id: str):
    """
    Exclui o registro de um navio e suas cargas associadas do banco de dados.
    """
    navio = session.query(Navio).filter(Navio.imo_id == imo_id).first()
    if navio:
        nome_navio = navio.nome
        session.delete(navio)
        session.commit()
        print(f"[ADMIN] Sucesso: Registro do navio '{nome_navio}' ({imo_id}) foi excluído definitivamente.")
    else:
        print(f"[ADMIN] Erro: Nenhum navio encontrado com o IMO ID '{imo_id}'.")