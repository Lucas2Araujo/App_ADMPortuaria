import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Atracacao, Navio, Vaga, StatusVaga, StatusNavio
from controller_cadastros import solicitar_pre_cadastro, auditar_solicitacoes_pendentes, excluir_registro_navio
from controller_operacao import atracar_navio, registrar_desatracacao, exibir_painel_vagas, exibir_log_operacoes
from ord_propriety import exibir_fila_atracacao
from pop_bd import gerar_navios_fake, gerar_vagas_iniciais

def limpar_tela():
    """Limpa o terminal para melhorar a navegação do usuário."""
    os.system('cls' if os.name == 'nt' else 'clear')

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
        if not nome:
            print("Erro: O nome do navio não pode ser vazio.")
        elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", nome):
            print("Erro: O nome contém caracteres inválidos. Use apenas letras, números, espaços, hífens ou apóstrofos.")
        else:
            break
        
    while True:
        capitao = input("Nome do Capitão: ").strip()
        if not capitao:
            print("Erro: O nome do capitão não pode ser vazio.")
        elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", capitao):
            print("Erro: O nome do capitão contém caracteres inválidos.")
        else:
            break
    while True:
        companhia = input("Companhia: ").strip()
        if not companhia:
            print("Erro: A companhia não pode ser vazia.")
        elif not re.fullmatch(r"[A-Za-z0-9À-ÿ\s\-']+", companhia):
            print("Erro: A companhia contém caracteres inválidos.")
        else:
            break
        
    menu_cargas = {
        '1': ("Medicamentos e Vacinas", "URGENTE_PERECIVEL", True),
        '2': ("Carnes e Pescados Congelados", "URGENTE_PERECIVEL", True),
        '3': ("Frutas e Verduras Frescas", "ALTA_PERECIBILIDADE", True),
        '4': ("Laticínios e Derivados", "ALTA_PERECIBILIDADE", True),
        '5': ("Grãos Úmidos / Açúcar", "BAIXA_PERECIBILIDADE", True),
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
        if possui_doc_str in ('S', 'SIM', 'Y', 'YES'):
            possui_documentos = True
            break
        elif possui_doc_str in ('N', 'NAO', 'NÃO', 'NO'):
            possui_documentos = False
            break
        print("Erro: Responda com 'Sim' (S/Y) ou 'Não' (N/No).")
    
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
        # Garante que as vagas iniciais existam (cria 5 por padrão se o BD estiver vazio)
        gerar_vagas_iniciais(session, quantidade=5)

        # Exibe um status inicial do banco de dados
        total_navios = session.query(Navio).count()
        total_vagas = session.query(Vaga).count()
        print(f"\n[STATUS] Banco de dados conectado. Navios registrados: {total_navios}. Berços disponíveis: {total_vagas}.")
        
        while True:
            print("\n" + "="*40)
            print("  SISTEMA DE ADMINISTRAÇÃO PORTUÁRIA  ")
            print("="*40)
            print("[1] Portal da Tripulação")
            print("[2] Painel do Administrador")
            print("[0] Sair")
            
            escolha = input("Escolha uma opção: ").strip()
            
            if escolha == '1':
                print("\n--- PORTAL DA TRIPULAÇÃO ---")
                print("[1] Solicitar Pré-Cadastro")
                print("[0] Voltar")
                op_capitao = input("Opção: ").strip()
                
                limpar_tela()

                if op_capitao == '1':
                    coletar_dados_cadastro(session)
                    input("\n[Pressione ENTER para voltar ao menu...]")
                
                limpar_tela()
            
            elif escolha == '2':
                limpar_tela()
                while True:
                    print("\n--- PAINEL DO ADMINISTRADOR ---")
                    print("[1] Registrar Navio Manualmente (Balcão)")
                    print("[2] Auditar Solicitações Pendentes")
                    print("[3] Ver Fila de Atracação")
                    print("[4] Iniciar Próxima Atracação")
                    print("[5] Registrar Saída (Desatracação)")
                    print("[6] Ver Painel de Vagas Atuais")
                    print("[7] Ver Histórico de Operações")
                    print("[8] Excluir Registro de Navio")
                    print("[9] Gerar Dados de Teste (Popular BD para testes)")
                    print("[0] Voltar")
                    
                    op_admin = input("Escolha uma opção: ").strip()
                    
                    limpar_tela()

                    if op_admin == '1':   coletar_dados_cadastro(session)
                    elif op_admin == '2': auditar_solicitacoes_pendentes(session)
                    elif op_admin == '3': exibir_fila_atracacao(session)
                    elif op_admin == '4': 
                        print("\n--- INICIAR ATRACAÇÃO ---")
                        print("[1] Atracar apenas o próximo navio")
                        print("[2] Preencher todas as vagas livres automaticamente")
                        print("[0] Cancelar")
                        escolha_atr = input("Escolha uma opção: ").strip()
                        
                        limpar_tela()
                        if escolha_atr == '1':
                            atracar_navio(session)
                        elif escolha_atr == '2':
                            atr_count = 0
                            while True:
                                vaga_livre = session.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).first()
                                navio_fila = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).first()
                                
                                if not vaga_livre or not navio_fila:
                                    if atr_count == 0:
                                        atracar_navio(session) # Chama para exibir o motivo exato de não ter atracado
                                    else:
                                        print(f"\nOperação em lote concluída. {atr_count} navio(s) atracado(s) com sucesso!")
                                    break
                                
                                if atracar_navio(session):
                                    atr_count += 1
                        elif escolha_atr == '0':
                            print("Operação cancelada.")
                        else:
                            print("Opção inválida.")
                    elif op_admin == '5':
                        atracacoes_ativas = session.query(Atracacao).filter(Atracacao.data_hora_fim.is_(None)).all()
                        if not atracacoes_ativas:
                            print("Não há navios atracados no momento.")
                        else:
                            print("\n--- NAVIOS ATRACADOS ---")
                            for i, atracacao in enumerate(atracacoes_ativas, start=1):
                                navio = session.query(Navio).filter(Navio.imo_id == atracacao.navio_imo_id).first()
                                nome_navio = navio.nome if navio else "Desconhecido"
                                print(f"[{i}] {nome_navio} (IMO: {atracacao.navio_imo_id}) - Vaga {atracacao.vaga_id}")
                            print("[T] Desatracar TODOS os navios")
                            print("[0] Cancelar")
                            
                            escolha_desatracar = input("Escolha o navio para desatracar: ").strip().upper()
                            
                            if escolha_desatracar == '0':
                                print("Operação cancelada.")
                            elif escolha_desatracar == 'T':
                                for atracacao in atracacoes_ativas:
                                    registrar_desatracacao(session, atracacao.navio_imo_id)
                                print(f"\nSucesso: Todos os {len(atracacoes_ativas)} navios foram desatracados.")
                            elif escolha_desatracar.isdigit() and 1 <= int(escolha_desatracar) <= len(atracacoes_ativas):
                                idx = int(escolha_desatracar) - 1
                                imo_selecionado = atracacoes_ativas[idx].navio_imo_id
                                registrar_desatracacao(session, imo_selecionado)
                            else:
                                print("Erro: Opção inválida.")
                    elif op_admin == '6': exibir_painel_vagas(session)
                    elif op_admin == '7': exibir_log_operacoes(session)
                    elif op_admin == '8':
                        todos_navios = session.query(Navio).all()
                        if not todos_navios:
                            print("Não há navios registrados no sistema.")
                        else:
                            print("\n--- EXCLUIR REGISTRO DE NAVIO ---")
                            for i, navio in enumerate(todos_navios, start=1):
                                print(f"[{i}] {navio.nome} (IMO: {navio.imo_id}) - Status: {navio.status.value}")
                            print("[0] Cancelar")
                            
                            escolha_excluir = input("Escolha o navio para excluir: ").strip()
                            
                            if escolha_excluir == '0':
                                print("Operação cancelada.")
                            elif escolha_excluir.isdigit() and 1 <= int(escolha_excluir) <= len(todos_navios):
                                idx = int(escolha_excluir) - 1
                                imo_selecionado = todos_navios[idx].imo_id
                                excluir_registro_navio(session, imo_selecionado)
                            else:
                                print("Erro: Opção inválida.")
                    elif op_admin == '9':
                        print("\n--- GERAR DADOS DE TESTE ---")
                        print("[1] Adicionar apenas novos navios (Manter banco atual)")
                        print("[2] Resetar TUDO (Apagar banco e recriar)")
                        print("[0] Cancelar")
                        escolha_teste = input("Escolha uma opção: ").strip()
                        
                        limpar_tela()
                        if escolha_teste == '1':
                            try:
                                qtd_navios = int(input("Quantidade de navios para gerar: "))
                                if qtd_navios > 0:
                                    gerar_navios_fake(quantidade=qtd_navios)
                                else:
                                    print("Erro: A quantidade deve ser maior que zero.")
                            except ValueError:
                                print("Erro: Digite um número inteiro válido.")
                        elif escolha_teste == '2':
                            print("\n--- REINICIAR E POPULAR BANCO DE DADOS ---")
                            print("Atenção: Esta operação irá APAGAR todo o banco 'porto.db' atual.")
                            confirm = input("Deseja continuar? (S/N): ").strip().upper()
                            
                            if confirm in ('S', 'SIM', 'Y', 'YES'):
                                try:
                                    qtd_navios = int(input("Quantidade de navios para gerar: "))
                                    qtd_vagas = int(input("Quantidade de berços (terminais) para criar: "))
                                    
                                    if qtd_navios <= 0 or qtd_vagas <= 0:
                                        print("Erro: As quantidades devem ser maiores que zero.")
                                    else:
                                        session.commit()  # Libera transações pendentes para não travar o SQLite
                                        Base.metadata.drop_all(engine)
                                        Base.metadata.create_all(engine)
                                        print("Banco de dados anterior removido e recriado.")
                                        
                                        gerar_vagas_iniciais(session, quantidade=qtd_vagas)
                                        gerar_navios_fake(quantidade=qtd_navios)
                                except ValueError:
                                    print("Erro: Digite um número inteiro válido.")
                            else:
                                print("Operação cancelada.")
                        elif escolha_teste == '0':
                            print("Operação cancelada.")
                        else:
                            print("Opção inválida.")
                    elif op_admin == '0': 
                        break
                    else: print("Opção inválida.")
                    
                    input("\n[Pressione ENTER para continuar...]")
                    limpar_tela()
            
            elif escolha == '0':
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print("Opção inválida. Tente novamente.")
                input("\n[Pressione ENTER para continuar...]")
                limpar_tela()

if __name__ == "__main__":
    main()