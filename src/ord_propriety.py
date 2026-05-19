PESOS_CATEGORIA = {
    "ULTRA_PERECIVEL": 10, # carnes, pscados, vacinas
    "ALTA_PERECIVEL": 7,   # frutas, laticínios
    "BAIXA_PERECIVEL": 3,  #grãos úmidos, Açucar
    "COMUM": 0             # minério, maquinário, fertilizantes (não perecível)
}

class Carga:
    def __init__(self, desc, categoria, qtd_toneladas):
        self.desc = desc
        self.categoria = categoria
        self.quantidade = qtd_toneladas

class Navio:
    def __init__(self, imo_id, nome):
        self.imo_id = imo_id
        self.nome = nome
        self.manifesto_carga = [] 
        self.score_prioridade = 0 

    def adicionar_carga(self, carga):
        self.manifesto_carga.append(carga)

    def calcular_score(self):
        # Soma ponderada pelo seus repectivos pesos e níveis de perecividade e possíveis danos
        score_total = 0
        for carga in self.manifesto_carga:
            peso = PESOS_CATEGORIA.get(carga.categoria, 0)
            score_total += (carga.quantidade * peso)
        
        self.score_prioridade = score_total
        return self.score_prioridade
