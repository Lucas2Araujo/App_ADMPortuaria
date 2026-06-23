import flet as ft
import time
from threading import Thread

def main(page: ft.Page):
    conteudo_principal = ft.Container()
    page.add(conteudo_principal)
    page.update()
    
    container_inner = ft.Container(content=ft.Text("Hello Inner"))
    conteudo_principal.content = container_inner
    page.update()
    
    print("Initial check:")
    print("conteudo_principal.page:", conteudo_principal.page)
    print("container_inner.page:", container_inner.page)
    
    def background_checker():
        time.sleep(1)
        print("After 1s in background:")
        print("conteudo_principal.page:", conteudo_principal.page)
        print("container_inner.page:", container_inner.page)
        
        # Now replace it
        container_new = ft.Container(content=ft.Text("Hello New"))
        conteudo_principal.content = container_new
        page.update()
        time.sleep(1)
        print("After replacement in background:")
        print("container_inner.page:", container_inner.page)
        print("container_new.page:", container_new.page)
        
        # Exit program safely
        page.controls.clear()
        page.update()

    Thread(target=background_checker).start()

ft.run(main)
