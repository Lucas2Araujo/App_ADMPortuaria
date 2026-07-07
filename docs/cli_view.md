# Interface de Linha de Comando (CLI)

O arquivo `src/app.py` é o ponto de entrada da versão **CLI** do AdminPort.
Ele expõe **todos os fluxos do sistema** — cadastro de navios, auditoria, atracação e desatracação — por meio de menus de texto interativos no terminal.

A implementação é 100% assíncrona: usa `asyncio` + `async/await` com SQLAlchemy e `aiosqlite` para que as operações de banco de dados nunca bloqueiem o event loop.

---

## Como iniciar

```bash
# A partir da raiz do projeto
python src/app.py
```

Ao iniciar, o sistema imprime o status do banco de dados e exibe o **menu principal**:

```
[STATUS] Banco de dados conectado. Navios registrados: 12. Berços disponíveis: 5.

========================================
  SISTEMA DE ADMINISTRAÇÃO PORTUÁRIA
========================================
[1] Portal da Tripulação
[2] Painel do Administrador
[0] Sair

Escolha uma opção:
```

---

## Portal da Tripulação

Destinado ao **capitão** ou representante do navio que deseja solicitar uma vaga no porto.

```
--- PORTAL DA TRIPULAÇÃO ---
[1] Solicitar Pré-Cadastro
[0] Voltar
```

### Opção 1 — Solicitar Pré-Cadastro

O sistema guia o usuário por um formulário passo a passo:

| Campo                        | Regras de validação                                                              |
|------------------------------|----------------------------------------------------------------------------------|
| **IMO**                      | Exatamente 7 dígitos numéricos (ex: `1234567` → salvo como `IMO1234567`)        |
| **Nome do Navio**            | Letras, números, espaços, hífens ou apóstrofos. Não pode ser vazio.             |
| **Nome do Capitão**          | Mesmas regras do nome do navio.                                                  |
| **Companhia**                | Mesmas regras do nome do navio.                                                  |
| **Categoria da Carga**       | Menu numerado de 0 a 9 (ver abaixo).                                             |
| **Peso Total (Toneladas)**   | Número inteiro positivo.                                                         |
| **Documentos da Alfândega**  | Resposta `S`/`N` (sim ou não).                                                  |

#### Categorias de carga disponíveis

```
--- Categoria da Carga ---
[1] Medicamentos e Vacinas          → URGENTE_PERECIVEL
[2] Carnes e Pescados Congelados    → URGENTE_PERECIVEL
[3] Frutas e Verduras Frescas       → ALTA_PERECIBILIDADE
[4] Laticínios e Derivados          → ALTA_PERECIBILIDADE
[5] Grãos Úmidos / Açúcar           → BAIXA_PERECIBILIDADE
[6] Grãos Secos (Soja, Milho)       → COMUM
[7] Minérios e Siderurgia           → COMUM
[8] Combustíveis e Petróleo         → COMUM
[9] Contêineres de Carga Geral      → COMUM
[0] Outros (Especificar manualmente)
```

Após o preenchimento, o navio é registrado com status **PENDENTE** e aguarda auditoria do administrador.

```
[CAPITÃO] Pré-cadastro realizado: Navio 'Santa Marta' (IMO1234567) adicionado com status PENDENTE.
```

---

## Painel do Administrador

Acesso via opção `[2]` no menu principal. Contém todas as operações de gestão do porto.

```
--- PAINEL DO ADMINISTRADOR ---
[1] Gerenciar Registros (Novo / Editar existentes)
[2] Auditar Solicitações Pendentes
[3] Ver Fila de Atracação
[4] Iniciar Próxima Atracação
[5] Registrar Saída (Desatracação)
[6] Ver Painel de Vagas Atuais
[7] Ver Histórico de Operações
[8] Excluir Registro de Navio
[9] Gerar Dados de Teste (Popular BD para testes)
[0] Voltar
```

---

### `[1]` Gerenciar Registros

Submenu para criar ou editar registros de navios diretamente pelo balcão administrativo.

```
--- GERENCIAR REGISTROS DE NAVIOS ---
[1] Novo Registro Manual (Balcão)   ← mesmo formulário da tripulação
[2] Editar Dados de um Navio Existente
[0] Cancelar
```

Na edição, pressionar `ENTER` sem digitar nada mantém o valor atual do campo.

---

### `[2]` Auditar Solicitações Pendentes

Processa todos os navios com status **PENDENTE** automaticamente:

- Se todos os documentos da alfândega estiverem corretos → status **VALIDADO** (entra na fila oficial).
- Se a documentação estiver incompleta → status **REJEITADO**.
- Se alguma carga possuir categoria `OUTROS_PENDENTE`, o admin é solicitado a classificá-la antes de continuar:

```
Atenção: O navio Santa Marta possui uma carga não classificada: [Produto especial].
[1] Ultra Perecível  [2] Alta Perecibilidade  [3] Baixa Perecibilidade  [4] Comum
Classifique a carga (1-4):
```

---

### `[3]` Ver Fila de Atracação

Exibe a fila ordenada por **score de prioridade** (calculado por `ord_propriety.py`):

```
POS  | IMO          | NOME DA EMBARCAÇÃO             | COMPANHIA                 | SCORE        | ESPERA
--------------------------------------------------------------------------------------------------------------
1    | IMO1234567   | Santa Marta                    | Cia. Marítima Norte       | 1850.50      | 0:12:34
2    | IMO7654321   | Porto Seguro                   | TransOceano Ltda.         | 1200.00      | 1:05:10
```

Navios com carga perecível recebem **bônus multiplicador** e sobem na fila.

---

### `[4]` Iniciar Próxima Atracação

```
--- INICIAR ATRACAÇÃO ---
[1] Atracar apenas o próximo navio
[2] Preencher todas as vagas livres automaticamente
[0] Cancelar
```

- Opção `[1]`: atracação única, confirma o navio e a vaga utilizados.
- Opção `[2]`: modo lote — repete o processo até não haver mais vagas livres ou navios na fila.

---

### `[5]` Registrar Saída (Desatracação)

Lista os navios atualmente atracados:

```
--- NAVIOS ATRACADOS ---
[1] Santa Marta (IMO: IMO1234567) - Vaga 2
[2] Porto Seguro (IMO: IMO7654321) - Vaga 4
[T] Desatracar TODOS os navios
[0] Cancelar

Escolha o número, digite o IMO, ou [T] para todos:
```

---

### `[6]` Ver Painel de Vagas Atuais

Exibe o status atual de todos os berços com cores ANSI:

```
======================================================================
DASHBOARD DO PORTO - STATUS DAS VAGAS
Total: 5 | Disponíveis: 3 | Ocupadas: 2
======================================================================
Vaga 1  [CONTAINER] - [LIVRE]
Vaga 2  [CONTAINER] - [OCUPADA] -> Navio: Santa Marta (IMO: IMO1234567) - Atracado desde: 2026-07-07 10:30:00
```

---

### `[7]` Ver Histórico de Operações

Log cronológico de todas as atracações e desatracações registradas no sistema:

```
DATA/HORA            | EVENTO           | NAVIO (IMO)     | VAGA    | OP ID
-----------------------------------------------------------------------------
2026-07-07 10:30:00  | [+] ATRACAÇÃO    | IMO1234567      | Vaga 2  | OP-001
2026-07-07 11:15:00  | [-] DESATRACAÇÃO | IMO9876543      | Vaga 1  | OP-002
```

---

### `[8]` Excluir Registro de Navio

Localiza o navio pelo número da lista ou pelos 7 dígitos do IMO e o remove **permanentemente** do banco.

---

### `[9]` Gerar Dados de Teste

Utilitário para popular o banco rapidamente durante o desenvolvimento:

```
--- GERAR DADOS DE TESTE ---
[1] Adicionar apenas novos navios (Manter banco atual)
[2] Resetar TUDO (Apagar banco e recriar)
[0] Cancelar
```

!!! warning "Atenção"
    A opção `[2]` remove **todos** os dados existentes no banco `porto.db` antes de recriar.
