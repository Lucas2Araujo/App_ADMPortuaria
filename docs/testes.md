# Testes Automatizados

O projeto possui uma robusta suíte de testes organizados na pasta `src/testes/`. Eles garantem que as regras de negócios, a interface gráfica (GUI) e a interface de terminal (CLI) funcionem corretamente.

Os arquivos foram agrupados logicamente pelas responsabilidades de cada componente testado.

---

## Estrutura de Testes

### 1. Testes de Backend (`src/testes/backend/`)
Focam na validação das regras de negócios profundas e do acesso ao banco de dados:
- **`test_ord_propriety.py`**: Valida unitariamente o motor matemático de pontuação. Garante que os pesos por tipo de carga e os bônus exponenciais e de envelhecimento da fila anti-starvation estão funcionando corretamente.
- **`test_integracao_operacao.py`**: Testes de integração de fluxos completos. Simula ações reais usando banco de dados SQLite em memória para pré-cadastro de navios, validação de filas e registro de histórico de movimentações portuárias.

### 2. Testes da Interface Gráfica (`src/testes/gui/`)
Certificam-se de que as telas Flet funcionem sem quebrar ou renderizar problemas:
- **`test_gui.py`**: Smoke tests (verifica se nenhuma tela possui erros sintáticos de importação) e testes rigorosos e unitários da função pura `validar_formulario_navio` do painel administrativo.
- **`test_componentes_flet.py`**: Simula cenários reais usando as Views do Flet, verificando se modais abrem, se botões de auditoria acionam as mudanças corretas de status da interface e se os dados são persistidos na tela do operador administrativo.

### 3. Testes da Linha de Comando (`src/testes/cli/`)
- **`test_app.py`**: Simula a entrada de dados (stdin) no formulário iterativo do terminal do usuário (CLI), garantindo que as validações e o registro do banco de dados continuem funcionais sem a necessidade de uma GUI instanciada.

---

## Como executar (Local e no CI)

As GitHub Actions já rodam `pytest src/` automaticamente a cada commit, englobando todas as subpastas. Mas localmente, você pode executar de forma refinada:

```bash
# 1. Rodar todos os testes de uma só vez (Backend, GUI e CLI)
pytest src/ -v

# 2. Rodar apenas os testes do motor do Backend (muito rápido, não carrega GUI)
pytest src/testes/backend/ -v

# 3. Rodar apenas testes relativos à Interface Gráfica (Flet)
pytest src/testes/gui/ -v

# 4. Rodar apenas simulações do Terminal (CLI)
pytest src/testes/cli/ -v
```

> **Dica**: No VSCode ou PyCharm, todos esses testes são reconhecidos automaticamente pelo menu "Testing", pois todos começam com o prefixo `test_`.
