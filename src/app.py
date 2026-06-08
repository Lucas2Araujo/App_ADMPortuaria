import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Atracacao, Navio, Vaga, StatusVaga, StatusNavio
from controller_cadastros import solicitar_pre_cadastro, auditar_solicitacoes_pendentes, excluir_registro_navio
from controller_operacao import atracar_navio, registrar_desatracacao, exibir_painel_vagas, exibir_log_operacoes
from ord_propriety import exibir_fila_atracacao
from pop_bd import gerar_navios_fake, gerar_vagas_iniciais

# Constantes pro sonarqube não perturbar mais
REGEX_NOME_VALIDO = r"[A-Za-z0-9À-ÿ\s\-']+"
MSG_OPCAO_INVALIDA = "Opção inválida."
MSG_ERRO_OPCAO_INVALIDA = "Erro: Opção inválida."
MSG_CANCELAR = "[0] Cancelar"
MSG_ESCOLHA_OPCAO = "Escolha uma opção: "
MSG_OPERACAO_CANCELADA = "Operação cancelada."
MSG_PRESSIONE_ENTER = "\n[Pressione ENTER para continuar...]"

def limpar_tela():
    """Limpa o terminal para melhorar a navegação do usuário."""
    os.system('cls' if os.name == 'nt' else 'clear')

def _obter_imo():
    while True:
        imo_num = input("Número do IMO (apenas números, ex: 1234567): ").strip()
        if imo_num.isdigit():
            return f"IMO{imo_num}"
        print("Erro: IMO inválido. Digite apenas números.")

def _obter_nome_valido(prompt, msg_erro_vazio):
    while True:
        nome = input(prompt).strip()
        if not nome:
            print(msg_erro_vazio)
        elif not re.fullmatch(REGEX_NOME_VALIDO, nome):
            print("Erro: O valor contém caracteres inválidos. Use apenas letras, números, espaços, hífens ou apóstrofos.")
        else:
            return nome

def _obter_descricao_personalizada():
    while True:
        carga_desc = input("Especifique a descrição da carga: ").strip()
        if carga_desc:
            return carga_desc
        print("Erro: A descrição da carga não pode ser vazia.")

def _obter_carga():
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
        '0': ("Outros (Especificar manualmente)", "OUTROS_PENDENTE", False)
    }

    while True:
        print("\n--- Categoria da Carga ---")
        for key, (desc, _, _) in menu_cargas.items():
            print(f"[{key}] {desc}")
            
        opcao = input("Selecione o tipo de carga (1-10): ").strip()
        if opcao in menu_cargas:
            desc_padrao, categoria, eh_perecivel = menu_cargas[opcao]
            if opcao == '10':
                return _obter_descricao_personalizada(), categoria, eh_perecivel
            return desc_padrao, categoria, eh_perecivel
        print("Erro: Opção inválida. Escolha um número de 1 a 10.")

def _obter_peso():
    while True:
        try:
            peso = int(input("Peso Total (Toneladas): "))
            if peso > 0:
                return peso
            print("Erro: O peso deve ser maior que zero.")
        except ValueError:
            print("Erro: O peso deve ser um número inteiro.")

def _obter_documentos():
    while True:
        possui_doc_str = input("Possui documentos da alfândega? (S/N): ").strip().upper()
        if possui_doc_str in ('S', 'SIM', 'Y', 'YES'):
            return True
        elif possui_doc_str in ('N', 'NAO', 'NÃO', 'NO'):
            return False
        print("Erro: Responda com 'Sim' (S/Y) ou 'Não' (N/No).")

def coletar_dados_cadastro(session):
    """Função auxiliar para coletar inputs do usuário via terminal e chamar o pré-cadastro."""
    print("\n--- Formulário de Registro de Navio ---")
    imo = _obter_imo()
    nome = _obter_nome_valido("Nome do Navio: ", "Erro: O nome do navio não pode ser vazio.")
    capitao = _obter_nome_valido("Nome do Capitão: ", "Erro: O nome do capitão não pode ser vazio.")
    companhia = _obter_nome_valido("Companhia: ", "Erro: A companhia não pode ser vazia.")
    carga_desc, categoria, eh_perecivel = _obter_carga()
    peso = _obter_peso()
    possui_documentos = _obter_documentos()
    
    solicitar_pre_cadastro(
        session=session, 
        imo=imo, nome=nome, capitao=capitao, companhia=companhia, 
        carga_desc=carga_desc, categoria=categoria, peso=peso, eh_perecivel=eh_perecivel, 
        possui_documentos=possui_documentos
    )

def _atracar_lote(session):
    atr_count = 0
    while True:
        vaga_livre = session.query(Vaga).filter(Vaga.status == StatusVaga.LIVRE).first()
        navio_fila = session.query(Navio).filter(Navio.status == StatusNavio.VALIDADO).first()
        
        if not vaga_livre or not navio_fila:
            if atr_count == 0:
                atracar_navio(session)
            else:
                print(f"\nOperação em lote concluída. {atr_count} navio(s) atracado(s) com sucesso!")
            break
        
        if atracar_navio(session):
            atr_count += 1

def iniciar_atracacao(session):
    print("\n--- INICIAR ATRACAÇÃO ---")
    print("[1] Atracar apenas o próximo navio")
    print("[2] Preencher todas as vagas livres automaticamente")
    print(MSG_CANCELAR)
    escolha_atr = input(MSG_ESCOLHA_OPCAO).strip()
    
    limpar_tela()
    if escolha_atr == '1':
        atracar_navio(session)
    elif escolha_atr == '2':
        _atracar_lote(session)
    elif escolha_atr == '0':
        print(MSG_OPERACAO_CANCELADA)
    else:
        print(MSG_OPCAO_INVALIDA)

def desatracar_navio(session):
    atracacoes_ativas = session.query(Atracacao).filter(Atracacao.data_hora_fim.is_(None)).all()
    if not atracacoes_ativas:
        print("Não há navios atracados no momento.")
        return

    print("\n--- NAVIOS ATRACADOS ---")
    for i, atracacao in enumerate(atracacoes_ativas, start=1):
        navio = session.query(Navio).filter(Navio.imo_id == atracacao.navio_imo_id).first()
        nome_navio = navio.nome if navio else "Desconhecido"
        print(f"[{i}] {nome_navio} (IMO: {atracacao.navio_imo_id}) - Vaga {atracacao.vaga_id}")
    print("[T] Desatracar TODOS os navios")
    print(MSG_CANCELAR)
    
    escolha_desatracar = input("Escolha o navio para desatracar: ").strip().upper()
    
    if escolha_desatracar == '0':
        print(MSG_OPERACAO_CANCELADA)
    elif escolha_desatracar == 'T':
        for atracacao in atracacoes_ativas:
            registrar_desatracacao(session, atracacao.navio_imo_id)
        print(f"\nSucesso: Todos os {len(atracacoes_ativas)} navios foram desatracados.")
    elif escolha_desatracar.isdigit() and 1 <= int(escolha_desatracar) <= len(atracacoes_ativas):
        idx = int(escolha_desatracar) - 1
        imo_selecionado = atracacoes_ativas[idx].navio_imo_id
        registrar_desatracacao(session, imo_selecionado)
    else:
        print(MSG_ERRO_OPCAO_INVALIDA)

def menu_excluir_navio(session):
    todos_navios = session.query(Navio).all()
    if not todos_navios:
        print("Não há navios registrados no sistema.")
        return

    print("\n--- EXCLUIR REGISTRO DE NAVIO ---")
    for i, navio in enumerate(todos_navios, start=1):
        print(f"[{i}] {navio.nome} (IMO: {navio.imo_id}) - Status: {navio.status.value}")
    print(MSG_CANCELAR)
    
    escolha_excluir = input("Escolha o navio para excluir: ").strip()
    
    if escolha_excluir == '0':
        print(MSG_OPERACAO_CANCELADA)
    elif escolha_excluir.isdigit() and 1 <= int(escolha_excluir) <= len(todos_navios):
        idx = int(escolha_excluir) - 1
        imo_selecionado = todos_navios[idx].imo_id
        excluir_registro_navio(session, imo_selecionado)
    else:
        print(MSG_ERRO_OPCAO_INVALIDA)

def _gerar_apenas_navios():
    try:
        qtd_navios = int(input("Quantidade de navios para gerar: "))
        if qtd_navios > 0:
            gerar_navios_fake(quantidade=qtd_navios)
        else:
            print("Erro: A quantidade deve ser maior que zero.")
    except ValueError:
        print("Erro: Digite um número inteiro válido.")

def _resetar_banco(session, engine):
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
                session.commit()
                Base.metadata.drop_all(engine)
                Base.metadata.create_all(engine)
                print("Banco de dados anterior removido e recriado.")
                
                gerar_vagas_iniciais(session, quantidade=qtd_vagas)
                gerar_navios_fake(quantidade=qtd_navios)
        except ValueError:
            print("Erro: Digite um número inteiro válido.")
    else:
        print(MSG_OPERACAO_CANCELADA)

def menu_gerar_dados(session, engine):
    print("\n--- GERAR DADOS DE TESTE ---")
    print("[1] Adicionar apenas novos navios (Manter banco atual)")
    print("[2] Resetar TUDO (Apagar banco e recriar)")
    print(MSG_CANCELAR)
    escolha_teste = input(MSG_ESCOLHA_OPCAO).strip()
    
    limpar_tela()
    if escolha_teste == '1':
        _gerar_apenas_navios()
    elif escolha_teste == '2':
        _resetar_banco(session, engine)
    elif escolha_teste == '0':
        print(MSG_OPERACAO_CANCELADA)
    else:
        print(MSG_OPCAO_INVALIDA)

def painel_admin(session, engine):
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
        
        op_admin = input(MSG_ESCOLHA_OPCAO).strip()
        limpar_tela()

        if op_admin == '1':   coletar_dados_cadastro(session)
        elif op_admin == '2': auditar_solicitacoes_pendentes(session)
        elif op_admin == '3': exibir_fila_atracacao(session)
        elif op_admin == '4': iniciar_atracacao(session)
        elif op_admin == '5': desatracar_navio(session)
        elif op_admin == '6': exibir_painel_vagas(session)
        elif op_admin == '7': exibir_log_operacoes(session)
        elif op_admin == '8': menu_excluir_navio(session)
        elif op_admin == '9': menu_gerar_dados(session, engine)
        elif op_admin == '0': break
        else: print(MSG_OPCAO_INVALIDA)
        
        input(MSG_PRESSIONE_ENTER)
        limpar_tela()

def main():
    """Inicializa a aplicação e apresenta o menu principal de navegação do sistema."""
    engine = create_engine("sqlite:///porto.db")
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        gerar_vagas_iniciais(session, quantidade=5)

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
            
            escolha = input(MSG_ESCOLHA_OPCAO).strip()
            
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
                painel_admin(session, engine)
            
            elif escolha == '0':
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print(f"{MSG_OPCAO_INVALIDA} Tente novamente.")
                input(MSG_PRESSIONE_ENTER)
                limpar_tela()

if __name__ == "__main__":
    main()