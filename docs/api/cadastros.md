# Controladores de Cadastro

Esta seção detalha as funções responsáveis pelo pré-cadastro de navios, classificação de manifestos de carga e auditoria documental pelo Administrador.

> **Aviso de Assincronicidade:** Todas as funções de manipulação de banco de dados neste módulo agora são co-rotinas assíncronas (`async def`) e retornam *awaitables*. Elas não bloqueiam a thread principal.

::: controller_cadastros