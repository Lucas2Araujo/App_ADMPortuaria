# Sistema de Administração Portuária - Porto do Itaqui

> **Disciplina:** Projeto e Desenvolvimento de Software (PDS)
> **Professor:** Davi Viana dos Santos
> **Instituição:** Universidade Federal do Maranhão (UFMA) - BICT / Engenharia da Computação
> **Desenvolvedores:** Jennifer Caroline da Silva Barraza / Lucas Araújo Dominici / Luis Fernando Ribeiro Curvelo

## Objetivo do Projeto
Este projeto consiste no desenvolvimento de um sistema para a gestão de embarque e desembarque de navios no **Porto do Itaqui, em São Luís - MA**. O foco central do software é a automação da **fila de atracação**, aplicando algoritmos de prioridade baseados na natureza da carga transportada.

### O Motor de Fila (Lógica de Negócio)
A gestão da fila evita o travamento logístico do porto através de duas regras principais:
1. **Prioridade Dinâmica de Perecibilidade:** Cargas classificadas como urgentes/perecíveis (ex: vacinas, carnes, frutas) recebem multiplicadores massivos de prioridade, furando a fila automaticamente de acordo com o grau de urgência.
2. **Regra Anti-Starvation (Envelhecimento):** Para evitar que navios de cargas comuns (ex: minério, fertilizantes) aguardem infinitamente, o sistema bonifica o *score* do navio a cada hora de espera, garantindo atracação justa a longo prazo.

## Funcionalidades (Requisitos Funcionais)
- [X] **Cadastro de Navios:** Registro via IMO ID, Nome e Capitão.
- [X] **Gestão de Cargas:** Catálogo dinâmico de cargas com dedução automática de perecibilidade.
- [X] **Motor de Fila:** Reordenação automática em tempo real baseada em prioridade e tempo de espera.
- [X] **Controle de Atracação:** Vínculo físico e temporal entre Navio e Vaga.
- [X] **Monitoramento de Vagas:** Dashboard de terminal com o status atualizado dos berços do porto (Livres/Ocupadas).
- [X] **Portal da Tripulação:** Interface para que comandantes solicitem o pré-cadastro de suas embarcações.
- [X] **Workflow de Aprovação:** O Administrador do Porto audita documentos e classifica cargas não mapeadas antes da entrada na fila.

## Arquitetura e Tecnologias
O projeto foi estruturado utilizando o padrão de **Camadas de Serviço (Controllers/Services)** e está atualmente na fase de MVP (Sprint 1), rodando nativamente via interface de terminal (CLI).

**Stack Atual (Sprint 1):**
* **Linguagem:** Python 3.10+
* **ORM:** SQLAlchemy (Declarative Base)
* **Banco de Dados:** SQLite (`porto.db`)
* **Mock de Dados:** Faker (Para simulação de massa de dados)
* **Modelagem:** PlantUML / UML 2.0

**Planejamento para Próximas Sprints:**
* **Interface Gráfica (GUI):** PyQt6 / CustomTkinter
* **Migração de Banco:** PostgreSQL
* **Prototipação UI:** Penpot / Figma

## ⚙️ Como Configurar e Executar o Ambiente

Siga os passos abaixo no seu terminal para testar a aplicação:

```bash
# 1. Clone este repositório
git clone [https://github.com/Lucas2Araujo/App_ADMPortuaria](https://github.com/Lucas2Araujo/App_ADMPortuaria)

# 2. Acesse o diretório do projeto e da pasta de código
cd App_ADMPortuaria

# 3. Crie e ative um ambiente virtual (Recomendado)
python3 -m venv venv
source venv/bin/activate  # No Linux/macOS
# ou venv\Scripts\activate no Windows

# 4. Instale as dependências
pip install sqlalchemy faker

# 5. Gere o Banco de Dados, Vagas e Navios Fake para teste
python src/pop_bd.py

# 6. Inicie o Sistema (Menu Interativo)
python src/app.py