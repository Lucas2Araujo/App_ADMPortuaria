# Fila de Atracação — `fila_view.py`

O **Fila de Atracação** é o painel público que exibe a ordem atual das embarcações validadas aguardando para atracar no porto, calculada dinamicamente pelo algoritmo do motor de prioridades.

## Funcionalidades implementadas

- **Fila de Atracação Dinâmica**: Tabela ordenada em tempo real pela pontuação de score de prioridade de cada navio.
- **Auto-Atualização (Auto-Refresh)**: Loop em segundo plano que executa a cada 2 segundos atualizando a fila visual automaticamente sem exigir recarga manual de página.
- **Ficha Técnica Individual**: Ação de "Ver mais" que exibe em um popup/modal os detalhes técnicos da embarcação e suas respectivas cargas vinculadas (Capitão, Categoria, Manifesto de Carga, Perecibilidade, Documentos, Peso e Score).

## Critérios de Priorização

A ordem da fila é calculada pelo serviço `calcular_score` baseado nas regras de negócio (do motor `ord_propriety.py`):
1. **Peso da Carga**: O score cresce conforme a quantidade de toneladas e o peso da categoria da carga.
2. **Prioridade de Perecíveis**: Navios com cargas classificadas como urgentes/perecíveis recebem bônus de pontuação massivos de +10000 a +30000.
3. **Regra Anti-Starvation**: Navios que esperam mais tempo na fila oficial recebem um bônus dinâmico no tempo de espera (+1000 pontos por hora) para evitar inanição.

> **Separação de Papéis:** A tela de Fila de Atracação é estritamente **somente-leitura** para permitir consulta pública para tripulações e operadoras. A ação de alocar (atracar) os navios nas vagas físicas e gerenciar os berços é feita de forma exclusiva pelo Administrador no menu **Monitor de Berços** do painel ADM.
