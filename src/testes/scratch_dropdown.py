import flet as ft

try:
    dd1 = ft.Dropdown(options=[], prefix=ft.Icon(ft.Icons.LAYERS))
    print("prefix OK")
except Exception as e:
    print("prefix Error:", e)

try:
    dd2 = ft.Dropdown(options=[], prefix_icon=ft.Icons.LAYERS)
    print("prefix_icon OK")
except Exception as e:
    print("prefix_icon Error:", e)

try:
    dd3 = ft.Dropdown(options=[], icon=ft.Icons.LAYERS)
    print("icon OK")
except Exception as e:
    print("icon Error:", e)
