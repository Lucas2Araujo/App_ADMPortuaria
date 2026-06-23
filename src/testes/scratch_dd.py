import flet as ft

print(ft.__version__)
import inspect

print(inspect.signature(ft.Dropdown.__init__))
