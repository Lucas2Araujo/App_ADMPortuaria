# Portal da Tripulação — `painel_tripulacao.py`

O **Portal da Tripulação** é a interface simplificada destinada aos capitães ou operadores externos das embarcações para realizar o pré-cadastro antes da chegada física ao cais.

## Funcionalidades implementadas

- **Formulário de Pré-Cadastro Remoto**: Permite declarar os detalhes da embarcação e de seu manifesto de carga.
- **Campos de entrada e validações**:
  - Número IMO (7 dígitos obrigatórios)
  - Nome da Embarcação
  - Nome do Capitão
  - Companhia / Armador
  - Categoria da Carga (Dropdown com opções predefinidas)
  - Peso Total em Toneladas
  - Declaração de Documentos de Liberação Alfandegária (Switch)

## Integração com o Backend

Ao enviar a declaração de chegada, a interface executa a função pura de validação `validar_formulario_navio`. Se nenhum erro for encontrado, chama o serviço `solicitar_pre_cadastro` da camada lógica:

```python
solicitar_pre_cadastro(
    session=session,
    imo=imo_formatado,
    nome=nome_formatado,
    capitao=capitao,
    companhia=companhia,
    carga_desc=f"Carga: {categoria}",
    categoria=categoria,
    peso=peso,
    eh_perecivel=eh_perecivel,
    possui_documentos=possui_documentos,
)
```

> **Nota:** Por padrão, todos os navios cadastrados remotamente são salvos no banco de dados com o status `PENDENTE`. Eles permanecem isolados e não ingressam na fila de atracação oficial até que um Administrador aprove a solicitação após a auditoria documental.
