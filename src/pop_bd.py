from faker import Faker
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Navio, Carga

# Configuração do Banco de Dados
ENGINE = create_engine("sqlite:///porto.db")
Base.metadata.create_all(ENGINE)

# Inicializa o Faker
fake = Faker('pt_BR')

# Mapeamento de cargas por categoria baseado em ord_propriety.py
MAPA_CARGAS = {
    'Vacinas': 'ULTRA_PERECIVEL',
    'Carne Bovina': 'ULTRA_PERECIVEL',
    'Peixes': 'ULTRA_PERECIVEL',
    'Frutas': 'ALTA_PERECIVEL',
    'Verduras': 'ALTA_PERECIVEL',
    'Grãos': 'BAIXA_PERECIVEL',
    'Biscoitos': 'BAIXA_PERECIVEL',
    'Petróleo': 'COMUM',
    'Minério de Ferro': 'COMUM',
    'Containers': 'COMUM',
    'Automóveis': 'COMUM',
    'Produtos Químicos': 'COMUM',
    'Gás Natural': 'COMUM',
    'Carvão': 'COMUM',
    'Eletrodomésticos': 'COMUM',
    'RTX 5090': 'COMUM'
}

def gerar_navios_fake(quantidade=10):
    """Gera instâncias de Navio com dados aleatórios e as salva no banco"""
    with Session(ENGINE) as session:
        print(f"Gerando e inserindo {quantidade} navios no banco de dados...")
        
        for _ in range(quantidade):
            novo_navio = Navio(
                imo_id = f"IMO{fake.unique.random_number(digits=7, fix_len=True)}",
                nome = fake.first_name().upper() + " " + fake.last_name().upper(),
                nome_capitao = fake.name(),
                companhia = fake.company()
            )
            
            num_cargas = random.randint(5, 10)
            total_toneladas = 0
            produtos_disponiveis = list(MAPA_CARGAS.keys())
            
            for _ in range(num_cargas):
                if total_toneladas >= 40:
                    break
                    
                toneladas = random.randint(1, 15)
                if total_toneladas + toneladas > 40:
                    toneladas = 40 - total_toneladas
                    
                descricao = random.choice(produtos_disponiveis)
                nova_carga = Carga(
                    descricao=descricao,
                    categoria=MAPA_CARGAS[descricao],
                    quantidade_toneladas=toneladas
                )
                novo_navio.cargas.append(nova_carga)
                total_toneladas += toneladas
                
            session.add(novo_navio)
        
        session.commit()
        print("Sucesso: Dados persistidos!")

def verificar_integridade():
    """Consulta o banco de dados para verificar se os dados foram inseridos corretamente"""
    print("\n--- Verificação de Integridade ---")
    with Session(ENGINE) as session:
        navios = session.query(Navio).all()
        total = len(navios)
        print(f"Total de navios no banco: {total}")
        
        if total > 0:
            print("Exemplo do primeiro registro recuperado:")
            primeiro = navios[0]
            print(f"ID: {primeiro.imo_id}")
            print(f"Capitão: {primeiro.nome_capitao}")
            print(f"Companhia: {primeiro.companhia}")
            print("Cargas no Manifesto:")
            soma_peso = 0
            for carga in primeiro.cargas:
                print(f"  - {carga.descricao} [{carga.categoria}] - {carga.quantidade_toneladas}T")
                soma_peso += carga.quantidade_toneladas
            print(f"Total Transportado: {soma_peso}T")
        else:
            print("Aviso: Nenhum dado encontrado no banco.")

if __name__ == "__main__":
    gerar_navios_fake(10)
    verificar_integridade()
