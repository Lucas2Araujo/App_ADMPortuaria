# Sistema de Administração Portuária

> **Disciplina:** Projeto e Desenvolvimento de Software (PDS)
> **Professor::** Davi Viana dos Santos
> **Instituição:** Universidade Federal do Maranhão (UFMA) - BICT / Engenharia da Computação
> **Desenvolvedores:** Jennifer Caroline da Silva Barraza / Lohana de Vasconcelos Floriano / Lucas Araujo Dominici / Luis Fernando Ribeiro Curvelo / 

## Objetivo do Projeto
Este projeto consiste no desenvolvimento de um sistema desktop/cliente-servidor para a gestão de embarque e desembarque de navios no **Porto em São Luis -MA**. O foco central do software é a automação da **fila de atracação**, aplicando algoritmos de prioridade baseados na natureza da carga transportada.

A gestão da fila segue uma política estrita de perecibilidade:
* **Cargas Comuns (Ex: Minério, Fertilizantes):** Inserção padrão no final da fila (FIFO - *First In, First Out*).
* **Cargas Perecíveis (Ex: Alimentos):** Atribuição de prioridade máxima. O algoritmo reposiciona a embarcação no topo da fila de espera automaticamente após a liberação aduaneira.

## Funcionalidades (Requisitos Funcionais)
- [x] **Cadastro de Navios:** Registro via IMO ID, Nome e Comandante.
- [x] **Gestão de Cargas:** Lançamento de manifesto de carga com toggle de perecibilidade.
- [x] **Motor de Fila:** Reordenação automática em tempo real baseada em prioridade.
- [x] **Controle de Atracação:** Vínculo temporal entre Navio e Vaga (Timestamp de entrada e saída).
- [x] **Monitoramento de Vagas:** Dashboard com o status atualizado dos berços do porto.

## Arquitetura e Tecnologias
O projeto é planejado para rodar nativamente em ambientes Linux e Windows, utilizando as seguintes tecnologias:

* **Linguagem:** Python 3.14 (Planejado)
* **Banco de Dados:** PostgreSQL (Planejado)
* **Interface Gráfica (GUI):** PyQt6 / CustomTkinter (Planejado)
* **Modelagem:** PlantUML / UML 2.0
* **Prototipação UI:** Penpot / IA Generativa (Google Stitch, Ai Studio e Figma)

## Documentação e Modelagem (Parte 1)
Os artefatos de engenharia de software da fase de Especificação e Projeto encontram-se na pasta `/docs`:

1.  **Modelo de Casos de Uso:** Visão geral das interações dos atores (Admin e Alfândega) com o sistema.
2.  **Modelo de Domínio (Classes):** Abstração das regras de negócio (Navio, Carga, Fila, Vaga).
3.  **Diagramas de Sequência:** 
    * *Cenário A:* Atracação padrão (Carga comum).
    * *Cenário B:* Atracação prioritária (Carga perecível interceptando a fila).
4.  **Diagrama Entidade-Relacionamento (DER):** Esquema relacional para o PostgreSQL.
5.  **Protótipos de Tela:** Wireframes descartáveis do Dashboard e Formulário de Registro.

## ⚙️ Como Configurar o Ambiente de Desenvolvimento

```bash
# 1. Clone este repositório
git clone [https://github.com/Lucas2Araujo/App_PortoItaqui.git](https://github.com/lucas2araujo/sistema-itaqui-pds.git)

# 2. Acesse o diretório do projeto
cd App_PortoItaqui

# 3. Crie um ambiente virtual (Recomendado)
python3 -m venv venv
source venv/bin/activate  # No Linux/macOS
# ou venv\Scripts\activate no Windows

# 4. Instale as dependências (quando o requirements.txt estiver gerado)
pip install -r requirements.txt
