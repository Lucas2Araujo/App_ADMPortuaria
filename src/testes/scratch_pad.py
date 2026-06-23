import flet as ft

print(ft.__version__)
try:
    print(ft.padding.only(top=5, bottom=5))
except Exception as e:
    print("padding.only:", type(e).__name__, e)

try:
    print(ft.Padding(left=0, top=5, right=0, bottom=5))
except Exception as e:
    print("Padding kwargs:", type(e).__name__, e)

try:
    print(ft.Padding(0, 5, 0, 5))
except Exception as e:
    print("Padding positional:", type(e).__name__, e)
