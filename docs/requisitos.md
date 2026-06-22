# **Documento de Especificação de Requisitos**

## **Projeto: Sistema de Administração Portuária** 

### **1\. Introdução**

Este documento descreve os requisitos funcionais e não-funcionais para o sistema de gerenciamento de embarque e desembarque de produtos. O foco principal é a automação da fila de atracação utilizando critérios de prioridade baseados na natureza da carga.

### **2\. Requisitos Funcionais (RF)**

| ID | Nome | Descrição |
| :---- | :---- | :---- |
| **RF01** | Manter Cadastro de Navios | Permitir a inclusão, alteração e exclusão de navios com IMO ID, Nome do Navio, Nome do Capitão e Companhia |
| **RF02** | Registrar Carga | Vincular ao navio os dados da carga, incluindo categoria, peso, sinalizador de perecibilidade e declaração de documentos aduaneiros. |
| **RF03** | Gerenciar Fila de Espera | Visualizar a ordem dos navios aguardando atracação. |
| **RF04** | Priorização de Cargas Perecíveis | Aplicar lógica de negócio onde cargas perecíveis assumem prioridade máxima na fila. |
| **RF05** | Controle de Atracação | Registrar o horário de entrada do navio na vaga e o horário de saída (desatracação). |
| **RF06** | Status de Vagas | Exibir o estado atual (Disponível/Ocupada) de cada berço do porto. |
| **RF07** | Pré-Cadastro Remoto | Permitir que a tripulação envie dados do navio e carga antes da chegada física. |
| **RF08** | Fluxo de Aprovação | O Administrador deve validar ou rejeitar solicitações de pré-cadastro. |
| **RF09** | Rastreamento de Status | O sistema deve manter o status do navio (Pendente, Validado, Atracado, Finalizado). |

### **3\. Requisitos Não-Funcionais (RNF)**

| ID | Nome | Descrição |
| :---- | :---- | :---- |
| **RNF01** | Usabilidade | O sistema deve ser simples o suficiente para operação rápida em ambiente portuário. |
| **RNF02** | Confiabilidade | O registro de horários de entrada e saída deve ser preciso e imutável após a finalização. |
| **RNF03** | Disponibilidade | O sistema deve estar operacional 24/7 para atender o fluxo contínuo do porto. |

### **4\. Regras de Negócio (RN)**

* **RN01 \- Cálculo de Fila:** Cargas perecíveis recebem prioridade máxima no cálculo de Score. O desempate e a justiça na fila (evitando *starvation*) são garantidos por um bônus dinâmico baseado no tempo de espera do navio desde a sua solicitação.  
* **RN02 \- Liberação de Vaga:** Uma vaga só pode ser ocupada por um novo navio após o registro de saída do navio anterior.  
* **RN03 \- Bloqueio de Fila:** Um navio só pode ingressar na fila de atracação oficial após o status de validação ser alterado para "VALIDADO" pelo Administrador.  
* **RN04 \- Prioridade de Perecíveis:** A lógica de prioridade é aplicada no exato momento da validação, calculando a nova ordem da fila instantaneamente.

