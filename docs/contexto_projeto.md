# Contexto do Projeto: App de Administração Portuária (Porto do Itaqui)

## 1. Visão Geral e Arquitetura
* **Objetivo:** Sistema de gestão e administração portuária, desenvolvido como projeto avaliativo para a disciplina de Projeto e Desenvolvimento de Software (UFMA).
* **Stack Tecnológico:** 
  * Backend: Python com SQLAlchemy 2.0 (migrando para `sqlalchemy.ext.asyncio`).
  * Frontend: Flet (GUI em Python).
  * Documentação: MkDocs com integração PlantUML.
* **Problema Atual a ser Resolvido:** O sistema sofre de lentidão e travamentos na GUI ao renderizar muitos dados (especialmente na tela de visualização da fila e informações da embarcação). Precisamos refatorar as chamadas síncronas para **assíncronas** e eliminar o problema de **N+1 Queries** no SQLAlchemy.

## 2. Regras de Negócio Críticas
* **Fila de Atracação e Anti-Starvation:** O sistema possui um algoritmo de fila baseado em pontuação (score). Existe uma regra de *anti-starvation* onde a pontuação de uma embarcação aumenta progressivamente a cada hora de espera.
* **DTO e Processamento:** O cálculo do score é feito de forma iterativa no backend (já pré-calculado). O DTO apenas repassa esse valor para o frontend (Flet) exibir, ou seja, o front não deve realizar cálculos pesados de pontuação.

## 3. Padrões de Código Exigidos (Diretrizes para a IA)
Ao gerar ou refatorar o código, aja como um Engenheiro de Software Sênior e obedeça rigorosamente a estas regras:
1. **Concorrência:** Toda chamada ao banco de dados acionada por um evento do Flet (ex: `on_click`) deve usar a abordagem assíncrona (`async def` e `await`). A thread da UI nunca deve ser bloqueada.
2. **Eager Loading:** É estritamente obrigatório usar `joinedload` ou `selectinload` ao buscar as Embarcações. Dados de Carga, Tripulação e outras tabelas filhas devem vir na mesma transação. Nunca faça Lazy Loading em listagens.
3. **Paginação:** Se houver listagem de muitos dados, as queries devem conter `.limit()` e `.offset()`.
4. **Clean Code:** Mantenha a nomenclatura em português para regras de negócio, utilize Type Hints (`-> list`, `: str`, etc.) em todas as funções e respeite a separação entre rotas da interface e a lógica do banco.

## 4. Modelagem de Dados (Diagrama de Classes)
*Nota para a IA: Baseie suas queries em SQLAlchemy a partir das entidades e relações descritas no diagrama PlantUML abaixo.*

```plantuml
@startuml
title Modelo de Domínio: Administração Portuária (Refatorado para a Realidade)
skinparam classAttributeIconSize 0

class Navio {
  - imo_id: String
  - nome: String
  - nome_capitao: String
  - companhia: String
  - status: StatusNavio
  - data_solicitacao: DateTime
}

class Carga {
  - id: Integer
  - descricao: String
  - categoria: String
  - quantidade_toneladas: Integer
  - eh_perecivel: Boolean
  - documento_alfandega: Boolean
}

class Vaga {
  - id: Integer
  - tipo_vaga: String
  - status: StatusVaga
}

class Atracacao {
  - id: Integer
  - data_hora_inicio: DateTime
  - data_hora_fim: DateTime
}

class ControladorCadastros <<Service>> {
  + solicitar_pre_cadastro()
  + auditar_solicitacoes_pendentes()
  + excluir_registro_navio()
  - _solicitar_classificacao_carga()
  - _auditar_documentacao_navio()
}

class MotorDeFila <<Service>> {
  + calcular_score(navio: Navio)
  + obter_proximo_da_fila(): Navio
  + exibir_fila_atracacao()
  + criar_subquery_score_cargas()
  + obter_expressao_score_total()
}

class ControladorOperacao <<Service>> {
  + atracar_navio()
  + registrar_desatracacao()
  + exibir_painel_vagas()
  + exibir_log_operacoes()
}

' Relacionamentos do Banco de Dados
Navio "1" *-- "1..*" Carga : transporta >
Navio "0..*" -- "1" Vaga : ocupa >
(Navio, Vaga) .. Atracacao

' Dependências das Camadas de Serviço
ControladorCadastros ..> Navio : gerencia >
MotorDeFila ..> Navio : prioriza >
ControladorOperacao ..> Atracacao : registra >

@enduml

## 5. Mapeamento de Gargalos (Pente Fino)
A IA deve focar a refatoração nestes pontos críticos identificados no repositório:

- **Concorrência na GUI:**
  - O arquivo `gui/telas/fila_view.py`[cite: 11] e `gui/telas/painel_adm.py`[cite: 11] utilizam `Thread(target=worker)` para não travar a UI. A refatoração para `asyncio` deve substituir essas threads, utilizando `page.run_task` ou suporte nativo a `async` do Flet[cite: 8].
  
- **N+1 Queries Confirmadas:**
  - No arquivo `controller_operacao.py`[cite: 5], a função `obter_painel_vagas_dto` faz consultas separadas para `Vaga`, `Atracacao` e `Navio`. Isso deve ser consolidado em um `joinedload` único na consulta de `Atracacao` que traga o `Navio` e suas `Cargas`[cite: 5].
  - Em `controller_cadastros.py`, as funções como `auditar_solicitacoes_pendentes` já utilizam `joinedload(Navio.cargas)`, o que serve de exemplo, mas precisa ser migrado para a versão `Async` do SQLAlchemy[cite: 4].

- **Consistência de DTOs:**
  - O arquivo `dto.py` define a estrutura que o front-end consome. Qualquer mudança na query (Eager Loading) deve garantir que o `NavioDTO` receba os dados corretamente preenchidos sem causar erros de `AttributeError` no Flet[cite: 10].