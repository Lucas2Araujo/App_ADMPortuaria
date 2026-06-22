# Painel do Administrador — `painel_adm.py`

O **Painel ADM** é a tela central do AdminPort. Ela é composta por três abas internas, acessadas por botões de texto na parte superior:

## Abas do Painel

### 1. Visão Geral (Dashboard)

Exibe três cartões de métricas em tempo real consultados diretamente no banco de dados:

| Métrica | Descrição |
|---------|-----------|
| **Vagas Livres / Total** | Berços disponíveis vs. capacidade total |
| **Navios na Fila** | Embarcações com status `VALIDADO` aguardando atracação |
| **Auditorias Pendentes** | Pré-cadastros com status `PENDENTE` aguardando revisão |

Um botão de atualização (🔄) permite recarregar os dados a qualquer momento.

### 2. Gerenciar Embarcações

Formulário de **pré-cadastro** de navios com os seguintes campos:

| Campo | Tipo | Validação |
|-------|------|-----------|
| Número IMO | `TextField` (numérico) | Exatamente 7 dígitos |
| Nome do Navio | `TextField` | Sem caracteres especiais (`@#$%`) |
| Nome do Capitão | `TextField` | Sem caracteres especiais |
| Companhia | `TextField` | Sem caracteres especiais |
| Categoria da Carga | `Dropdown` | Obrigatório; 4 opções disponíveis |
| Peso Total (t) | `TextField` (numérico) | Inteiro positivo |
| Documentos Alfandegários | `Switch` | Booleano opcional |

#### Categorias de carga disponíveis

| Chave | Descrição |
|-------|-----------|
| `URGENTE_PERECIVEL` | Medicamentos / Carnes (Perecível) — prioridade máxima |
| `ALTA_PERECIBILIDADE` | Frutas / Laticínios (Perecível) |
| `BAIXA_PERECIBILIDADE` | Grãos Úmidos |
| `COMUM` | Carga Geral / Minérios / Contêineres |

### 3. Controle de Vagas

Tabela com todos os berços do porto e suas situações:

| Coluna | Descrição |
|--------|-----------|
| ID Vaga | Identificador numérico do berço |
| Status | `LIVRE` (verde) ou `OCUPADA` (vermelho) |
| Navio Atracado | Nome do navio presente |
| Tempo de Atracação | Minutos desde a atracação |
| Ações | Botão para **liberar a vaga** (desatracar) |

---

## Função de validação — `validar_formulario_navio`

Esta é a única função **pura e testável de forma isolada** do módulo. Ela não depende de UI nem de banco de dados.

Localização: `src/gui/telas/painel_adm.py`

```python
def validar_formulario_navio(
    imo: str,
    nome: str,
    capitao: str,
    companhia: str,
    peso: str,
    categoria: str,
) -> dict[str, str]:
    """Valida os dados do formulário de cadastro de navio.

    Recebe os valores brutos (strings) dos campos e retorna um dicionário
    com os erros encontrados. Chaves são os nomes dos campos e valores são
    as mensagens de erro. Um dicionário vazio significa que tudo está válido.

    Args:
        imo: Número IMO (deve conter exatamente 7 dígitos).
        nome: Nome do navio.
        capitao: Nome do capitão.
        companhia: Nome da companhia.
        peso: Peso total em toneladas (string numérica inteira).
        categoria: Categoria da carga selecionada.

    Returns:
        Dicionário ``{campo: mensagem_de_erro}`` — vazio se não houver erros.
    """
```

### Regras de validação

| Campo | Regra |
|-------|-------|
| `imo` | Obrigatório; exatamente 7 dígitos numéricos |
| `nome` | Obrigatório; apenas letras, números, acentos, espaços, `-` e `'` |
| `capitao` | Obrigatório; mesmas regras do nome |
| `companhia` | Obrigatório; mesmas regras do nome |
| `peso` | Obrigatório; inteiro positivo (`> 0`) |
| `categoria` | Obrigatório; qualquer string não-vazia |

---

## Fluxo interno de salvamento

```
salvar_navio(e)
  └─► validar_formulario_navio(...)   ← função pura
        ├── erros != {}  → exibe error_text em cada campo, retorna
        └── erros == {}  → chama solicitar_pre_cadastro(session, ...)
                              └─► status do navio: PENDENTE
```

> **Nota:** O salvamento bem-sucedido cria um navio com status `PENDENTE`.
> O administrador deve validar manualmente para que o navio ingresse na fila.
