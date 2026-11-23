"""Dessin de la fenêtre sur des Canvas tkinter : bandeau, en-tête, tableau aux rangées arrondies.

Adapte le rendu au thème actif (par défaut « kabhal ») ; repli géométrique si les images ne sont pas disponibles.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from forge import theme as T
from forge.erreurs import noter as _noter_erreur

HAUTEUR_RANGEE = 31
ESPACE = 2
HAUT_TABLEAU = 22
CADRE_TABLEAU = "#8a7c5c"   # (v170) filet doré du tableau (thème kabhal)


def rect_arrondi(c, x0, y0, x1, y1, r=6, **kw):
    """Coins discrets inspirés des rangées de l'atelier DOFUS."""
    r = max(2, min(int(r), 7))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r,
           x1, y1, x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r,
           x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def pastille(c, x0, y0, x1, y1, texte, fond, couleur_texte, police=None):
    """Petit cartouche de jeu aux coins sobres, jamais une capsule."""
    rect_arrondi(c, x0, y0, x1, y1, r=4, fill=fond, outline="")
    c.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=texte, fill=couleur_texte,
                  font=police or (T.POLICE, 8, "bold"))


def dessiner_sceau_ame(c, x: int, y: int, taille: int = 18, couleur: str = ""):
    """Petit sceau de flamme en trait continu, reutilisable dans les titres d'atelier."""
    couleur = couleur or T.ACCENT_CLAIR
    s = max(10, int(taille))
    contours = (((.25,.86),(.08,.62),(.25,.48),(.38,.34)),
                ((.38,.34),(.30,.17),(.39,.08),(.54,.31)),
                ((.54,.31),(.76,.08),(.95,.36),(.82,.61)),
                ((.82,.61),(.76,.82),(.62,.91),(.50,.96)))
    for segment in contours:
        pts = [coord for px, py in segment for coord in (x + px*s, y + py*s)]
        c.create_line(*pts, smooth=True, splinesteps=14, fill=couleur, width=max(1, s/13))
    spirale = (((.43,.73),(.34,.60),(.48,.47),(.62,.55)),
               ((.62,.55),(.76,.65),(.64,.77),(.52,.68)))
    for segment in spirale:
        pts = [coord for px, py in segment for coord in (x + px*s, y + py*s)]
        c.create_line(*pts, smooth=True, splinesteps=12, fill=couleur, width=max(1, s/16))
    r = max(1, s/17)
    c.create_polygon(x + .73*s, y + .23*s-r, x + .73*s+r, y + .23*s,
                     x + .73*s, y + .23*s+r, x + .73*s-r, y + .23*s,
                     fill=couleur, outline="")


# police pixel 5x7 : juste les lettres du titre (aucun fichier de police à installer)
_GLYPHES = {
    "F": ("11111", "10000", "11110", "10000", "10000", "10000", "10000"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
}


def texte_pixel(c, x, y, texte: str, taille: int, couleur: str, ombre: str = "") -> int:
    """Écrit `texte` en pixels (carrés de `taille` px). Renvoie la largeur occupée. Lettres inconnues : espace."""
    cur = x
    for ch in texte.upper():
        g = _GLYPHES.get(ch)
        if g:
            for j, rang in enumerate(g):
                for i, bit in enumerate(rang):
                    if bit == "1":
                        px, py = cur + i * taille, y + j * taille
                        if ombre:
                            c.create_rectangle(px + taille, py + taille, px + 2 * taille, py + 2 * taille, fill=ombre, outline="")
                        c.create_rectangle(px, py, px + taille, py + taille, fill=couleur, outline="")
        cur += 6 * taille
    return cur - x


def chemin_flamme():
    from forge.chemins import chemin_data
    return chemin_data("flamme.png")


def dessiner_bandeau_flamme(c, largeur: int, hauteur: int):
    """Plaque d'atelier sobre, inspirée du bandeau Forgemagie et marquée par le logo."""
    c.delete("all")
    # Une seule plaque mate, avec une patine verticale. Les anciens cadres
    # imbriqués créaient plusieurs filets noirs qui alourdissaient l'en-tête.
    for y, couleur in enumerate(T.degrade(T.TITRE, T.TITRE_FONCE, max(1, hauteur))):
        c.create_rectangle(0, y, largeur, y + 1, fill=couleur, outline=couleur)

    milieu = largeur // 2
    # Deux gravures d'atelier, en retrait dans la matière, encadrent le logo.
    gravure = T.TITRE
    for sens in (-1, 1):
        x = milieu + sens * 133
        c.create_line(x, 42, x + sens * 18, 32, x + sens * 34, 42,
                      x + sens * 48, 50, x + sens * 62, 42,
                      smooth=True, splinesteps=16, fill=gravure, width=2)

    try:
        import tkinter as tk
        c._flamme_source = tk.PhotoImage(file=str(chemin_flamme()), master=c)
        c._flamme = c._flamme_source.zoom(10, 10).subsample(11, 11)
        # La flammèche seule devient le sceau central du bandeau.
        x_flamme = max(0, (largeur - c._flamme.width()) // 2)
        y_flamme = max(0, (hauteur - c._flamme.height()) // 2)
        c.create_image(x_flamme, y_flamme, image=c._flamme, anchor="nw")
    except Exception:
        _noter_erreur("dessin.dessiner_bandeau_flamme")


def dessiner_onglets(c, largeur: int, libelles: Sequence[str], selection: int, survol: int = -1):
    """Navigation compacte inspirée des onglets de l'atelier Dofus, sans filets décoratifs."""
    c.delete("all")
    hauteur = max(34, int(c.winfo_height()))
    c.create_rectangle(0, 0, largeur, hauteur, fill=T.PANNEAU, outline="")
    if not libelles:
        return
    pas = largeur / len(libelles)
    if T.NOM == "kabhal":
        # (v170) boutons à bord métallique, onglet actif turquoise lumineux (images Pillow) ; repli : ancien dessin
        try:
            from forge.rendu_image import image_onglet, vers_photo
            c._images_onglets = []
            for i, libelle in enumerate(libelles):
                x0, x1 = int(i * pas), int((i + 1) * pas)
                etat = "actif" if i == selection else ("survol" if i == survol else "repos")
                photo = vers_photo(image_onglet(x1 - x0, hauteur, etat, T.PANNEAU), c)
                c._images_onglets.append(photo)
                c.create_image(x0, 0, image=photo, anchor="nw")
                couleur = "#f2fffd" if etat == "actif" else (T.OS if etat == "survol" else "#b4c0c3")
                police = (T.POLICE_TITRE, 10, "bold") if etat == "actif" else (T.POLICE_TITRE, 10)
                c.create_text((x0 + x1) // 2, hauteur // 2, text=libelle.upper(), fill=couleur,
                              font=police)
            c.create_line(0, hauteur - 1, largeur, hauteur - 1, fill="#474233")
            return
        except Exception:
            _noter_erreur("dessin.dessiner_onglets.image")
    for i, libelle in enumerate(libelles):
        x0, x1 = int(i * pas), int((i + 1) * pas)
        actif = i == selection
        if T.NOM == "kabhal" and (actif or i == survol):
            # (v166) Forge ténébreuse : lueur discrète et trait de feu d'âme sous l'onglet actif.
            c.create_rectangle(x0 + 2, 3, x1 - 2, hauteur - 2, fill=T.CARTE if actif else T.PANNEAU, outline="")
            if actif:
                c.create_rectangle(x0 + 6, hauteur - 4, x1 - 6, hauteur - 2, fill=T.ACCENT, outline="")
        elif actif or i == survol:
            # Petite plaque à coins coupés, comme une pièce d'interface de jeu.
            coupe = 4
            c.create_polygon(x0 + coupe, 3, x1 - coupe, 3, x1, 3 + coupe,
                             x1, hauteur - 2, x0, hauteur - 2, x0, 3 + coupe,
                             fill=T.TITRE_FONCE if actif else T.CARTE, outline="")
        xm, ym = (x0 + x1) // 2, hauteur // 2
        couleur = T.ACCENT_CLAIR if actif else (T.OS if i == survol else T.OS_DOUX)
        taille = 4 if actif else 3
        c.create_polygon(xm - 31, ym, xm - 31 + taille, ym - taille,
                         xm - 31 + 2 * taille, ym, xm - 31 + taille, ym + taille,
                         fill=T.ACCENT if actif else T.FILET, outline="")
        c.create_text(xm + 5, ym, text=libelle.upper(), fill=couleur,
                      font=(T.POLICE_TITRE, 9, "bold"))


def chemin_icone_stat(id_ligne: str):
    """Chemin vers une vraie icône de caractéristique DOFUS, si elle est disponible."""
    from pathlib import Path
    cle = (id_ligne or "").lower().replace("%", "")
    fichier = None
    if any(x in cle for x in ("vitalite", "vita")):
        fichier = "stat_vitalite.png"
    elif "force" in cle or cle == "fo":
        fichier = "stat_force.png"
    elif "sagesse" in cle or cle == "sa":
        fichier = "stat_sagesse.png"
    elif "crit" in cle and not any(x in cle for x in ("res_crit", "resistance_critique")):
        fichier = "stat_critique.png"
    elif "do_neutre" in cle or "dommage_neutre" in cle:
        fichier = "stat_dommage_neutre.png"
    elif "do_terre" in cle or "dommage_terre" in cle:
        fichier = "stat_dommage_terre.png"
    elif "res_eau" in cle or "resistance_eau" in cle:
        fichier = "stat_resistance_eau.png"
    elif "tacle" in cle:
        fichier = "stat_tacle.png"
    elif "retrait_pa" in cle or "ret_pa" in cle:
        fichier = "stat_retrait_pa.png"
    if not fichier:
        # Repli d'affichage uniquement : réutiliser la rune de la caractéristique.
        from forge.runes_jeu import chemin_icone, nom_rune
        speciales = {"arme_chasse": "Rune de chasse", "puissance_pieges": "Rune Per Pi"}
        return chemin_icone(speciales.get(cle) or nom_rune(cle, "simple"))
    from forge.chemins import chemin_data
    chemin = chemin_data("icones", fichier)
    return chemin if chemin.is_file() else None


def charger_icone_stat(chemin, master):
    """Préserver les petites icônes ; borner les runes à 24 pixels sans écrire d'image."""
    import tkinter as tk
    image = tk.PhotoImage(file=str(chemin), master=master)
    facteur = max(1, (max(image.width(), image.height()) + 23) // 24)
    return image.subsample(facteur, facteur) if facteur > 1 else image


def dessiner_bandeau_kabhal(c, largeur: int, hauteur: int):
    """(v166) Forge ténébreuse : fond noir froid, halo de feu d'âme derrière la flammèche, filet à losanges.

    La flammèche est affichée à sa taille d'origine (1 pixel = 1 pixel) pour rester nette, sans pixels déformés.
    (v170) D'abord l'image Pillow (flammèche sur une enclume, avec lueur) ; l'ancien dessin reste en repli.
    """
    c.delete("all")
    try:
        from forge.rendu_image import image_entete, vers_photo
        c._entete = vers_photo(image_entete(int(largeur), int(hauteur), str(chemin_flamme()), T.FOND), c)
        c.create_image(0, 0, image=c._entete, anchor="nw")
        return
    except Exception:
        _noter_erreur("dessin.dessiner_bandeau_kabhal.image")
    # Fond uni : le halo part exactement de cette couleur, donc il n'a pas de bord visible.
    c.create_rectangle(0, 0, largeur, hauteur, fill=T.FOND, outline="")
    milieu = largeur // 2
    centre_y = hauteur // 2 - 4
    # Halo doux : beaucoup d'ovales très proches, du fond vers un sarcelle sombre, avec une montée lente
    # (courbe au carré) pour que la lueur reste discrète sur les bords (tkinter n'a pas de transparence).
    pas = 28
    teintes = T.degrade(T.FOND, "#0a3a35", 64)
    for k in range(pas):
        t = k / (pas - 1)
        couleur = teintes[int((t ** 2) * 63)]
        rx = int(150 - t * 122)
        ry = int(48 - t * 30)
        c.create_oval(milieu - rx, centre_y - ry, milieu + rx, centre_y + ry, fill=couleur, outline="")
    # Filet du bas : deux traits acier et trois losanges, celui du centre en feu d'âme.
    y = hauteur - 3
    c.create_line(16, y, milieu - 22, y, fill=T.FILET)
    c.create_line(milieu + 22, y, largeur - 16, y, fill=T.FILET)
    for dx, plein in ((-12, False), (0, True), (12, False)):
        t = 4 if plein else 3
        c.create_polygon(milieu + dx - t, y, milieu + dx, y - t, milieu + dx + t, y, milieu + dx, y + t,
                         fill=T.ACCENT if plein else T.FOND, outline=T.ACCENT if plein else T.FILET)
    try:
        import tkinter as tk
        c._flamme = tk.PhotoImage(file=str(chemin_flamme()), master=c)
        x_flamme = max(0, (largeur - c._flamme.width()) // 2)
        y_flamme = max(0, (hauteur - 8 - c._flamme.height()) // 2)
        c.create_image(x_flamme, y_flamme, image=c._flamme, anchor="nw")
    except Exception:
        _noter_erreur("dessin.dessiner_bandeau_kabhal")


def dessiner_bandeau(c, largeur: int, hauteur: int = 58):
    """Dessine le bandeau supérieur selon le thème actif."""
    if T.NOM == "flamme":
        return dessiner_bandeau_flamme(c, largeur, hauteur)
    if T.NOM == "kabhal":
        return dessiner_bandeau_kabhal(c, largeur, hauteur)
    c.delete("all")
    if T.NOM == "brakmar":
        for i, col in enumerate(T.degrade(T.TITRE, T.FOND, max(1, largeur // 3))):
            c.create_rectangle(i * 3, 0, i * 3 + 3, hauteur, fill=col, outline=col)
        c.create_rectangle(0, hauteur - 3, largeur, hauteur - 1, fill=T.ACCENT, outline=T.ACCENT)
        c.create_rectangle(0, hauteur - 1, largeur, hauteur, fill=T.OR, outline=T.OR)
        x, y = 38, hauteur // 2 + 2
        for sens in (-1, 1):
            c.create_polygon(x + sens * 10, y - 8, x + sens * 30, y - 10, x + sens * 26, y - 26, x + sens * 16, y - 16,
                             x + sens * 6, y - 14, fill=T.OS, outline=T.ACCENT)
        c.create_oval(x - 14, y - 12, x + 14, y + 16, fill=T.OS, outline=T.ACCENT, width=2)
        c.create_oval(x - 9, y - 3, x - 2, y + 5, fill=T.TITRE_FONCE, outline="")
        c.create_oval(x + 2, y - 3, x + 9, y + 5, fill=T.TITRE_FONCE, outline="")
        c.create_polygon(x - 2, y + 6, x + 2, y + 6, x, y + 10, fill=T.TITRE_FONCE, outline="")
        c.create_text(78, 29, text="FORGEMAGIE", anchor="w", fill=T.OS, font=(T.POLICE_TITRE, 17, "bold"))
        return
    # thème « jeu » : dégradé turquoise -> ardoise, titre centré, arabesques de chaque côté
    for i, col in enumerate(T.degrade(T.TITRE, T.CARTE, hauteur)):
        c.create_rectangle(0, i, largeur, i + 1, fill=col, outline=col)
    milieu = largeur // 2
    c.create_text(milieu, 29, text="Forgemagie", fill=T.OS, font=(T.POLICE_TITRE, 15, "bold"))
    for sens, x0 in ((1, milieu + 110), (-1, milieu - 110)):
        for k, dy in enumerate((16, 24, 32)):
            x1 = x0 + sens * (150 - k * 25)
            c.create_line(x0, dy, x0 + sens * 40, dy - 6 + k * 3, x1, dy, smooth=True, fill=T.ACCENT, width=1)
        c.create_polygon(x0 + sens * 160, 20, x0 + sens * 172, 24, x0 + sens * 160, 28, fill=T.ACCENT)


def cadre_bronze_canvas(c, x0: int, y0: int, x1: int, y1: int, fond: str = ""):
    """Cadre bronze antique unifié pour Canvas (identique aux cartes Pillow : filet #7a6e51 + coins fins)."""
    c.create_rectangle(x0, y0, x1, y1, fill=fond, outline="#050809")
    c.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill="", outline="#7a6e51")
    c.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill="", outline="#151d1e")
    for rx, ry, sx, sy in ((x0 + 1, y0 + 1, 1, 1), (x1 - 1, y0 + 1, -1, 1),
                           (x0 + 1, y1 - 1, 1, -1), (x1 - 1, y1 - 1, -1, -1)):
        c.create_line(rx, ry, rx + sx * 7, ry, fill="#a89970", width=1)
        c.create_line(rx, ry, rx, ry + sy * 7, fill="#a89970", width=1)
        c.create_rectangle(rx + sx * 2, ry + sy * 2, rx + sx * 4, ry + sy * 4,
                           fill="#7a6e51", outline="#d5c592")


def dessiner_entete(c, largeur: int, reliquat: str, progres: str, rune: str, fait: int = 0, total: int = 0,
                    hauteur: int = 68):
    """Reliquat et prochaine rune dans une plaque sobre inspirée de l'interface de jeu."""
    c.delete("all")
    compact = (T.NOM == "kabhal" and hauteur <= 46)
    c.create_rectangle(0, 0, largeur, hauteur, fill="#0e1617" if compact else (T.PANNEAU if T.NOM == "kabhal" else T.CARTE), outline="")
    if compact:
        cadre_bronze_canvas(c, 0, 0, largeur - 1, hauteur - 1, fond="#0e1617")
        ym = (hauteur - 5) // 2
        c.create_text(14, ym, text="RELIQUAT", anchor="w", fill=T.OS_DOUX, font=(T.POLICE_TITRE, 8, "bold"))
        c.create_text(78, ym, text=reliquat, anchor="w", fill=T.OS, font=(T.POLICE_TITRE, 13, "bold"))
        texte_progres = f"{fait} / {total}" if total else (progres or "—")
        c.create_text(largeur - 14, ym, text=texte_progres, anchor="e", fill=T.ACCENT_CLAIR, font=(T.POLICE_TITRE, 12, "bold"))
        c.create_text(largeur - 64, ym, text="AU BUT", anchor="e", fill=T.OS_DOUX, font=(T.POLICE_TITRE, 8, "bold"))
        x0, x1 = 10, largeur - 10
        y0, y1 = hauteur - 8, hauteur - 4
        c.create_rectangle(x0 - 1, y0 - 1, x1 + 1, y1 + 1, fill="#080d0e", outline="#4c4738")
        if total > 0:
            fin = x0 + (x1 - x0) * max(0, min(fait, total)) / total
            c.create_rectangle(x0, y0, fin, y1, fill=T.ACCENT, outline="")
            if fin - x0 > 3:
                c.create_line(x0, y0, fin, y0, fill="#bafff4")
        return
    # (v166) thème kabhal : pas de plaque autour du reliquat et des lignes au but, juste le fond.
    c.create_text(16, 15, text="RELIQUAT", anchor="w", fill=T.OS_DOUX,
                  font=(T.POLICE_TITRE, 8, "bold"))
    c.create_text(16, 42, text=reliquat, anchor="w", fill=T.OS,
                  font=(T.POLICE_TITRE, 20, "bold"))
    c.create_text(largeur - 16, 15, text="LIGNES AU BUT", anchor="e", fill=T.OS_DOUX,
                  font=(T.POLICE_TITRE, 8, "bold"))
    texte_progres = f"{fait} / {total}" if total else (progres or "—")
    c.create_text(largeur - 16, 40, text=texte_progres, anchor="e",
                  fill=T.ACCENT_CLAIR, font=(T.POLICE_TITRE, 16, "bold"))
    x0, x1 = 16, largeur - 16
    y0, y1 = hauteur - 7, hauteur - 4
    c.create_rectangle(x0, y0, x1, y1, fill=T.LIGNE, outline="")
    if total > 0:
        fin = x0 + (x1 - x0) * max(0, min(fait, total)) / total
        c.create_rectangle(x0, y0, fin, y1, fill=T.ACCENT, outline="")


# Sous-ligne « chances SC / SN / EC » (case cochée) : échelle 70 % choisie par l'utilisateur le 06/11
# (maquettes 100 / 85 / 70 / 55 % dans developpement/captures_interface/echelles/).
HAUTEUR_SOUS = 34
TAILLE_ICONE_RUNE = 22
POLICE_VALEUR_RUNE = 7
POLICE_SIGLE_RUNE = 6


def hauteur_tableau(n: int, sous: int = 0) -> int:
    """Hauteur du tableau : `n` rangées, plus `sous` sous-lignes de chances (0 = tableau habituel)."""
    return HAUT_TABLEAU + max(1, n) * (HAUTEUR_RANGEE + ESPACE) + sous * (HAUTEUR_SOUS + ESPACE) + 4


def _image_rune(c, chemin: str):
    """Icône de rune (data/icones/, prise du jeu) mise à TAILLE_ICONE_RUNE px (lissée, comme la carte de la rune) ;
    repli : réduction entière de tkinter. None si absente ou illisible."""
    if not chemin:
        return None
    if not hasattr(c, "_icones_runes"):
        c._icones_runes = {}
    if chemin not in c._icones_runes:
        try:
            import base64
            import cv2
            import tkinter as tk
            src = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
            h, w = src.shape[:2]
            e = TAILLE_ICONE_RUNE / max(h, w)
            petit = cv2.resize(src, (max(1, round(w * e)), max(1, round(h * e))),
                               interpolation=cv2.INTER_AREA if e < 1 else cv2.INTER_LANCZOS4)
            ok, png = cv2.imencode(".png", petit)
            if ok:
                c._icones_runes[chemin] = tk.PhotoImage(data=base64.b64encode(png.tobytes()), master=c)
                return c._icones_runes[chemin]
        except Exception:
            pass
        try:
            import tkinter as tk
            image = tk.PhotoImage(file=chemin, master=c)
            cote = max(image.width(), image.height())
            facteur = max(1, (cote + TAILLE_ICONE_RUNE - 1) // TAILLE_ICONE_RUNE)
            c._icones_runes[chemin] = image.subsample(facteur, facteur) if facteur > 1 else image
        except Exception:
            c._icones_runes[chemin] = None
    return c._icones_runes[chemin]


def dessiner_tuile_rune(c, x0: int, x1: int, y0: int, rune: Dict):
    """Une rune : son icône, et à droite trois lignes « SC 22 % », « SN 55 % », « EC 22 % » en blanc sur fond sombre.
    Chiffres repris tels quels de forge.vue_chances (moteur) ; « inconnu » (gris) si le moteur ne sait pas."""
    from forge.vue_chances import texte_pourcent
    y1, ym = y0 + HAUTEUR_SOUS, y0 + HAUTEUR_SOUS // 2
    rect_arrondi(c, x0, y0, x1, y1, r=4, fill=T.FOND, outline="")
    xi = x0 + 4 + TAILLE_ICONE_RUNE // 2
    img = _image_rune(c, rune.get("icone", ""))
    if img is not None:
        c.create_image(xi, ym, image=img)
    else:  # pas d'icône : le nom court de la rune dans un petit cartouche
        pastille(c, xi - 12, ym - 8, xi + 12, ym + 8, rune.get("runes", "?"), T.CARTE, T.OS,
                 police=(T.POLICE, POLICE_SIGLE_RUNE, "bold"))
    xs, xv = x0 + 10 + TAILLE_ICONE_RUNE, x0 + 27 + TAILLE_ICONE_RUNE
    couleurs = {"SC": T.VERT, "SN": T.BLEU, "EC": T.ROUGE}  # écriture seulement : SC vert, SN bleu, EC rouge
    for (sigle, dy) in (("SC", -10), ("SN", 0), ("EC", 10)):
        v = rune.get(sigle)
        couleur = couleurs[sigle] if v is not None else T.OS_DOUX  # « inconnu » reste gris
        c.create_text(xs, ym + dy, text=sigle, anchor="w", fill=couleur, font=(T.POLICE, POLICE_SIGLE_RUNE, "bold"))
        c.create_text(xv, ym + dy, text=texte_pourcent(v), anchor="w", fill=couleur,
                      font=(T.POLICE, POLICE_VALEUR_RUNE, "bold"))


def dessiner_sous_chances(c, largeur: int, y0: int, runes: Sequence[Dict]):
    """Sous-ligne d'une ligne de l'objet : une tuile par rune, en colonnes Ba / Pa / Ra alignées d'une ligne à l'autre."""
    x_debut, x_fin = 24, largeur - 6
    pas = (x_fin - x_debut) / 3
    for i, rune in enumerate(list(runes)[:3]):
        x0 = int(x_debut + i * pas)
        x1 = int(x_debut + (i + 1) * pas) - 4
        dessiner_tuile_rune(c, x0, x1, y0, rune)


def dessiner_tableau(c, largeur: int, lignes: Sequence[Sequence[str]], details: Sequence[Dict],
                     badges: Optional[Dict[str, int]] = None, prochain: Optional[Dict] = None,
                     entetes: Sequence[str] = ("Cible", "État"), chances: Optional[Dict] = None):
    """Liste d'effets compacte, sur les rangées acier et la typo du jeu.
    `chances` (facultatif) : id de ligne -> runes de forge.vue_chances ; une sous-ligne d'icônes SC / SN / EC par ligne."""
    import tkinter as tk
    badges = badges or {}
    c.delete("all")
    y_suivant = HAUT_TABLEAU
    h_tot = hauteur_tableau(len(lignes), sum(1 for det in details if chances and chances.get(det.get("id"))))
    if T.NOM == "kabhal":
        try:
            cadre_bronze_canvas(c, 0, 0, largeur - 1, max(h_tot, 40) - 1, fond="#0c1213")
        except Exception:
            pass
    colonnes = (("Min", 34, "center"), ("Max", 76, "center"),
                ("Effets / Carac.", 118, "w"), (entetes[0], largeur - 150, "e"),
                (entetes[1], largeur - 138, "w"))
    for texte, x, ancre in colonnes:
        c.create_text(x, 12, text=texte, anchor=ancre, fill=T.OS_DOUX,
                      font=(T.POLICE, 8, "bold"))
    if T.NOM == "kabhal" and not lignes:
        c.create_text(largeur // 2, HAUT_TABLEAU + HAUTEUR_RANGEE // 2,
                      text="Aucune ligne lue pour l'instant",
                      fill=T.OS_DOUX, font=(T.POLICE, 9, "italic"))
    if not hasattr(c, "_icones_stats"):
        c._icones_stats = {}
    for i, (ligne, det) in enumerate(zip(lignes, details)):
        libelle, actuel, cible, etat = ligne[:4]
        y0 = y_suivant
        y_suivant = y0 + HAUTEUR_RANGEE + ESPACE
        runes_ligne = chances.get(det.get("id")) if chances else None
        if runes_ligne:
            try:
                dessiner_sous_chances(c, largeur, y_suivant, runes_ligne)
            except Exception:
                _noter_erreur("dessin.sous_chances")
            y_suivant += HAUTEUR_SOUS + ESPACE
        y1, ym = y0 + HAUTEUR_RANGEE, y0 + HAUTEUR_RANGEE // 2
        couleur = T.couleur_etat(etat)
        delta = badges.get(libelle)
        vise = bool(prochain) and det.get("id") and det.get("id") == prochain.get("id")
        if T.NOM == "kabhal":
            fond = "#17322d" if vise else ("#151e1f" if i % 2 == 0 else "#101718")
            bord = "#3d9789" if vise else "#1f2a2c"
            reflet = "#2c685f" if vise else "#202b2d"
        else:
            fond = T.SURVOL if vise else (T.LIGNE if i % 2 == 0 else T.LIGNE_PAIRE)
            bord = ""
            reflet = ""
        rect_arrondi(c, 6, y0, largeur - 6, y1, r=5, fill=fond, outline=bord)
        if T.NOM == "kabhal":
            c.create_line(11, y0 + 1, largeur - 11, y0 + 1, fill=reflet)
            c.create_line(11, y1 - 1, largeur - 11, y1 - 1, fill="#080c0d")
        if vise:
            c.create_rectangle(6, y0 + 5, 9, y1 - 5, fill=T.ACCENT, outline="")
        for valeur, x in ((det.get("mini"), 34), (det.get("maxi"), 76)):
            c.create_text(x, ym, text="-" if valeur is None else str(valeur),
                          fill=T.OS_DOUX, font=(T.POLICE, 9))
        icone_path = chemin_icone_stat(det.get("id", ""))
        dessinee = False
        if icone_path:
            try:
                cle = str(icone_path)
                if cle not in c._icones_stats:
                    c._icones_stats[cle] = charger_icone_stat(cle, c)
                c.create_image(104, ym, image=c._icones_stats[cle])
                dessinee = True
            except Exception:
                _noter_erreur("dessin.icone_stat")
        if not dessinee:
            c.create_oval(99, ym - 5, 109, ym + 5, fill=T.couleur_icone(det.get("id", "")), outline="")
        courant_id = c.create_text(118, ym, text=actuel, anchor="w", fill=couleur,
                                   font=(T.POLICE, 10, "bold"))
        bbox = c.bbox(courant_id)
        x_libelle = (bbox[2] + 6) if bbox else (118 + 8 * len(actuel))
        c.create_text(x_libelle, ym, text=libelle, anchor="w", fill=couleur, font=(T.POLICE, 10))
        c.create_text(largeur - 150, ym, text="" if cible in ("", None) else cible,
                      anchor="e", fill=T.OS_DOUX, font=(T.POLICE, 9))
        c.create_text(largeur - 138, ym, text=etat, anchor="w", fill=couleur,
                      font=(T.POLICE, 9, "bold"))
        if delta:
            pastille(c, largeur - 226, ym - 9, largeur - 184, ym + 9, f"{delta:+d}",
                     T.VERT if delta > 0 else T.ROUGE, T.FOND)
        if vise:
            fond_p = "#1b463f" if T.NOM == "kabhal" else T.BOUTON_OR
            bord_p = "#54c8b5" if T.NOM == "kabhal" else ""
            txt_p = "#e8fffc" if T.NOM == "kabhal" else T.TEXTE_BOUTON_OR
            rect_arrondi(c, largeur - 228, ym - 12, largeur - 180, ym + 12, r=4,
                         fill=fond_p, outline=bord_p)
            if T.NOM == "kabhal":
                c.create_line(largeur - 224, ym - 10, largeur - 184, ym - 10, fill="#8ff7e6")
            c.create_text(largeur - 204, ym, text=f"+{prochain.get('montant', '')}",
                          fill=txt_p, font=(T.POLICE_TITRE, 12, "bold"))
    if T.NOM == "kabhal":
        # (v172) Cadre bronze vieilli unifié autour du tableau complet (même sans lignes)
        try:
            cadre_bronze_canvas(c, 0, 0, largeur - 1, max(y_suivant + 1, h_tot - 1))
        except Exception:
            _noter_erreur("dessin.cadre_tableau")
