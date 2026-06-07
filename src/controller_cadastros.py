from datetime import datetime
from cad import Navio, Carga, StatusNavio

def solicitar_pre_cadastro(session, imo: str, nome: str, capitao: str, companhia: str, carga_desc: str, categoria: str, peso: int, eh_perecivel: bool, possui_documentos: bool):
    """
    Simula a ação do Capitão. Realiza o pré-cadastro de um navio informando 
    os dados da embarcação e o seu manifesto de carga.
    """
    # O construtor já possui defaults definidos no BD, mas reforçamos a regra aqui
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
        dAlfandega=possui_documentos  # Mapeamos a flag para o campo de documentos da Alfândega
    )
    
    novo_navio.cargas.append(nova_carga)
    session.add(novo_navio)
    session.commit()
    
    print(f"[CAPITÃO] Pré-cadastro realizado: Navio '{nome}' ({imo}) adicionado com status PENDENTE.")
    return novo_navio

def auditar_solicitacoes_pendentes(session):
    """
    Simula a ação do Admin do Porto. Audita navios pendentes e altera o status
    para VALIDADO ou REJEITADO baseado na documentação da carga.
    """
    navios_pendentes = session.query(Navio).filter(Navio.status == StatusNavio.PENDENTE).all()
    
    if not navios_pendentes:
        print("[ADMIN] Não há solicitações pendentes para auditoria no momento.")
        return
        
    for navio in navios_pendentes:
        # Verifica se há cargas pendentes de classificação
        for carga in navio.cargas:
            if carga.categoria == 'OUTROS_PENDENTE':
                print(f"Atenção: O navio {navio.nome} possui uma carga não classificada: [{carga.descricao}].")
                print("[1] Ultra Perecível | [2] Alta Perecibilidade | [3] Baixa Perecibilidade | [4] Comum")
                while True:
                    escolha = input("Classifique a carga (1-4): ").strip()
                    if escolha == '1':
                        carga.categoria, carga.eh_perecivel = 'ULTRA_PERECIVEL', True
                        break
                    elif escolha == '2':
                        carga.categoria, carga.eh_perecivel = 'ALTA_PERECIVEL', True
                        break
                    elif escolha == '3':
                        carga.categoria, carga.eh_perecivel = 'BAIXA_PERECIVEL', True
                        break
                    elif escolha == '4':
                        carga.categoria, carga.eh_perecivel = 'COMUM', False
                        break
                    print("Opção inválida. Tente novamente.")
                session.commit()

        # Verifica se alguma carga do navio não possui os documentos (dAlfandega == False)
        if any(not carga.dAlfandega for carga in navio.cargas):
            navio.status = StatusNavio.REJEITADO
            print(f"[ADMIN] AVISO: Navio '{navio.nome}' ({navio.imo_id}) REJEITADO. Documentação da carga incompleta.")
        else:
            navio.status = StatusNavio.VALIDADO
            print(f"[ADMIN] SUCESSO: Navio '{navio.nome}' ({navio.imo_id}) VALIDADO. Aprovado para entrar na Fila de Atracação.")
            
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