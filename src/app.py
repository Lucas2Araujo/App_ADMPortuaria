import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cad import Base, Atracacao, Navio, Vaga, StatusVaga, StatusNavio, obter_sessao, inicializar_banco
from controller_cadastros import (
    solicitar_pre_cadastro,
    auditar_solicitacoes_pendentes,
    excluir_registro_navio,
    classificar_carga,
    editar_registro_navio,
    CargaNaoClassificadaError,
)
from controller_operacao import (
    atracar_navio,
    registrar_desatracacao,
    obter_painel_vagas_dto,
    obter_log_operacoes_dto,
)
from ord_propriety import obter_fila_atracacao_dto
from pop_bd import gerar_navios_fake, gerar_vagas_iniciais

# Constantes
REGEX_NOME_VALIDO = r"[A-Za-z0-9À-ÿ\s\-']+"
MSG_OPCAO_INVALIDA = "Opção inválida."
MSG_ERRO_OPCAO_INVALIDA = "Erro: Opção inválida."
MSG_CANCELAR = "[0] Cancelar"
MSG_ESCOLHA_OPCAO = "Escolha uma opção: "
MSG_OPERACAO_CANCELADA = "Operação cancelada."
MSG_PRESSIONE_ENTER = "\n[Pressione ENTER para continuar...]"


def limpar_tela():
    """Limpa o terminal para melhorar a navegação do usuário."""
    os.system("cls" if os.name == "nt" else "clear")


def _obter_imo():
    while True:
        imo_num = input("Informe os 7 dígitos númericos do IMO: ").strip()
        if imo_num.isdigit():
            if len(imo_num) == 7:
                return f"IMO{imo_num}"
            else:
                print(
                    f"IMO Inválido! Você digitou {len(imo_num)} dígitos. O padrão exige exatamente 7 dígitos!"
                )
        else:
            print("Erro: O IMO deve conter apenas números.")


def _obter_nome_valido(prompt, msg_erro_vazio):
    while True:
        nome = input(prompt).strip()
        if not nome:
            print(msg_erro_vazio)
        elif not re.fullmatch(REGEX_NOME_VALIDO, nome):
            print(
                "Erro: O valor contém caracteres inválidos. Use apenas letras, números, espaços, hífens ou apóstrofos."
            )
        else:
            return nome


def _obter_nome_edicao(prompt, valor_atual):
    while True:
        novo_valor = input(f"{prompt} [{valor_atual}]: ").strip()
        if not novo_valor:
            return valor_atual
        elif not re.fullmatch(REGEX_NOME_VALIDO, novo_valor):
            print(
                "Erro: O valor contém caracteres inválidos. Use apenas letras, números, espaços, hífens ou apóstrofos."
            )
        else:
            return novo_valor


def _obter_descricao_personalizada():
    while True:
        carga_desc = input("Especifique a descrição da carga: ").strip()
        if carga_desc:
            return carga_desc
        print("Erro: A descrição da carga não pode ser vazia.")


def _obter_carga():
    menu_cargas = {
        "1": ("Medicamentos e Vacinas", "URGENTE_PERECIVEL", True),
        "2": ("Carnes e Pescados Congelados", "URGENTE_PERECIVEL", True),
        "3": ("Frutas e Verduras Frescas", "ALTA_PERECIBILIDADE", True),
        "4": ("Laticínios e Derivados", "ALTA_PERECIBILIDADE", True),
        "5": ("Grãos Úmidos / Açúcar", "BAIXA_PERECIBILIDADE", True),
        "6": ("Grãos Secos (Soja, Milho)", "COMUM", False),
        "7": ("Minérios e Siderurgia", "COMUM", False),
        "8": ("Combustíveis e Petróleo", "COMUM", False),
        "9": ("Contêineres de Carga Geral", "COMUM", False),
        "0": ("Outros (Especificar manualmente)", "OUTROS_PENDENTE", False),
    }

    while True:
        print("\n--- Categoria da Carga ---")
        for key, (desc, _, _) in menu_cargas.items():
            print(f"[{key}] {desc}")

        opcao = input("Selecione o tipo de carga (1-10): ").strip()
        if opcao in menu_cargas:
            desc_padrao, categoria, eh_perecivel = menu_cargas[opcao]
            if opcao == "0":
                return _obter_descricao_personalizada(), categoria, eh_perecivel
            return desc_padrao, categoria, eh_perecivel
        print("Erro: Opção inválida. Escolha um número de 1 a 10 ou 0.")


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
        possui_doc_str = (
            input("Possui documentos da alfândega? (S/N): ").strip().upper()
        )
        if possui_doc_str in ("S", "SIM", "Y", "YES"):
            return True
        elif possui_doc_str in ("N", "NAO", "NÃO", "NO"):
            return False
        print("Erro: Responda com 'Sim' (S/Y) ou 'Não' (N/No).")


def coletar_dados_cadastro(session):
    """Função auxiliar para coletar inputs do usuário via terminal e chamar o pré-cadastro."""
    print("\n--- Formulário de Registro de Navio ---")
    imo = _obter_imo()
    nome = _obter_nome_valido(
        "Nome do Navio: ", "Erro: O nome do navio não pode ser vazio."
    )
    capitao = _obter_nome_valido(
        "Nome do Capitão: ", "Erro: O nome do capitão não pode ser vazio."
    )
    companhia = _obter_nome_valido(
        "Companhia: ", "Erro: A companhia não pode ser vazia."
    )
    carga_desc, categoria, eh_perecivel = _obter_carga()
    peso = _obter_peso()
    possui_documentos = _obter_documentos()

    solicitar_pre_cadastro(
        session=session,
        imo=imo,
        nome=nome,
        capitao=capitao,
        companhia=companhia,
        carga_desc=carga_desc,
        categoria=categoria,
        peso=peso,
        eh_perecivel=eh_perecivel,
        possui_documentos=possui_documentos,
    )
    print(f"[CAPITÃO] Pré-cadastro realizado: Navio '{nome}' ({imo}) adicionado com status PENDENTE.")


def editar_navio(session):
    print("\n--- EDITAR DADOS DO NAVIO ---")
    navio = _selecionar_ou_pesquisar_navio(session)

    if navio == "CANCELADO":
        print(MSG_OPERACAO_CANCELADA)
        return
    if not navio:
        return

    print(f"\n Editando: {navio.nome} | Pressione ENTER para manter o valor atual.")
    novo_nome = _obter_nome_edicao("Novo Nome", navio.nome)
    novo_capitao = _obter_nome_edicao("Novo Capitão", navio.nome_capitao)
    nova_companhia = _obter_nome_edicao("Nova Companhia", navio.companhia)

    try:
        editar_registro_navio(session, navio.imo_id, novo_nome, novo_capitao, nova_companhia)
        print(f"\n Dados do navio {navio.imo_id} atualizados com sucesso no sistema!")
    except Exception as e:
        print(f"Erro ao editar navio: {e}")


def _atracar_lote(session):
    atr_count = 0
    while True:
        vagas = obter_painel_vagas_dto(session)
        vaga_livre = next((v for v in vagas if v.status == "LIVRE"), None)
        
        fila = obter_fila_atracacao_dto(session)
        navio_fila = fila[0] if fila else None

        if not vaga_livre or not navio_fila:
            if atr_count == 0:
                print(
                    "\nOperação não concluída, checar se há navios para atracar ou vagas livres."
                )
            else:
                print(
                    f"\nOperação em lote concluída. {atr_count} navio(s) atracado(s) com sucesso!"
                )
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
    if escolha_atr == "1":
        log = atracar_navio(session)
        if log:
            print(f"Navio {log.navio_imo_id} atracado na Vaga {log.vaga_id} com sucesso.")
        else:
            print("Nenhum navio disponível na fila ou nenhuma vaga livre.")
    elif escolha_atr == "2":
        _atracar_lote(session)
    elif escolha_atr == "0":
        print(MSG_OPERACAO_CANCELADA)
    else:
        print(MSG_OPCAO_INVALIDA)


def desatracar_navio(session):
    vagas = obter_painel_vagas_dto(session)
    vagas_ocupadas = [v for v in vagas if v.status == "OCUPADA"]
    if not vagas_ocupadas:
        print("Não há navios atracados no momento.")
        return

    print("\n--- NAVIOS ATRACADOS ---")
    for i, vaga in enumerate(vagas_ocupadas, start=1):
        navio = vaga.navio_atracado
        nome_navio = navio.nome if navio else "Desconhecido"
        imo = navio.imo_id if navio else "Desconhecido"
        print(
            f"[{i}] {nome_navio} (IMO: {imo}) - Vaga {vaga.id}"
        )
    print("[T] Desatracar TODOS os navios")
    print(MSG_CANCELAR)

    escolha = (
        input("\nEscolha o número, digite o IMO, ou [T] para todos: ").strip().upper()
    )

    if escolha == "0":
        print(MSG_OPERACAO_CANCELADA)
    elif escolha == "T":
        count = 0
        for vaga in vagas_ocupadas:
            if vaga.navio_atracado:
                registrar_desatracacao(session, vaga.navio_atracado.imo_id)
                count += 1
        print(
            f"\nSucesso: Todos os {count} navios foram desatracados."
        )

    elif escolha.isdigit() and 1 <= int(escolha) <= len(vagas_ocupadas):
        idx = int(escolha) - 1
        navio = vagas_ocupadas[idx].navio_atracado
        if navio:
            registrar_desatracacao(session, navio.imo_id)
            print(f"Desatracação do navio {navio.imo_id} registrada. Vaga {vagas_ocupadas[idx].id} agora está LIVRE.")

    else:
        imo_busca = escolha if escolha.startswith("IMO") else f"IMO{escolha}"
        vaga_encontrada = next(
            (v for v in vagas_ocupadas if v.navio_atracado and v.navio_atracado.imo_id == imo_busca), None
        )

        if vaga_encontrada:
            registrar_desatracacao(session, imo_busca)
            print(f"Desatracação do navio {imo_busca} registrada. Vaga {vaga_encontrada.id} agora está LIVRE.")
        else:
            print(
                " Erro: Navio não encontrado na lista de atracados ou opção inválida."
            )


def menu_excluir_navio(session):
    print("\n--- EXCLUIR REGISTRO DE NAVIO ---")
    navio = _selecionar_ou_pesquisar_navio(session)

    if navio == "CANCELADO":
        print(MSG_OPERACAO_CANCELADA)
        return
    if not navio:
        return

    try:
        excluir_registro_navio(session, navio.imo_id)
        print(f"[ADMIN] Sucesso: Registro do navio '{navio.nome}' ({navio.imo_id}) foi excluído definitivamente.")
    except Exception as e:
        print(f"[ADMIN] Erro: {e}")


def _gerar_apenas_navios(session):
    try:
        qtd_navios = int(input("Quantidade de navios para gerar: "))
        if qtd_navios > 0:
            gerar_navios_fake(session, quantidade=qtd_navios)
        else:
            print("Erro: A quantidade deve ser maior que zero.")
    except ValueError:
        print("Erro: Digite um número inteiro válido.")


def _resetar_banco(session, engine):
    print("\n--- REINICIAR E POPULAR BANCO DE DADOS ---")
    print("Atenção: Esta operação irá APAGAR todo o banco 'porto.db' atual.")
    confirm = input("Deseja continuar? (S/N): ").strip().upper()

    if confirm in ("S", "SIM", "Y", "YES"):
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
                gerar_navios_fake(session, quantidade=qtd_navios)
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
    if escolha_teste == "1":
        _gerar_apenas_navios(session)
    elif escolha_teste == "2":
        _resetar_banco(session, engine)
    elif escolha_teste == "0":
        print(MSG_OPERACAO_CANCELADA)
    else:
        print(MSG_OPCAO_INVALIDA)


def menu_gerenciar_navios(session):
    print("\n--- GERENCIAR REGISTROS DE NAVIOS ---")
    print("[1] Novo Registro Manual (Balcão)")
    print("[2] Editar Dados de um Navio Existente")
    print(MSG_CANCELAR)

    escolha = input(MSG_ESCOLHA_OPCAO).strip()
    limpar_tela()

    if escolha == "1":
        coletar_dados_cadastro(session)
    elif escolha == "2":
        editar_navio(session)
    elif escolha == "0":
        print(MSG_OPERACAO_CANCELADA)
    else:
        print(MSG_OPCAO_INVALIDA)


def _selecionar_ou_pesquisar_navio(session):
    """
    Exibe os navios e permite selecionar pelo número da lista
    ou pesquisando os 7 dígitos do IMO diretamente.
    """
    todos_navios = session.query(Navio).all()
    if not todos_navios:
        print("Não há navios registrados no sistema.")
        return None

    for i, navio in enumerate(todos_navios, start=1):
        print(
            f"[{i}] {navio.nome} (IMO: {navio.imo_id}) - Status: {navio.status.value}"
        )
    print(MSG_CANCELAR)

    entrada = (
        input("\nEscolha o número da lista ou digite o IMO (7 dígitos): ")
        .strip()
        .upper()
    )

    if entrada == "0":
        return "CANCELADO"

    # 1. Tenta interpretar como um índice numérico da lista
    if entrada.isdigit() and 1 <= int(entrada) <= len(todos_navios):
        return todos_navios[int(entrada) - 1]

    # 2. Se não for índice, tenta como pesquisa direta de IMO
    imo_busca = entrada if entrada.startswith("IMO") else f"IMO{entrada}"
    navio_encontrado = session.query(Navio).filter(Navio.imo_id == imo_busca).first()

    if navio_encontrado:
        return navio_encontrado

    print(MSG_ERRO_OPCAO_INVALIDA)
    return None


def auditar_solicitacoes(session):
    while True:
        try:
            auditos = auditar_solicitacoes_pendentes(session)
            if not auditos:
                print("[ADMIN] Não há solicitações pendentes para auditoria no momento.")
            else:
                for navio in auditos:
                    if navio.status == "VALIDADO":
                        print(f"[ADMIN] SUCESSO: Navio '{navio.nome}' ({navio.imo_id}) VALIDADO. Aprovado para entrar na Fila de Atracação.")
                    else:
                        print(f"[ADMIN] AVISO: Navio '{navio.nome}' ({navio.imo_id}) REJEITADO. Documentação da carga incompleta.")
            break
        except CargaNaoClassificadaError as err:
            print(f"\nAtenção: O navio {err.navio_nome} possui uma carga não classificada: [{err.carga_descricao}].")
            print("[1] Ultra Perecível | [2] Alta Perecibilidade | [3] Baixa Perecibilidade | [4] Comum")
            opcoes = {
                "1": ("URGENTE_PERECIVEL", True),
                "2": ("ALTA_PERECIBILIDADE", True),
                "3": ("BAIXA_PERECIBILIDADE", True),
                "4": ("COMUM", False),
            }
            while True:
                escolha = input("Classifique a carga (1-4): ").strip()
                if escolha in opcoes:
                    categoria, eh_perecivel = opcoes[escolha]
                    classificar_carga(session, err.carga_id, categoria, eh_perecivel)
                    break
                print("Opção inválida. Tente novamente.")


def mostrar_fila_atracacao(session):
    fila = obter_fila_atracacao_dto(session)
    if not fila:
        print("Aviso: A fila de atracação está vazia no momento (Nenhum navio VALIDADO).")
        return

    print(
        f"\n{'POS':<4} | {'IMO':<12} | {'NOME DA EMBARCAÇÃO':<30} | {'COMPANHIA':<25} | {'SCORE':<12} | {'ESPERA'}"
    )
    print("-" * 110)

    for pos, navio in enumerate(fila, start=1):
        if navio.data_solicitacao:
            from datetime import datetime
            espera = datetime.now() - navio.data_solicitacao
            espera_str = str(espera).split(".")[0]
        else:
            espera_str = "N/A"

        print(
            f"{pos:<4} | {navio.imo_id:<12} | {navio.nome:<30} | {navio.companhia[:25]:<25} | {navio.score:<12.2f} | {espera_str}"
        )


def mostrar_painel_vagas(session):
    vagas = obter_painel_vagas_dto(session)
    if not vagas:
        print("Nenhuma vaga cadastrada no sistema.")
        return

    total_vagas = len(vagas)
    vagas_livres = sum(1 for v in vagas if v.status == "LIVRE")
    vagas_ocupadas = total_vagas - vagas_livres

    print("\n" + "=" * 70)
    print("DASHBOARD DO PORTO - STATUS DAS VAGAS")
    print(
        f"Total: {total_vagas} | Disponíveis: {vagas_livres} | Ocupadas: {vagas_ocupadas}"
    )
    print("=" * 70)

    cor_verde = "\033[92m"
    cor_vermelha = "\033[91m"
    reset = "\033[0m"

    for vaga in vagas:
        if vaga.status == "LIVRE":
            print(f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {cor_verde}[LIVRE]{reset}")
        else:
            navio = vaga.navio_atracado
            nome_navio = navio.nome if navio else "Desconhecido"
            imo = navio.imo_id if navio else "Desconhecido"
            data_inicio = (
                vaga.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
                if vaga.data_hora_inicio
                else "N/A"
            )
            print(
                f"Vaga {vaga.id:<2} [{vaga.tipo_vaga}] - {cor_vermelha}[OCUPADA]{reset} -> Navio: {nome_navio} (IMO: {imo}) - Atracado desde: {data_inicio}"
            )


def mostrar_log_operacoes(session):
    eventos = obter_log_operacoes_dto(session)
    print(f"\n{'--- LOG DE OPERAÇÕES (HISTÓRICO) ---'}")
    if not eventos:
        print("Nenhuma operação registrada no histórico.")
        return

    print(
        f"{'DATA/HORA':<20} | {'EVENTO':<16} | {'NAVIO (IMO)':<15} | {'VAGA':<7} | {'OP ID'}"
    )
    print("-" * 77)

    cor_verde = "\033[92m"
    cor_vermelha = "\033[91m"
    reset = "\033[0m"

    for ev in eventos:
        data_str = ev.data_hora.strftime("%Y-%m-%d %H:%M:%S")
        if ev.tipo == "ATRACAO":
            evento_str = f"{cor_verde}{'[+] ATRACAÇÃO':<16}{reset}"
        else:
            evento_str = f"{cor_vermelha}{'[-] DESATRACAÇÃO':<16}{reset}"

        print(
            f"{data_str:<20} | {evento_str} | {ev.navio_imo_id:<15} | Vaga {ev.vaga_id:<2} | OP-{ev.id:03d}"
        )


def painel_admin(session, engine):
    while True:
        print("\n--- PAINEL DO ADMINISTRADOR ---")
        print("[1] Gerenciar Registros (Novo / Editar existentes)")
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

        if op_admin == "1":
            menu_gerenciar_navios(session)
        elif op_admin == "2":
            auditar_solicitacoes(session)
        elif op_admin == "3":
            mostrar_fila_atracacao(session)
        elif op_admin == "4":
            iniciar_atracacao(session)
        elif op_admin == "5":
            desatracar_navio(session)
        elif op_admin == "6":
            mostrar_painel_vagas(session)
        elif op_admin == "7":
            mostrar_log_operacoes(session)
        elif op_admin == "8":
            menu_excluir_navio(session)
        elif op_admin == "9":
            menu_gerar_dados(session, engine)
        elif op_admin == "0":
            break
        else:
            print(MSG_OPCAO_INVALIDA)

        input(MSG_PRESSIONE_ENTER)
        limpar_tela()


def main():
    """Inicializa a aplicação e apresenta o menu principal de navegação do sistema."""
    db_path = Path(__file__).parent / "porto.db"
    engine = inicializar_banco(str(db_path))

    with obter_sessao() as session:
        gerar_vagas_iniciais(session, quantidade=5)

        total_navios = session.query(Navio).count()
        total_vagas = session.query(Vaga).count()
        print(
            f"\n[STATUS] Banco de dados conectado. Navios registrados: {total_navios}. Berços disponíveis: {total_vagas}."
        )

        while True:
            print("\n" + "=" * 40)
            print("  SISTEMA DE ADMINISTRAÇÃO PORTUÁRIA  ")
            print("=" * 40)
            print("[1] Portal da Tripulação")
            print("[2] Painel do Administrador")
            print("[0] Sair")

            escolha = input(MSG_ESCOLHA_OPCAO).strip()

            if escolha == "1":
                print("\n--- PORTAL DA TRIPULAÇÃO ---")
                print("[1] Solicitar Pré-Cadastro")
                print("[0] Voltar")
                op_capitao = input("Opção: ").strip()

                limpar_tela()

                if op_capitao == "1":
                    coletar_dados_cadastro(session)
                    input("\n[Pressione ENTER para voltar ao menu...]")

                limpar_tela()

            elif escolha == "2":
                limpar_tela()
                painel_admin(session, engine)

            elif escolha == "0":
                print("Encerrando o sistema. Até logo!")
                break
            else:
                print(f"{MSG_OPCAO_INVALIDA} Tente novamente.")
                input(MSG_PRESSIONE_ENTER)
                limpar_tela()


if __name__ == "__main__":
    main()
