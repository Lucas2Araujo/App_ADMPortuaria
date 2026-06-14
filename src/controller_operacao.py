"""
Módulo Controlador de Operações de Fila e Atracação.

Este módulo processa a movimentação de navios, atracação em vagas livres e
a geração de histórico (logs) das operações em tempo real.
"""
from datetime import datetime
from cad import Vaga, Atracacao, StatusVaga, StatusNavio, Navio
from ord_propriety import obter_proximo_da_fila

COR_VERDE = "\033[92m"
COR_VERMELHA = "\033[91m"
RESET = "\033[0m"

def atracar_navio(session):
    """
    Busca o próximo navio da fila e o aloca na primeira vaga disponível.
    Altera o status do navio, da vaga e gera o histórico de atracação.

    Args:
        session (Session): Sessão ativa do SQLAlchemy conectada ao banco de dados.

    Returns:
        Atracacao | None: O objeto `Atracacao` recém-registrado, ou `None` se a atracação falhar.
    """
    navio = obter_proximo_da_fila(session)
    if not navio:
        print("Nenhum navio aguardando na fila com status VALIDADO.")
        return None
        
    vaga = session.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).first()
    if not vaga:
        print("Nenhuma vaga livre no momento para atracação.")
        return None
        
    navio.status = StatusNavio.ATRACADO
    vaga.status = StatusVaga.OCUPADA
    
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

    Args:
        session (Session): Sessão ativa do SQLAlchemy.
        imo_id (str): O código IMO do navio que deve realizar a desatracação.

    Returns:
        Atracacao | None: O objeto `Atracacao` finalizado, ou `None` caso não encontre atracação ativa.
    """
    atracacao = session.query(Atracacao).filter(
        Atracacao.navio_imo_id == imo_id,
        Atracacao.data_hora_fim.is_(None)
    ).first()
    
    if not atracacao:
        print(f"Não há atracação ativa (em aberto) para o navio {imo_id}.")
        return None
        
    atracacao.data_hora_fim = datetime.now()
    
    vaga = session.query(Vaga).filter(Vaga.id == atracacao.vaga_id).first()
    if vaga:
        vaga.status = StatusVaga.LIVRE
        
    navio = session.query(Navio).filter(Navio.imo_id == imo_id).first()
    if navio:
        navio.status = StatusNavio.FINALIZADO
        
    session.commit()
    
    print(f"Desatracação do navio {imo_id} registrada. Vaga {atracacao.vaga_id} agora está LIVRE.")
    return atracacao

def _imprimir_cabecalho_dashboard(total_vagas, vagas_livres, vagas_ocupadas):
    """
    Imprime o cabeçalho formatado para o dashboard de vagas.

    Args:
        total_vagas (int): Número total de vagas cadastradas.
        vagas_livres (int): Número de vagas atualmente livres.
        vagas_ocupadas (int): Número de vagas atualmente ocupadas.
    """
    print("\n" + "=" * 70)
    print("DASHBOARD DO PORTO - STATUS DAS VAGAS")
    print(f"Total: {total_vagas} | Disponíveis: {vagas_livres} | Ocupadas: {vagas_ocupadas}")
    print("=" * 70)

def _imprimir_detalhe_vaga(vaga, mapa_atracacoes, mapa_navios, COR_VERDE, COR_VERMELHA, RESET):
    """
    Imprime os detalhes de uma única vaga, indicando seu status e, se ocupada,
    o navio correspondente.

    Args:
        vaga (Vaga): Objeto da vaga a ser exibida.
        mapa_atracacoes (dict): Dicionário mapeando ID da vaga para o objeto Atracacao ativa.
        mapa_navios (dict): Dicionário mapeando IMO do navio para o objeto Navio.
        COR_VERDE (str): Código ANSI para cor verde.
        COR_VERMELHA (str): Código ANSI para cor vermelha.
        RESET (str): Código ANSI para resetar a cor do terminal.
    """
    if vaga.status != StatusVaga.OCUPADA:
        print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERDE}[LIVRE]{RESET}")
        return

    atracacao = mapa_atracacoes.get(vaga.id)
    if not atracacao:
        print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERMELHA}[OCUPADA]{RESET} -> (Sem atracação ativa registrada)")
        return

    navio = mapa_navios.get(atracacao.navio_imo_id)
    nome_navio = navio.nome if navio else "Desconhecido"
    data_inicio = atracacao.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S") if atracacao.data_hora_inicio else "N/A"
    print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {COR_VERMELHA}[OCUPADA]{RESET} -> Navio: {nome_navio} (IMO: {navio.imo_id}) - Atracado desde: {data_inicio}")

def exibir_painel_vagas(session):
    """
    Exibe o painel atualizado com todas as vagas cadastradas.
    Mostra qual navio está ocupando a vaga, caso não esteja livre.

    Args:
        session (Session): Sessão ativa do banco de dados.
    """
    vagas = session.query(Vaga).all()
    
    if not vagas:
        print("Nenhuma vaga cadastrada no sistema.")
        return
        
    total_vagas = len(vagas)
    vagas_livres = sum(1 for v in vagas if v.status == StatusVaga.LIVRE)
    vagas_ocupadas = total_vagas - vagas_livres
    
    _imprimir_cabecalho_dashboard(total_vagas, vagas_livres, vagas_ocupadas)

    atracacoes_ativas = session.query(Atracacao).filter(Atracacao.data_hora_fim.is_(None)).all()
    mapa_atracacoes = {a.vaga_id: a for a in atracacoes_ativas}
    imos_ativos = [a.navio_imo_id for a in atracacoes_ativas]
    
    navios = session.query(Navio).filter(Navio.imo_id.in_(imos_ativos)).all() if imos_ativos else []
    mapa_navios = {n.imo_id: n for n in navios}

    for vaga in vagas:
        _imprimir_detalhe_vaga(vaga, mapa_atracacoes, mapa_navios, COR_VERDE, COR_VERMELHA, RESET)

def exibir_log_operacoes(session):
    """
    Busca e exibe o histórico cronológico de todas as atracações e desatracações 
    que ocorreram no porto.
    
    Args:
        session (Session): Sessão ativa do banco de dados.
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
            
    eventos.sort(key=lambda x: x['data_hora'], reverse=True)

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