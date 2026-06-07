from datetime import datetime
from cad import Vaga, Atracacao, StatusVaga, StatusNavio, Navio
from ord_propriety import obter_proximo_da_fila

def atracar_navio(session):
    """
    Busca o próximo navio da fila e o aloca na primeira vaga disponível.
    Altera o status do navio, da vaga e gera o histórico de atracação.
    """
    navio = obter_proximo_da_fila(session)
    if not navio:
        print("Nenhum navio aguardando na fila com status VALIDADO.")
        return None
        
    vaga = session.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).first()
    if not vaga:
        print("Nenhuma vaga livre no momento para atracação.")
        return None
        
    # Atualiza status
    navio.status = StatusNavio.ATRACADO
    vaga.status = StatusVaga.OCUPADA
    
    # Registra o histórico
    nova_atracacao = Atracacao(
        navio_imo_id=navio.imo_id,
        vaga_id=vaga.id,
        data_hora_inicio=datetime.now()
    )
    
    session.add(nova_atracacao)
    session.commit()
    
    print(f"Navio {navio.imo_id} ('{navio.nome}') atracado na Vaga {vaga.id} com sucesso.")
    return nova_atracacao

def registrar_desatracacao(session, imo_id: str):
    """
    Busca a atracação em aberto para o navio, registra o fim da operação
    e libera a vaga, mudando o status do navio para finalizado.
    """
    atracacao = session.query(Atracacao).filter(
        Atracacao.navio_imo_id == imo_id,
        Atracacao.data_hora_fim.is_(None)
    ).first()
    
    if not atracacao:
        print(f"Não há atracação ativa (em aberto) para o navio {imo_id}.")
        return None
        
    atracacao.data_hora_fim = datetime.now()
    
    # Atualiza as entidades relacionadas
    vaga = session.query(Vaga).filter(Vaga.id == atracacao.vaga_id).first()
    if vaga:
        vaga.status = StatusVaga.LIVRE
        
    navio = session.query(Navio).filter(Navio.imo_id == imo_id).first()
    if navio:
        navio.status = StatusNavio.FINALIZADO
        
    session.commit()
    
    print(f"Desatracação do navio {imo_id} registrada. Vaga {atracacao.vaga_id} agora está LIVRE.")
    return atracacao

def exibir_painel_vagas(session):
    """
    Exibe o painel atualizado com todas as vagas cadastradas.
    Mostra qual navio está ocupando a vaga, caso não esteja livre.
    """
    vagas = session.query(Vaga).all()
    
    if not vagas:
        print("Nenhuma vaga cadastrada no sistema.")
        return
        
    total_vagas = len(vagas)
    vagas_livres = sum(1 for v in vagas if v.status == StatusVaga.LIVRE)
    vagas_ocupadas = total_vagas - vagas_livres
    
    print("\n" + "=" * 70)
    print("DASHBOARD DO PORTO - STATUS DAS VAGAS")
    print(f"Total: {total_vagas} | Disponíveis: {vagas_livres} | Ocupadas: {vagas_ocupadas}")
    print("=" * 70)

    for vaga in vagas:
        if vaga.status == StatusVaga.OCUPADA:
            atracacao = session.query(Atracacao).filter(
                Atracacao.vaga_id == vaga.id,
                Atracacao.data_hora_fim.is_(None)
            ).first()
            if atracacao:
                navio = session.query(Navio).filter(Navio.imo_id == atracacao.navio_imo_id).first()
                nome_navio = navio.nome if navio and navio.nome else "Desconhecido"
                data_inicio = atracacao.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S") if atracacao.data_hora_inicio else "N/A"
                print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga:<15}] - [OCUPADA] -> Navio: {nome_navio} (IMO: {navio.imo_id}) - Atracado desde: {data_inicio}")
            else:
                print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga:<15}] - [OCUPADA] -> (Sem atracação ativa registrada)")
        else:
            print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga:<15}] - [LIVRE]")

def exibir_log_operacoes(session):
    """
    Exibe o histórico de atracações e desatracações, ordenado dos mais recentes para os mais antigos.
    """
    print(f"\n{'--- LOG DE OPERAÇÕES (HISTÓRICO) ---'}")
    operacoes = session.query(Atracacao).order_by(Atracacao.data_hora_inicio.desc()).all()
    
    print(f"{'ID':<4} | {'NAVIO (IMO)':<15} | {'VAGA':<6} | {'INÍCIO':<20} | {'FIM':<20}")
    print("-" * 75)
    for op in operacoes:
        inicio = op.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S") if op.data_hora_inicio else "N/A"
        fim = op.data_hora_fim.strftime("%Y-%m-%d %H:%M:%S") if op.data_hora_fim else "Em andamento"
        print(f"{op.id:<4} | {op.navio_imo_id:<15} | {op.vaga_id:<6} | {inicio:<20} | {fim:<20}")