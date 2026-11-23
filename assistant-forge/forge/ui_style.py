"""Style et mise en forme de l'interface Forge Assistant (police, thème ttk, ornements, barre de titre Windows)."""

from __future__ import annotations

import sys

from forge import theme as T
from forge.chemins import chemin_data
from forge.erreurs import noter as _noter_erreur


def charger_police_dofus() -> bool:
    """Charge Roboto Condensed pour cette application seulement."""
    if sys.platform != "win32":
        return False
    fichier = chemin_data("fonts", "RobotoCondensed.ttf")
    if not fichier.is_file():
        return False
    try:
        import ctypes
        ajouter = ctypes.windll.gdi32.AddFontResourceExW
        ajouter.argtypes = (ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p)
        ajouter.restype = ctypes.c_int
        return ajouter(str(fichier), 0x10, None) > 0
    except Exception:
        _noter_erreur("fenetre_forge.charger_police_dofus")
        return False


def appliquer_theme(racine):
    """Habille les widgets façon atelier de forgemagie DOFUS, avec l'accent de la flammèche."""
    from tkinter import ttk
    st = ttk.Style(racine)
    try:
        st.theme_use("clam")
    except Exception:
        _noter_erreur("fenetre_forge.appliquer_theme")
    st.configure(".", background=T.PANNEAU, foreground=T.OS, fieldbackground=T.CARTE,
                 font=(T.POLICE, 9), bordercolor=T.PANNEAU, lightcolor=T.PANNEAU,
                 darkcolor=T.PANNEAU, troughcolor=T.PANNEAU, focuscolor=T.ACCENT)
    st.configure("TFrame", background=T.PANNEAU)
    st.configure("TLabel", background=T.PANNEAU, foreground=T.OS)
    st.configure("TCheckbutton", background=T.PANNEAU, foreground=T.OS,
                 indicatorbackground=T.CARTE, indicatorforeground=T.ACCENT)
    st.map("TCheckbutton", background=[("active", T.PANNEAU)],
           foreground=[("active", T.ACCENT_CLAIR)], indicatorbackground=[("selected", T.TITRE)])
    st.configure("Compact.TCheckbutton", background=T.PANNEAU, foreground=T.OS_DOUX,
                 indicatorbackground=T.CARTE, indicatorforeground=T.ACCENT,
                 font=(T.POLICE, 8), padding=(0, 0))
    st.map("Compact.TCheckbutton", background=[("active", T.PANNEAU)],
           foreground=[("active", T.ACCENT_CLAIR)], indicatorbackground=[("selected", T.TITRE)])
    st.configure("Ligne.TCheckbutton", background=T.LIGNE, foreground=T.OS,
                 indicatorbackground=T.PANNEAU, indicatorforeground=T.ACCENT, padding=0)
    st.map("Ligne.TCheckbutton", background=[("active", T.LIGNE)],
           foreground=[("active", T.ACCENT_CLAIR)], indicatorbackground=[("selected", T.TITRE)])
    st.configure("LignePaire.TCheckbutton", background=T.LIGNE_PAIRE, foreground=T.OS,
                 indicatorbackground=T.PANNEAU, indicatorforeground=T.ACCENT, padding=0)
    st.map("LignePaire.TCheckbutton", background=[("active", T.LIGNE_PAIRE)],
           foreground=[("active", T.ACCENT_CLAIR)], indicatorbackground=[("selected", T.TITRE)])
    if T.NOM == "kabhal":
        st.configure("TCheckbutton", indicatorbackground="#0c1213", indicatorforeground="#8ff7e6")
        st.map("TCheckbutton", indicatorbackground=[("selected", "#18645b"), ("active", "#152021")])
        st.configure("Compact.TCheckbutton", indicatorbackground="#0c1213", indicatorforeground="#8ff7e6")
        st.map("Compact.TCheckbutton", indicatorbackground=[("selected", "#18645b"), ("active", "#152021")])
        st.configure("Ligne.TCheckbutton", background="#141c1d", indicatorbackground="#0b1011",
                     indicatorforeground="#8ff7e6")
        st.map("Ligne.TCheckbutton", background=[("active", "#141c1d")],
               indicatorbackground=[("selected", "#18645b")])
        st.configure("LignePaire.TCheckbutton", background="#101718", indicatorbackground="#0b1011",
                     indicatorforeground="#8ff7e6")
        st.map("LignePaire.TCheckbutton", background=[("active", "#101718")],
               indicatorbackground=[("selected", "#18645b")])
        st.configure("TEntry", fieldbackground="#0b1011", foreground=T.OS, insertcolor=T.OS,
                     bordercolor="#334345", lightcolor="#334345", darkcolor="#334345",
                     borderwidth=1, padding=(3, 4), relief="solid")
        st.map("TEntry", bordercolor=[("focus", T.ACCENT)], lightcolor=[("focus", T.ACCENT)],
               darkcolor=[("focus", T.ACCENT)])
        st.configure("TSpinbox", fieldbackground="#0b1011", foreground=T.OS, arrowcolor=T.ACCENT,
                     bordercolor="#334345", lightcolor="#334345", darkcolor="#334345",
                     borderwidth=1, padding=(3, 3))
        st.configure("TCombobox", fieldbackground="#0b1011", background="#1c2627", foreground=T.OS,
                     arrowcolor=T.ACCENT, bordercolor="#334345", lightcolor="#334345", darkcolor="#334345",
                     borderwidth=1, padding=(4, 3))
    else:
        st.configure("TEntry", fieldbackground=T.FOND, foreground=T.OS, insertcolor=T.OS,
                     bordercolor=T.PANNEAU, lightcolor=T.PANNEAU, darkcolor=T.PANNEAU,
                     padding=(3, 3), relief="flat")
        st.configure("TSpinbox", fieldbackground=T.FOND, foreground=T.OS, arrowcolor=T.ACCENT,
                     bordercolor=T.PANNEAU, padding=(3, 3))
    st.configure("TNotebook", background=T.FOND, borderwidth=0, tabmargins=(0, 1, 0, 0))
    st.configure("TNotebook.Tab", background=T.FOND, foreground=T.OS_DOUX,
                 width=7, padding=(6, 6), font=(T.POLICE_TITRE, 10, "bold"), borderwidth=0,
                 lightcolor=T.PANNEAU, darkcolor=T.PANNEAU)
    st.map("TNotebook.Tab", background=[("selected", T.TITRE_FONCE), ("active", T.CARTE)],
           foreground=[("selected", T.ACCENT_CLAIR), ("active", T.OS)])
    st.configure("Atelier.TNotebook", background=T.PANNEAU, borderwidth=0, tabmargins=0)
    st.layout("Atelier.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
    # Les onglets restent sélectionnables, mais leur bande native est invisible :
    # la barre Canvas au-dessus est l'unique navigation affichée.
    st.configure("Atelier.TNotebook.Tab", padding=0, width=0)
    st.layout("Atelier.TNotebook.Tab", [])
    if T.NOM == "kabhal":
        st.configure("TButton", background="#1c2627", foreground=T.OS, padding=(10, 5),
                     font=(T.POLICE_TITRE, 9, "bold"), borderwidth=1, relief="solid",
                     bordercolor="#4a5857", lightcolor="#4a5857", darkcolor="#283233", focusthickness=0)
        st.map("TButton", background=[("active", "#263537"), ("pressed", "#121a1b")],
               bordercolor=[("active", "#708482")], foreground=[("active", "#f0faf8")])
        st.configure("Accent.TButton", background="#135950", foreground="#eefaf8",
                     padding=(12, 5), font=(T.POLICE_TITRE, 9, "bold"), borderwidth=1, relief="solid",
                     bordercolor="#35b8a7", lightcolor="#35b8a7", darkcolor="#0e403a", focusthickness=0)
        st.map("Accent.TButton", background=[("active", "#1b786c"), ("pressed", "#0d3d37")],
               bordercolor=[("active", "#72f5e4")])
        st.configure("Quiet.TButton", background="#141e1f", foreground=T.OS,
                     padding=(9, 5), font=(T.POLICE_TITRE, 9, "bold"), borderwidth=1, relief="solid",
                     bordercolor="#3a494a", lightcolor="#3a494a", darkcolor="#1d2627", focusthickness=0)
        st.map("Quiet.TButton", background=[("active", "#1e2c2e"), ("pressed", "#101718")],
               bordercolor=[("active", "#587072")], foreground=[("active", T.ACCENT_CLAIR)])
    else:
        st.configure("TButton", background=T.BOUTON, foreground=T.OS, padding=(10, 5),
                     font=(T.POLICE_TITRE, 9, "bold"), borderwidth=0, focusthickness=0)
        st.map("TButton", background=[("active", T.SURVOL), ("pressed", T.TITRE)],
               foreground=[("active", T.OS)])
        st.configure("Accent.TButton", background=T.BOUTON_OR, foreground=T.TEXTE_BOUTON_OR,
                     padding=(12, 5), font=(T.POLICE_TITRE, 9, "bold"), borderwidth=0, focusthickness=0)
        st.map("Accent.TButton", background=[("active", T.BOUTON_OR_CLAIR), ("pressed", T.TITRE)])
        st.configure("Quiet.TButton", background=T.PANNEAU, foreground=T.ACCENT_CLAIR,
                     padding=(8, 5), font=(T.POLICE_TITRE, 9, "bold"), borderwidth=0, focusthickness=0)
        st.map("Quiet.TButton", background=[("active", T.CARTE), ("pressed", T.TITRE)])
    st.configure("TScrollbar", background=T.CARTE, troughcolor=T.PANNEAU,
                 arrowcolor=T.OS_DOUX, bordercolor=T.PANNEAU)
    st.configure("Vertical.TScrollbar", background=T.CARTE, troughcolor=T.PANNEAU,
                 arrowcolor=T.OS_DOUX, bordercolor=T.PANNEAU)
    barres_defilement_sombres(st)
    if T.NOM == "kabhal":
        _appliquer_ornements_ttk(st, racine)


def _appliquer_ornements_ttk(st, racine):
    """Habillage 9-patch métallique/bronze pour boutons et champs du thème kabhal (repli silencieux)."""
    try:
        from forge.rendu_image import image_bouton_9patch, image_champ_9patch, vers_photo
        existants = set(st.element_names())
        imgs = getattr(racine, "_images_style", {})
        for style, variante, pad in (("TButton", "normal", (10, 5)),
                                     ("Accent.TButton", "accent", (12, 5)),
                                     ("Quiet.TButton", "quiet", (9, 5))):
            elem = f"KabhalBtn_{variante}.border"
            if elem not in existants:
                imgs[(variante, "repos")] = vers_photo(image_bouton_9patch("repos", variante), racine)
                imgs[(variante, "survol")] = vers_photo(image_bouton_9patch("survol", variante), racine)
                imgs[(variante, "presse")] = vers_photo(image_bouton_9patch("presse", variante), racine)
                st.element_create(
                    elem, "image", imgs[(variante, "repos")],
                    ("pressed", imgs[(variante, "presse")]),
                    ("active", imgs[(variante, "survol")]),
                    border=10, sticky="nsew", padding=pad,
                )
            st.layout(style, [(elem, {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})])
        elem_e = "KabhalEntry.field"
        if elem_e not in existants:
            imgs[("entry", "repos")] = vers_photo(image_champ_9patch(False), racine)
            imgs[("entry", "focus")] = vers_photo(image_champ_9patch(True), racine)
            st.element_create(
                elem_e, "image", imgs[("entry", "repos")],
                ("focus", imgs[("entry", "focus")]),
                border=6, sticky="nsew", padding=(5, 4),
            )
        st.layout("TEntry", [(elem_e, {"sticky": "nswe", "children": [("Entry.textarea", {"sticky": "nswe"})]})])
        racine._images_style = imgs
    except Exception:
        pass


def _couleur_windows(hexa: str) -> int:
    """« #rrggbb » -> COLORREF Windows (0x00BBGGRR)."""
    r, v, b = T._rgb(hexa)
    return (b << 16) | (v << 8) | r


def barre_titre_sombre(racine) -> bool:
    """(v166) Barre de titre Windows (fermer, réduire…) aux couleurs du thème kabhal.

    Windows 11 : couleur de la barre, du texte et du bord. Windows 10 récent : mode sombre seulement.
    Ne touche qu'à l'apparence de NOTRE fenêtre ; rien n'est envoyé au jeu. Sans effet ailleurs que sous Windows.
    """
    if sys.platform != "win32" or T.NOM != "kabhal":
        return False
    try:
        import ctypes
        racine.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(racine.winfo_id())
        dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute

        def _poser(attribut, valeur):
            v = ctypes.c_int(valeur)
            return dwm(hwnd, attribut, ctypes.byref(v), ctypes.sizeof(v)) == 0

        ok = _poser(20, 1) or _poser(19, 1)  # mode sombre (19 = anciennes versions de Windows 10)
        _poser(35, _couleur_windows(T.FOND))      # couleur de la barre (Windows 11)
        _poser(36, _couleur_windows(T.OS_DOUX))   # couleur du titre
        _poser(34, _couleur_windows(T.FILET))     # couleur du bord
        return ok
    except Exception:
        _noter_erreur("fenetre_forge.barre_titre_sombre")
        return False


def barres_defilement_sombres(st) -> None:
    """(v166) Thème kabhal : barres de défilement fines et sombres, sans flèches."""
    if T.NOM != "kabhal":
        return
    try:
        for sens, colle in (("Vertical", "ns"), ("Horizontal", "we")):
            nom = f"{sens}.TScrollbar"
            st.layout(nom, [(f"{sens}.Scrollbar.trough", {"sticky": colle, "children": [
                (f"{sens}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
            st.configure(nom, background=T.SURVOL, troughcolor=T.PANNEAU, bordercolor=T.PANNEAU,
                         lightcolor=T.SURVOL, darkcolor=T.SURVOL, arrowcolor=T.OS_DOUX, gripcount=0, width=8)
            st.map(nom, background=[("pressed", T.FILET), ("active", T.FILET), ("disabled", T.PANNEAU)],
                   lightcolor=[("pressed", T.FILET), ("active", T.FILET), ("disabled", T.PANNEAU)],
                   darkcolor=[("pressed", T.FILET), ("active", T.FILET), ("disabled", T.PANNEAU)])
    except Exception:
        _noter_erreur("fenetre_forge.barres_defilement_sombres")
