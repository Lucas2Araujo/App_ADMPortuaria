# ⚓ Sistema de Administração Portuária

<div align="center">

[![Documentação](https://img.shields.io/badge/Documentação-Ativa-blue?style=for-the-badge&logo=markdown)](https://lucas2araujo.github.io/App_ADMPortuaria/)
[![CI - Testes & Cobertura](https://github.com/Lucas2Araujo/App_ADMPortuaria/actions/workflows/ci.yml/badge.svg?style=for-the-badge)](https://github.com/Lucas2Araujo/App_ADMPortuaria/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-highlight.svg)](https://sonarcloud.io/summary/new_code?id=Lucas2Araujo_App_ADMPortuaria)

</div>

---

> **Disciplina:** Projeto e Desenvolvimento de Software (PDS)
> **Professor:** Davi Viana dos Santos
> **Instituição:** Universidade Federal do Maranhão (UFMA) — BICT / Engenharia da Computação
> **Desenvolvedores:** Jennifer Caroline da Silva Barraza · Lucas Araújo Dominici · Luis Fernando Ribeiro Curvelo · Marcos Paulo Dominice Silva

---

## ⚓ Objetivo do Projeto

Este projeto consiste no desenvolvimento de um sistema para a gestão de embarque e desembarque de navios similar ao fluxo do **Porto do Itaqui, em São Luís - MA**. O foco central do software é a automação da **fila de atracação**, aplicando algoritmos de prioridade baseados na natureza da carga transportada.

### O Motor de Fila (Lógica de Negócio)

A gestão da fila evita o travamento logístico do porto através de duas regras principais:

1. **Prioridade Dinâmica de Perecibilidade:** Cargas classificadas como urgentes/perecíveis (ex: vacinas, carnes, frutas) recebem multiplicadores massivos de prioridade, furando a fila automaticamente de acordo com o grau de urgência.
2. **Regra Anti-Starvation (Envelhecimento):** Para evitar que navios de cargas comuns (ex: minério, fertilizantes) aguardem infinitamente, o sistema bonifica o *score* do navio a cada hora de espera, garantindo atracação justa a longo prazo.

---

## 🚀 Funcionalidades (Requisitos Funcionais)

| Status | RF | Funcionalidade |
|:---:|:---:|---|
| ✅ | RF01 | **Cadastro de Navios** — Registro via IMO ID, Nome do Navio, Nome do Capitão e Companhia |
| ✅ | RF02 | **Gestão de Cargas** — Catálogo dinâmico com dedução automática de perecibilidade (Medicamentos, Carnes, Grãos, etc.) |
| ✅ | RF09 | **Workflow de Auditoria** — Auditoria de documentos alfandegários e reclassificação manual de cargas |
| ✅ | RF03/04 | **Fila de Espera Dinâmica** — Visualização ordenada por Score com cálculo de prioridade e bônus anti-starvation |
| ✅ | RF05/06 | **Controle de Atracação** — Monitoramento de vagas/berços em tempo real via Dashboard e logs históricos |

---

## 🛠️ Arquitetura e Tecnologias

O projeto foi estruturado utilizando o padrão de **Camadas de Serviço (Controllers/Services)**, separando as entidades de persistência (`cad.py`) das regras de negócio e fluxo de dados.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flet](https://img.shields.io/badge/Flet-Frontend-7952b3?style=for-the-badge&logo=flutter&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Banco%20de%20Dados-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Testes-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</div>

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Interface Gráfica | Flet (multiplataforma) |
| ORM | SQLAlchemy (Declarative Base) |
| Banco de Dados | SQLite (`porto.db`) |
| Mock de Dados | Faker |
| Testes | Pytest + pytest-cov |
| Formatação | Black |
| Modelagem | PlantUML / UML 2.0 |

---

## 📦 Como Executar o Sistema

Para facilitar a avaliação e o uso em computadores sem Python instalado, o sistema foi compilado em executáveis independentes para **Windows** e **Linux**.

### Opção A: Executáveis Compilados (Mais Rápido)

#### 🐧 Linux (Ubuntu, Nobara, Fedora, Debian, etc.)

1. Baixe o arquivo `Adm_Porto` correspondente ao Linux.
2. Conceda permissão de execução e rode:

```bash
chmod +x Adm_Porto
./Adm_Porto
```

#### 💻 Windows (10 e 11)

1. Baixe o arquivo `Adm_Porto.exe`.
2. Abra o Prompt de Comando ou PowerShell na pasta do arquivo e execute:

```dos
.\Adm_Porto.exe
```

> Se preferir, também é possível dar um duplo clique diretamente sobre o arquivo no Explorador de Arquivos.

> [!WARNING]
> **SmartScreen / Windows Defender:** Como o software foi empacotado via PyInstaller sem assinatura digital comercial, o Windows pode exibir um alerta preventivo (falso positivo). Clique em **"Mais informações"** → **"Executar assim mesmo"** para prosseguir com segurança.

---

### Opção B: A partir do Código-Fonte (Modo Desenvolvedor)

```bash
# 1. Clone o repositório
git clone https://github.com/Lucas2Araujo/App_ADMPortuaria

# 2. Acesse o diretório
cd App_ADMPortuaria

# 3. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# .\venv\Scripts\activate       # Windows

# 4. Instale as dependências
pip install -r src/requirements.txt

# 5. (Opcional) Popule o banco com dados simulados
python src/pop_bd.py

# 6. Inicie a aplicação
python src/app.py
```
