import flet as ft
def handler(e): pass
try:
    d = ft.Dropdown(options=[ft.dropdown.Option("A")], on_change=handler)
    print("on_change works")
except Exception as e:
    print("on_change error:", e)

try:
    d = ft.Dropdown(options=[ft.dropdown.Option("A")], on_select=handler)
    print("on_select works")
except Exception as e:
    print("on_select error:", e)

try:
    d = ft.Dropdown(options=[ft.dropdown.Option("A")], on_text_change=handler)
    print("on_text_change works")
except Exception as e:
    print("on_text_change error:", e)
