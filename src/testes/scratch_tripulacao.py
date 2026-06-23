import flet as ft
import sys

sys.path.insert(0, "./gui/telas")
sys.path.insert(0, ".")

from gui.telas.painel_tripulacao import obter_view


def main(page: ft.Page):
    try:
        view = obter_view(page)
        print("obter_view executou com sucesso!")
        page.add(view)
    except Exception as e:
        print("Erro ao executar obter_view:", type(e).__name__, e)


if __name__ == "__main__":
    ft.app(target=main)
