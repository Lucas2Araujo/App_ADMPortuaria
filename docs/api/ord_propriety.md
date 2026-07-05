# Fila de Atracação e Motor de Regras

Aqui documentamos o coração da lógica de negócios: os algoritmos que definem dinamicamente a prioridade dos navios baseando-se em perecibilidade e regras anti-starvation.

> **Importante:** A estrutura de queries virtuais via SQLAlchemy e o cálculo matemático puro do score permanecem **síncronos** por serem processamentos de CPU (CPU-bound) limpos, enquanto a execução efetiva das queries na base de dados (ex: `obter_proximo_da_fila`) ocorre de forma **assíncrona**.

::: ord_propriety