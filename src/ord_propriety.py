from datetime import datetime
from cad import Navio, StatusNavio

PESOS_CATEGORIA = {
    "ULTRA_PERECIVEL": 10, # carnes, pescados, vacinas
    "ALTA_PERECIVEL": 7,   # frutas, laticínios
    "BAIXA_PERECIVEL": 3,  # grãos úmidos, Açucar
    "COMUM": 0             # minério, maquinário, fertilizantes (não perecível)
}

def calcular_score(navio: Navio) -> float:
    """Calcula o score de prioridade de um navio no banco de dados"""
    score_total = 0
    maior_grau_perecivel = 0

    # Base do score original por pesos de categoria
    for carga in navio.cargas:
        peso = PESOS_CATEGORIA.get(carga.categoria, 0)
        score_total += (carga.quantidade_toneladas * peso)
        
        if carga.eh_perecivel:
            if peso > maior_grau_perecivel:
                maior_grau_perecivel = peso
            
    # Regra de Negócio: Bônus massivo escalonado para perecíveis
    if maior_grau_perecivel > 0:
        score_total += (10000 * maior_grau_perecivel)
        
    # Regra Anti-Starvation: Bônus de espera no tempo (+50 por hora)
    if navio.data_solicitacao:
        tempo_espera = datetime.now() - navio.data_solicitacao
        horas_espera = tempo_espera.total_seconds() / 3600.0
        score_total += (horas_espera * 50)
        
    return score_total

def obter_proximo_da_fila(session):
    """Busca os navios validados, calcula seus scores e retorna o que deve atracar em seguida"""
    navios_validados = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).all()
    
    if not navios_validados:
        return None
        
    fila_ordenada = sorted(navios_validados, key=lambda n: calcular_score(n), reverse=True)
    return fila_ordenada[0]

def exibir_fila_atracacao(session):
    """
    Exibe a fila de atracação atual no terminal, ordenada por prioridade (score).
    Mostra navios com status VALIDADO e calcula o tempo de espera.
    """
    navios_validados = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).all()
    
    if not navios_validados:
        print("Aviso: A fila de atracação está vazia no momento (Nenhum navio VALIDADO).")
        return
        
    # Associa cada navio ao seu respectivo score e ordena de forma decrescente
    navios_com_score = [(navio, calcular_score(navio)) for navio in navios_validados]
    navios_com_score.sort(key=lambda x: x[1], reverse=True)
    
    # Imprime o cabeçalho da tabela
    print(f"\n{'POS':<4} | {'IMO':<12} | {'NOME DA EMBARCAÇÃO':<30} | {'COMPANHIA':<25} | {'SCORE':<12} | {'ESPERA'}")
    print("-" * 110)
    
    # Imprime as linhas
    for pos, (navio, score) in enumerate(navios_com_score, start=1):
        nome_exibicao = navio.nome if navio.nome else f"[Capitão] {navio.nome_capitao}"
        
        if navio.data_solicitacao:
            espera = datetime.now() - navio.data_solicitacao
            espera_str = str(espera).split('.')[0]  # Remove microsegundos para ficar limpo
        else:
            espera_str = "N/A"
            
        print(f"{pos:<4} | {navio.imo_id:<12} | {nome_exibicao:<30} | {navio.companhia[:25]:<25} | {score:<12.2f} | {espera_str}")
