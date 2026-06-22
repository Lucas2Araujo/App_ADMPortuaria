# Testes Automatizados

O projeto possui duas suítes de testes localizadas em `src/`.

## Como executar

```bash
# Rodar todos os testes com relatório detalhado
pytest src/ -v

# Rodar apenas os testes da GUI
pytest src/test_gui.py -v

# Rodar apenas os testes do backend
pytest src/test_app.py -v
```

---

## Suíte 1 — Smoke tests de importação (`test_gui.py`)

**Classe:** `TestImportacaoModulos`

Verifica que todos os módulos do frontend importam sem levantar exceção. Se alguém introduzir um erro de sintaxe, remover uma dependência ou quebrar um import, esses testes falharão imediatamente no CI.

| Teste | O que verifica |
|-------|---------------|
| `test_importa_flet` | Pacote `flet` está instalado |
| `test_importa_painel_adm` | `painel_adm.py` importa sem erro |
| `test_importa_fila_view` | `fila_view.py` importa sem erro |
| `test_importa_painel_tripulacao` | `painel_tripulacao.py` importa sem erro |
| `test_importa_main_gui` | `main_gui.py` importa sem abrir janela (`ft.run` substituído por no-op) |

---

## Suíte 2 — Validação do formulário (`test_gui.py`)

**Classe:** `TestValidacaoFormularioNavio`

Testes unitários da função pura `validar_formulario_navio` de `painel_adm.py`.
Não requerem display gráfico nem banco de dados.

### Cenários cobertos

#### IMO
| Teste | Entrada | Resultado esperado |
|-------|---------|-------------------|
| `test_imo_vazio_e_obrigatorio` | `""` | erro em `imo` |
| `test_imo_com_espacos_e_obrigatorio` | `"   "` | erro em `imo` |
| `test_imo_com_menos_de_7_digitos` | `"12345"` | erro em `imo` |
| `test_imo_com_mais_de_7_digitos` | `"12345678"` | erro em `imo` |
| `test_imo_com_letras_invalido` | `"ABC1234"` | erro em `imo` |
| `test_imo_exatamente_7_digitos_valido` | `"1234567"` | sem erro |

#### Nome do Navio
| Teste | Entrada | Resultado esperado |
|-------|---------|-------------------|
| `test_nome_vazio_e_obrigatorio` | `""` | erro em `nome` |
| `test_nome_com_caracteres_especiais_invalido` | `"Navio@#$%"` | erro em `nome` |
| `test_nome_com_acentos_valido` | `"São Pedro"` | sem erro |
| `test_nome_com_hifen_e_apostrofo_valido` | `"D'Artagnan-II"` | sem erro |

#### Outros campos
| Teste | Campo | Comportamento |
|-------|-------|--------------|
| `test_capitao_vazio_e_obrigatorio` | capitao | erro se vazio |
| `test_capitao_com_caracteres_especiais_invalido` | capitao | erro com `Cap!@#` |
| `test_companhia_vazia_e_obrigatoria` | companhia | erro se vazio |
| `test_peso_zero_invalido` | peso | erro com `"0"` |
| `test_peso_negativo_invalido` | peso | erro com `"-10"` |
| `test_peso_decimal_invalido` | peso | erro com `"100.5"` (espera inteiro) |
| `test_categoria_vazia_obrigatoria` | categoria | erro se vazio |
| `test_categoria_none_obrigatoria` | categoria | erro se `""` (None do Dropdown) |

#### Cenários combinados
| Teste | O que verifica |
|-------|---------------|
| `test_dados_validos_sem_erros` | Dados completamente válidos → `{}` |
| `test_todas_categorias_validas` | As 4 categorias permitidas são aceitas |
| `test_todos_campos_vazios_retorna_todos_os_erros` | 6 campos vazios → 6 erros |
| `test_apenas_imo_invalido_nao_contamina_outros_campos` | Erro em IMO não afeta outros campos |

---

## Pipeline CI/CD

Os testes rodam automaticamente via GitHub Actions a cada `push` ou `pull_request`.
Veja a configuração em [`.github/workflows/ci.yml`](https://github.com/Lucas2Araujo/App_ADMPortuaria/blob/main/.github/workflows/ci.yml).
