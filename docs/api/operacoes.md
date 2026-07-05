# Controladores de Operação

Documentação das funções encarregadas de processar a atracação de navios em vagas livres, registrar desatracações e exibir o dashboard de vagas em tempo real.

> **Aviso de Assincronicidade:** As transações com o banco de dados nestes controladores funcionam de forma assíncrona (`async/await`) para suportar alto rendimento de leitura/escrita em tempo real sem travar a interface da aplicação.

::: controller_operacao