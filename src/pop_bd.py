from faker import Faker
import secrets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Navio, Carga, StatusNavio, Vaga, StatusVaga

gerar_random = secrets.SystemRandom()

ENGINE = create_engine("sqlite:///porto.db")
Base.metadata.create_all(ENGINE)

fake = Faker("pt_BR")

MAPA_CARGAS = {
    "Vacinas": "URGENTE_PERECIVEL",
    "Carne Bovina": "URGENTE_PERECIVEL",
    "Peixes": "URGENTE_PERECIVEL",
    "Frutas": "ALTA_PERECIBILIDADE",
    "Verduras": "ALTA_PERECIBILIDADE",
    "Grãos": "BAIXA_PERECIBILIDADE",
    "Biscoitos": "BAIXA_PERECIBILIDADE",
    "Petróleo": "COMUM",
    "Minério de Ferro": "COMUM",
    "Containers": "COMUM",
    "Automóveis": "COMUM",
    "Produtos Químicos": "COMUM",
    "Gás Natural": "COMUM",
    "Carvão": "COMUM",
    "Eletrodomésticos": "COMUM",
    "RTX 5090": "COMUM",
}


def gerar_navios_fake(session, quantidade=10):
    """Gera instâncias de Navio com dados aleatórios e as salva no banco"""
    print(f"Gerando e inserindo {quantidade} navios no banco de dados...")

    for _ in range(quantidade):
        novo_navio = Navio(
            imo_id=f"IMO{fake.unique.random_number(digits=7, fix_len=True)}",
            nome=fake.first_name().upper() + " " + fake.last_name().upper(),
            nome_capitao=fake.name(),
            companhia=fake.company(),
            status=gerar_random.choice([StatusNavio.PENDENTE, StatusNavio.VALIDADO]),
        )

        num_cargas = gerar_random.randint(5, 10)
        total_toneladas = 0
        produtos_disponiveis = list(MAPA_CARGAS.keys())

        for _ in range(num_cargas):
            if total_toneladas >= 80:
                break

            toneladas = gerar_random.randint(1, 15)
            if total_toneladas + toneladas > 80:
                toneladas = 80 - total_toneladas

            descricao = gerar_random.choice(produtos_disponiveis)
            categoria = MAPA_CARGAS[descricao]
            eh_perecivel = categoria in [
                "URGENTE_PERECIVEL",
                "ALTA_PERECIBILIDADE",
                "BAIXA_PERECIBILIDADE",
            ]
            nova_carga = Carga(
                descricao=descricao,
                categoria=categoria,
                quantidade_toneladas=toneladas,
                eh_perecivel=eh_perecivel,
                documento_alfandega=gerar_random.choice([True, True, True, False]),
            )
            novo_navio.cargas.append(nova_carga)
            total_toneladas += toneladas

        session.add(novo_navio)

    session.commit()
    print("Sucesso: Dados persistidos!")


def verificar_integridade():
    """Consulta o banco de dados paraverificar se os dados foram inseridos corretamente"""
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
                print(
                    f"  - {carga.descricao} [{carga.categoria}] - {carga.quantidade_toneladas}T"
                )
                soma_peso += carga.quantidade_toneladas
            print(f"Total Transportado: {soma_peso}T")
        else:
            print("Aviso: Nenhum dado encontrado no banco.")


def gerar_vagas_iniciais(session, quantidade: int = 5):
    """Verifica se existem vagas. Se não, cria a quantidade especificada com nomes genéricos."""
    if session.query(Vaga).count() == 0:
        print(f"\nCriando {quantidade} vagas iniciais...")
        for i in range(1, quantidade + 1):
            vaga = Vaga(tipo_vaga=f"Terminal {i}", status=StatusVaga.LIVRE)
            session.add(vaga)
        session.commit()
        print("Vagas iniciais geradas com sucesso!")


if __name__ == "__main__":
    print("--- GERADOR DE BANCO DE DADOS ---")
    print(
        "Atenção: Esta operação irá APAGAR o banco 'porto.db' existente e criar um novo."
    )
    confirm = input("Deseja continuar? (S/N): ").strip().upper()

    if confirm in ("S", "SIM", "Y", "YES"):
        Base.metadata.drop_all(ENGINE)
        Base.metadata.create_all(ENGINE)
        print("Banco de dados anterior removido.")

        try:
            qtd_navios = int(input("Quantidade de navios para gerar: "))
            qtd_vagas = int(input("Quantidade de berços (terminais) para criar: "))

            if qtd_navios <= 0 or qtd_vagas <= 0:
                print("Erro: As quantidades devem ser maiores que zero.")
            else:
                with Session(ENGINE) as session:
                    gerar_vagas_iniciais(session, quantidade=qtd_vagas)
                gerar_navios_fake(session, quantidade=qtd_navios)
            verificar_integridade()
        except ValueError:
            print("Erro: Digite um número inteiro válido.")
    else:
        print("Operação cancelada.")
