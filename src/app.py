from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cad import Base
from controller_cadastros import solicitar_pre_cadastro, auditar_solicitacoes_pendentes, excluir_registro_navio
from controller_operacao import atracar_navio, registrar_desatracacao, exibir_painel_vagas, exibir_log_operacoes
from ord_propriety import exibir_fila_atracacao
from pop_bd import gerar_navios_fake

def coletar_dados_cadastro(session):
    """Função auxiliar para coletar inputs do usuário via terminal e chamar o pré-cadastro."""
    print("\n--- Formulário de Registro de Navio ---")
    
    while True:
        imo_num = input("Número do IMO (apenas números, ex: 1234567): ").strip()
        if imo_num.isdigit():
            imo = f"IMO{imo_num}"
            break
        print("Erro: IMO inválido. Digite apenas números.")
        
    while True:
        nome = input("Nome do Navio: ").strip()
        if nome:
            break
        print("Erro: O nome do navio não pode ser vazio.")
        
    while True:
        capitao = input("Nome do Capitão: ").strip()
        if capitao:
            break
        print("Erro: O nome do capitão não pode ser vazio.")
        
    while True:
        companhia = input("Companhia: ").strip()
        if companhia:
            break
        print("Erro: A companhia não pode ser vazia.")
        
    menu_cargas = {
        '1': ("Medicamentos e Vacinas", "ULTRA_PERECIVEL", True),
        '2': ("Carnes e Pescados Congelados", "ULTRA_PERECIVEL", True),
        '3': ("Frutas e Verduras Frescas", "ALTA_PERECIVEL", True),
        '4': ("Laticínios e Derivados", "ALTA_PERECIVEL", True),
        '5': ("Grãos Úmidos / Açúcar", "BAIXA_PERECIVEL", True),
        '6': ("Grãos Secos (Soja, Milho)", "COMUM", False),
        '7': ("Minérios e Siderurgia", "COMUM", False),
        '8': ("Combustíveis e Petróleo", "COMUM", False),
        '9': ("Contêineres de Carga Geral", "COMUM", False),
        '10': ("Outros (Especificar manualmente)", "OUTROS_PENDENTE", False)
    }

    while True:
        print("\n--- Categoria da Carga ---")
        for key, (desc, _, _) in menu_cargas.items():
            print(f"[{key}] {desc}")
            
        opcao = input("Selecione o tipo de carga (1-10): ").strip()
        if opcao in menu_cargas:
            desc_padrao, categoria, eh_perecivel = menu_cargas[opcao]
            if opcao == '10':
                while True:
                    carga_desc = input("Especifique a descrição da carga: ").strip()
                    if carga_desc:
                        break
                    print("Erro: A descrição da carga não pode ser vazia.")
            else:
                carga_desc = desc_padrao
            break
        print("Erro: Opção inválida. Escolha um número de 1 a 10.")
    
    while True:
        try:
            peso = int(input("Peso Total (Toneladas): "))
            if peso > 0:
                break
            print("Erro: O peso deve ser maior que zero.")
        except ValueError:
            print("Erro: O peso deve ser um número inteiro.")
        
    while True:
        possui_doc_str = input("Possui documentos da alfândega? (S/N): ").strip().upper()
        if possui_doc_str in ('S', 'N'):
            possui_documentos = possui_doc_str == 'S'
            break
        print("Erro: Responda apenas com 'S' ou 'N'.")
    
    solicitar_pre_cadastro(
        session=session, 
        imo=imo, nome=nome, capitao=capitao, companhia=companhia, 
        carga_desc=carga_desc, categoria=categoria, peso=peso, eh_perecivel=eh_perecivel, 
        possui_documentos=possui_documentos
    )

def main():
    # Configuração e Conexão com o Banco de Dados
    engine = create_engine("sqlite:///porto.db")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        while True:
            print("\n" + "="*40)
            print("  SISTEMA DE ADMINISTRAÇÃO PORTUÁRIA  ")
            print("="*40)
            print("[1] Portal do Capitão")
            print("[2] Painel do Administrador")
            print("[0] Sair")
            
            escolha = input("Escolha uma opção: ").strip()
            
            if escolha == '1':
                print("\n--- PORTAL DO CAPITÃO ---")
                print("[1] Solicitar Pré-Cadastro")
                print("[0] Voltar")
                op_capitao = input("Opção: ").strip()
                
                if op_capitao == '1':
                    coletar_dados_cadastro(session)
            
            elif escolha == '2':
                while True:
                    print("\n--- PAINEL DO ADMINISTRADOR ---")
                    print("[1] Registrar Navio Manualmente (Balcão)")
                    print("[2] Auditar Solicitações Pendentes")
                    print("[3] Ver Fila de Atracação")
                    print("[4] Iniciar Próxima Atracação")
                    print("[5] Registrar Saída / Desatracação")
                    print("[6] Ver Painel de Vagas Atuais")
                    print("[7] Ver Histórico de Operações")
                    print("[8] Excluir Registro de Navio (CRUD)")
                    print("[9] Gerar Dados de Teste (Popular BD)")
                    print("[0] Voltar")
                    
                    op_admin = input("Escolha uma opção: ").strip()
                    
                    if op_admin == '1':   coletar_dados_cadastro(session)
                    elif op_admin == '2': auditar_solicitacoes_pendentes(session)
                    elif op_admin == '3': exibir_fila_atracacao(session)
                    elif op_admin == '4': atracar_navio(session)
                    elif op_admin == '5': 
                        imo_num = input("Digite apenas o número do IMO do navio para desatracar: ").strip()
                        if imo_num.isdigit():
                            registrar_desatracacao(session, f"IMO{imo_num}")
                        else:
                            print("Erro: Número de IMO inválido.")
                    elif op_admin == '6': exibir_painel_vagas(session)
                    elif op_admin == '7': exibir_log_operacoes(session)
                    elif op_admin == '8':
                        imo_num = input("Digite apenas o número do IMO do navio a ser excluído (ex: 1234567): ").strip()
                        if imo_num.isdigit():
                            excluir_registro_navio(session, f"IMO{imo_num}")
                        else:
                            print("Erro: Número de IMO inválido.")
                    elif op_admin == '9':
                        try:
                            qtd = int(input("Quantidade de navios para gerar: "))
                            if qtd > 0:
                                gerar_navios_fake(qtd)
                            else:
                                print("Erro: A quantidade deve ser maior que zero.")
                        except ValueError:
                            print("Erro: Digite um número inteiro válido.")
                    elif op_admin == '0': break
                    else: print("Opção inválida.")
            
            elif escolha == '0':
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    main()