"""
conftest.py — Configuração global do Pytest para a suite de testes do AdminPort.

Este arquivo é carregado AUTOMATICAMENTE pelo Pytest antes de qualquer coleta
ou execução de testes. Ele garante que os módulos de `src/` estejam sempre
no sys.path, independentemente de como o pytest é invocado:

  - `pytest src/` (da raiz do projeto, com ou sem PYTHONPATH=src)
  - `cd src && python -m pytest testes/`
  - via GitHub Actions CI (com PYTHONPATH: src no env)

Centraliza aqui o que antes estava espalhado em cada arquivo de teste,
eliminando duplicação e garantindo consistência.
"""

import sys
import os

# Garante que src/ esteja no path (caso não esteja via PYTHONPATH)
_DIR_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # → src/
if _DIR_SRC not in sys.path:
    sys.path.insert(0, _DIR_SRC)
