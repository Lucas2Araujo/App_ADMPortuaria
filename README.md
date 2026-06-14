# Sistema de Administração Portuária

[![Documentação Ativa](https://img.shields.io/badge/Documentação-Ativa-blue?style=for-the-badge&logo=markdown)](https://lucas2araujo.github.io/App_ADMPortuaria/)

> **Disciplina:** Projeto e Desenvolvimento de Software (PDS)  
> **Professor:** Davi Viana dos Santos  
> **Instituição:** Universidade Federal do Maranhão (UFMA) - BICT / Engenharia da Computação  
> **Desenvolvedores:** Jennifer Caroline da Silva Barraza / Lucas Araújo Dominici / Luis Fernando Ribeiro Curvelo  

## ⚓ Objetivo do Projeto
Este projeto consiste no desenvolvimento de um sistema para a gestão de embarque e desembarque de navios que seja similar ao fluxo do **Porto do Itaqui, em São Luís - MA**. O foco central do software é a automação da **fila de atracação**, aplicando algoritmos de prioridade baseados na natureza da carga transportada.

### O Motor de Fila (Lógica de Negócio)
A gestão da fila evita o travamento logístico do porto através de duas regras principais:
1. **Prioridade Dinâmica de Perecibilidade:** Cargas classificadas como urgentes/perecíveis (ex: vacinas, carnes, frutas) recebem multiplicadores massivos de prioridade, furando a fila automaticamente de acordo com o grau de urgência.
2. **Regra Anti-Starvation (Envelhecimento):** Para evitar que navios de cargas comuns (ex: minério, fertilizantes) aguardem infinitamente, o sistema bonifica o *score* do navio a cada hora de espera, garantindo atracação justa a longo prazo.

## 🚀 Funcionalidades (Requisitos Funcionais - Sprint 1)
- [X] **Cadastro de Navios (RF01):** Registro via IMO ID, Nome do Navio, Nome do Capitão e Companhia.
- [X] **Gestão de Cargas (RF02):** Catálogo dinâmico de cargas com dedução automática de perecibilidade através de classes estruturadas (Medicamentos, Carnes, Grãos, etc.).
- [X] **Workflow de Auditoria (RF09):** O Administrador do Porto realiza a auditoria de documentos alfandegários (`documento_alfandega`) e reclassifica cargas enviadas como "Outros" de forma manual e interativa.
- [X] **Fila de Espera Dinâmica (RF03/RF04):** Visualização ordenada por Score com o cálculo automatizado de prioridade e bônus anti-starvation.
- [X] **Controle de Atracação (RF05/RF06):** Monitoramento de vagas/berços em tempo real através de um painel estruturado (Dashboard de Vagas) e registro detalhado de logs históricos de entrada e saída.

## 🛠️ Arquitetura e Tecnologias
O projeto foi estruturado utilizando o padrão de **Camadas de Serviço (Controllers/Services)**, separando as entidades de persistência (`cad.py`) das regras de controle de negócios e fluxo de dados.

* **Linguagem:** Python 3.10+
* **Interface Gráfica (Frontend Sprint 2):** Flet (Aplicações multiplataforma em Python)
* **ORM:** SQLAlchemy (Declarative Base)
* **Banco de Dados:** SQLite (`porto.db`)
* **Mock de Dados:** Faker (Para simulação de massa de dados em testes corporativos)
* **Modelagem:** PlantUML / UML 2.0

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 📦 Como Executar o Sistema

Para facilitar a avaliação e o uso em computadores que não possuem o Python e o ecossistema do SQLAlchemy instalados, o sistema foi compilado em arquivos executáveis independentes para **Windows** e **Linux**.

### Opção A: Executando via Binários Compilados (Mais Rápido)

#### 🐧 No Linux (Ubuntu, Nobara, Fedora, Debian, etc.)
1. Baixe o arquivo binário correspondente ao Linux (`Adm_Porto`).
2. Abra o terminal na pasta onde o arquivo foi baixado e conceda a permissão necessária para transformá-lo em um executável:
   ```bash
   chmod +x Adm_Porto
3. Execute o aplicativo direto pelo terminal (Ou clique com botão direito em cima dele e na opção "Abrir no terminal")
    ./Adm_Porto

#### 💻 No Windows (10 e 11)
1. Baixe o arquivo executável correspondente ao Windows (Adm_Porto.exe).

2. Abra o Prompt de Comando (CMD) ou o PowerShell na pasta do arquivo (altamente recomendado para acompanhar a visualização textual do terminal perfeitamente) e execute:

    DOS
    .\Adm_Porto.exe
    (Nota: Se preferir, também é possível dar um duplo clique diretamente sobre o arquivo no Explorador de Arquivos).

#### ⚠️ Alerta Importante para Usuários Windows (SmartScreen / Defender):
Como este software foi empacotado nativamente a partir do Python (via PyInstaller) e não possui uma assinatura digital comercial de desenvolvedor (Code Signing Certificate), o Windows SmartScreen ou o antivírus podem exibir um alerta de segurança preventivo (Falso Positivo) bloqueando a execução inicial.

Como resolver: Quando a tela azul do SmartScreen aparecer, clique no link "Mais informações" e, em seguida, selecione o botão "Executar assim mesmo" para iniciar o sistema do porto com segurança.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### Opção B: Executando a partir do Código-Fonte (Modo Desenvolvedor)
Caso prefira rodar ou auditar o código diretamente no seu ambiente de desenvolvimento:

Bash
1. Clone o repositório oficial
git clone [https://github.com/Lucas2Araujo/App_ADMPortuaria](https://github.com/Lucas2Araujo/App_ADMPortuaria)

2. Acesse o diretório raiz do projeto
cd App_ADMPortuaria

3. Crie e ative um ambiente virtual (Recomendado)
python3 -m venv venv
source venv/bin/activate  # No Linux (Nobara/Ubuntu)

# No Windows: .\venv\Scripts\activate

4. Instale as dependências requeridas
pip install -r requirements.txt

5. Opcional - Popular o banco com dados simulados (Faker)
python src/pop_bd.py

6. Inicialize a aplicação oficial
python src/app.py
