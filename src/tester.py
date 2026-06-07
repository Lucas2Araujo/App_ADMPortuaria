from ord_propriety import Carga, Navio

def executar_teste():
    print("Iniciando Cálculo...\n")

    navio1 = Navio(imo_id="A-001", nome="Navio da Virginia")
    navio1.adicionar_carga(Carga("Minério de Ferro", "COMUM", 5000))
    
    navio2 = Navio(imo_id="A-002", nome="Barco do Vini JR")
    navio2.adicionar_carga(Carga("Carnes Congeladas", "URGENTE_PERECIVEL", 200))
    navio2.adicionar_carga(Carga("Eletrônicos", "COMUM", 500))

    navio3 = Navio(imo_id="A-003", nome="Colheita do Tigrinho")
    navio3.adicionar_carga(Carga("Soja Úmida", "BAIXA_PERECIBILIDADE", 1000))
    navio3.adicionar_carga(Carga("Fertilizantes", "COMUM", 2000))

    navio4 = Navio(imo_id="A-004", nome="Faz o L")
    navio4.adicionar_carga(Carga("Frutas Frescas", "ALTA_PERECIBILIDADE", 300))
    navio4.adicionar_carga(Carga("Laticínios", "ALTA_PERECIBILIDADE", 100))

    fila_espera = [navio1, navio2, navio3, navio4]

    for navio in fila_espera:
        navio.calcular_score()

    fila_ordenada = sorted(fila_espera, key=lambda n: n.score_prioridade, reverse=True)

    print(f"{'POSIÇÃO':<10} | {'ID DO NAVIO':<12} | {'NOME DA EMBARCAÇÃO':<20} | {'SCORE'}")
    print("-" * 60)
    
    for posicao, navio in enumerate(fila_ordenada, start=1):
        print(f"{posicao:<10} | {navio.imo_id:<12} | {navio.nome:<20} | {navio.score_prioridade} pts")

if __name__ == "__main__":
    executar_teste()