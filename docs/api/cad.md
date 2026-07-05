# Banco de Dados (Models)

Abaixo estão listadas as entidades e tabelas de persistência configuradas via SQLAlchemy no arquivo `cad.py`.

> **Suporte Assíncrono:** Este modelo híbrido foi refatorado e suporta a antiga abordagem de queries com sessão padrão (`obter_sessao`) usando o conector nativo do Python, bem como a nova abordagem orientada a eventos (`obter_sessao_async`) utilizando `AsyncSession` e o pacote `aiosqlite`.

::: cad