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

    COR_VERDE = "\033[92m"
    COR_VERMELHA = "\033[91m"
    RESET = "\033[0m"

    for vaga in vagas:
        if vaga.status == StatusVaga.OCUPADA:
            atracacao = session.query(Atracacao).filter(
                Atracacao.vaga_id == vaga.id,
                Atracacao.data_hora_fim.is_(None)
            ).first()
            if atracacao:
                navio = session.query(Navio).filter(Navio.imo_id == atracacao.navio_imo_id).first()
                nome_navio = navio.nome if navio else "Desconhecido"
                data_inicio = atracacao.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S") if atracacao.data_hora_inicio else "N/A"
                print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERMELHA}[OCUPADA]{RESET} -> Navio: {nome_navio} (IMO: {navio.imo_id}) - Atracado desde: {data_inicio}")
            else:
                print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERMELHA}[OCUPADA]{RESET} -> (Sem atracação ativa registrada)")
        else:
            print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERDE}[LIVRE]{RESET}")

def exibir_log_operacoes(session):
    """
    Exibe o histórico de atracações e desatracações, ordenado dos mais recentes para os mais antigos.
    """
    print(f"\n{'--- LOG DE OPERAÇÕES (HISTÓRICO) ---'}")
    atracacoes = session.query(Atracacao).all()
    
    if not atracacoes:
        print("Nenhuma operação registrada no histórico.")
        return
        
    eventos = []
    for op in atracacoes:
        eventos.append({
            'id': op.id,
            'tipo': 'ATRACAO',
            'navio_imo_id': op.navio_imo_id,
            'vaga_id': op.vaga_id,
            'data_hora': op.data_hora_inicio
        })
        if op.data_hora_fim:
            eventos.append({
                'id': op.id,
                'tipo': 'DESATRACAO',
                'navio_imo_id': op.navio_imo_id,
                'vaga_id': op.vaga_id,
                'data_hora': op.data_hora_fim
            })
            
    # Ordena os eventos do mais recente para o mais antigo
    eventos.sort(key=lambda x: x['data_hora'], reverse=True)

    COR_VERDE = "\033[92m"
    COR_VERMELHA = "\033[91m"
    RESET = "\033[0m"

    print(f"{'DATA/HORA':<20} | {'EVENTO':<16} | {'NAVIO (IMO)':<15} | {'VAGA':<7} | {'OP ID'}")
    print("-" * 77)
    for ev in eventos:
        data_str = ev['data_hora'].strftime("%Y-%m-%d %H:%M:%S")
        imo = ev['navio_imo_id']
        vaga = ev['vaga_id']
        op_id = ev['id']
        
        if ev['tipo'] == 'ATRACAO':
            evento_str = f"{COR_VERDE}{'[+] ATRACAÇÃO':<16}{RESET}"
        else:
            evento_str = f"{COR_VERMELHA}{'[-] DESATRACAÇÃO':<16}{RESET}"
            
        print(f"{data_str:<20} | {evento_str} | {imo:<15} | Vaga {vaga:<2} | OP-{op_id:03d}")