## Ideia inicial do motor da fila

os dados estão sendo recebidos nesse formato:
```json
{
  "imo_id": "A-0001",
  "nome": "Base da Virgínia",
  "comandante": "Capitão Trombadinha",
  "manifesto": [
    {
      "descricao": "Frutas Frescas",
      "categoria": "ALTA_PERECIVEL",
      "quantidade_toneladas": 300
    },
    {
      "descricao": "Laticínios",
      "categoria": "ALTA_PERECIVEL",
      "quantidade_toneladas": 100
    }
  ]
}
```

O script de ordenação dessa fila proprietária está entre algoritmo baseado em regra e soma ponderada

---

## Possíveis Erros Econtrados

1. Cargas não perecíveis nunca será atendida
    Se todo dia aparecer alimentos perecíveis, possivelmente a carga atual sempre ficará para baixo, por conseguite sendo um último e nunca atendido.

    OBS.: Aumentar o peso da soma não funcionaria ao longo prazo (meu sexto sentido me diz, confia)

2. O TEMPO não está sendo levado em consideração
    Tanto o tempo da viagem quanto o tempo de espera devem ser levados em consideração, ....


    