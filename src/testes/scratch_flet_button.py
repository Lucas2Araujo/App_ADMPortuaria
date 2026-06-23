import flet as ft

try:
    btn = ft.ElevatedButton("Enviar Declaração")
    print("btn1 OK")
except Exception as e:
    print("btn1 Error:", e)

try:
    btn2 = ft.ElevatedButton(text="Enviar Declaração")
    print("btn2 OK")
except Exception as e:
    print("btn2 Error:", type(e).__name__, e)

try:
    btn3 = ft.ElevatedButton("Enviar", icon=ft.Icons.DOCK)
    print("btn3 OK")
except Exception as e:
    print("btn3 Error:", type(e).__name__, e)

try:
    dd = ft.Dropdown(prefix_icon=ft.Icons.LAYERS, options=[])
    print("Dropdown prefix_icon OK")
except Exception as e:
    print("Dropdown Error:", e)
