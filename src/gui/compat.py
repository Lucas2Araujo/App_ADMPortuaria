import flet as ft

# Patch border
try:
    import flet.controls.border as flet_border

    if not hasattr(flet_border, "all"):
        flet_border.all = ft.Border.all
        flet_border.only = ft.Border.only
        flet_border.symmetric = ft.Border.symmetric
except Exception:
    pass

# Patch padding
try:
    import flet.controls.padding as flet_padding

    if not hasattr(flet_padding, "all"):
        flet_padding.all = ft.Padding.all
        flet_padding.only = ft.Padding.only
        flet_padding.symmetric = ft.Padding.symmetric
except Exception:
    pass

# Patch alignment
try:
    import flet.controls.alignment as flet_alignment

    if not hasattr(flet_alignment, "center"):
        flet_alignment.center = ft.alignment.Alignment(0, 0)
        flet_alignment.top_left = ft.alignment.Alignment(-1, -1)
        flet_alignment.top_right = ft.alignment.Alignment(1, -1)
        flet_alignment.bottom_left = ft.alignment.Alignment(-1, 1)
        flet_alignment.bottom_right = ft.alignment.Alignment(1, 1)
        flet_alignment.top_center = ft.alignment.Alignment(0, -1)
        flet_alignment.bottom_center = ft.alignment.Alignment(0, 1)
        flet_alignment.left = ft.alignment.Alignment(-1, 0)
        flet_alignment.right = ft.alignment.Alignment(1, 0)
except Exception:
    pass
