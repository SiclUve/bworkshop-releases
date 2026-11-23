"""(v170-v172) Images de l'interface dessinées avec Pillow : en-tête illustré (flammèche sur enclume gravée),
onglets à bord métallique, boutons/champs 9-slice et cadres ornés style bronze antique.

Tkinter ne sait pas faire de transparence, de dégradés ni d'ornements fins : ces effets sont calculés ici,
puis affichés comme des images. Purement visuel : aucune lecture du jeu, aucun fichier écrit. En cas d'échec,
l'appelant garde l'ancien dessin (repli).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter

TURQUOISE = (70, 226, 208)
BRONZE_CLAIR = (146, 134, 100, 255)
BRONZE_MOYEN = (104, 96, 72, 255)
BRONZE_SOMBRE = (54, 51, 40, 255)
CONTOUR_NOIR = (5, 8, 9, 255)


def _rgb(c: str) -> Tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _degrade_vertical(largeur: int, hauteur: int, haut, bas) -> Image.Image:
    """Image RGBA d'un dégradé vertical de `haut` à `bas` (couleurs RGB ou RGBA)."""
    largeur, hauteur = max(1, int(largeur)), max(1, int(hauteur))
    img = Image.new("RGBA", (largeur, hauteur))
    d = ImageDraw.Draw(img)
    alpha_h = haut[3] if len(haut) > 3 else 255
    alpha_b = bas[3] if len(bas) > 3 else 255
    for y in range(hauteur):
        t = y / max(1, hauteur - 1)
        c = tuple(round(haut[k] + (bas[k] - haut[k]) * t) for k in range(3)) + (round(alpha_h + (alpha_b - alpha_h) * t),)
        d.line([(0, y), (largeur - 1, y)], fill=c)
    return img


def _masque_arrondi(largeur: int, hauteur: int, rayon: int, retrait: int = 0) -> Image.Image:
    m = Image.new("L", (largeur, hauteur), 0)
    ImageDraw.Draw(m).rounded_rectangle([retrait, retrait, largeur - 1 - retrait, hauteur - 1 - retrait],
                                        radius=max(0, rayon - retrait), fill=255)
    return m


def _ajouter_grain(img: Image.Image, amplitude: int = 3) -> Image.Image:
    """Micro-texture déterministe très discrète pour éviter l'effet plastique uni."""
    w, h = img.size
    if w <= 0 or h <= 0:
        return img
    # motif 8x8 léger répété (rapide, aucun module externe)
    motif = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    px = motif.load()
    for y in range(8):
        for x in range(8):
            v = ((x * 37 + y * 53) % 11) - 5
            if v > 0:
                px[x, y] = (255, 255, 255, min(255, v * amplitude))
            elif v < 0:
                px[x, y] = (0, 0, 0, min(255, (-v) * amplitude))
    tuile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            tuile.paste(motif, (tx, ty))
    return Image.alpha_composite(img.convert("RGBA"), tuile)


def _ornements_coins(d: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, taille: int = 7):
    """Équerres fines et rivets bronze vieilli aux 4 coins (alignés avec les cadres Canvas)."""
    t = max(5, taille)
    for cx, sx in ((x0, 1), (x1, -1)):
        for cy, sy in ((y0, 1), (y1, -1)):
            d.line([(cx, cy + sy * t), (cx, cy), (cx + sx * t, cy)], fill=(168, 153, 112, 255), width=1)
            rx, ry = cx + sx * 3, cy + sy * 3
            d.rectangle([rx - 1, ry - 1, rx + 1, ry + 1], fill=(122, 110, 81, 255))
            d.point((rx, ry), fill=(213, 197, 146, 255))


def _dessiner_cadre_bronze(img: Image.Image, coins: bool = True, taille_coin: int = 7):
    """Cadre bronze antique unifié : filet extérieur sombre, bord bronze #7a6e51, rainure sombre, coins fins."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=CONTOUR_NOIR)
    d.rectangle([1, 1, w - 2, h - 2], outline=(122, 110, 81, 255))
    d.rectangle([2, 2, w - 3, h - 3], outline=(21, 29, 30, 255))
    if coins and w > 30 and h > 30:
        _ornements_coins(d, 1, 1, w - 2, h - 2, taille=taille_coin)


def _chemin_entete_illustree(chemin_flamme: str) -> Path:
    return Path(chemin_flamme).resolve().parent / "entete_kabhal.png"


@lru_cache(maxsize=8)
def image_entete(largeur: int, hauteur: int, chemin_flamme: str, fond: str = "#06090a") -> Image.Image:
    """En-tête : illustration sombre (flammèche + enclume gravée) fondue sans couture dans un halo sarcelle."""
    largeur, hauteur = max(120, int(largeur)), max(60, int(hauteur))
    img = _degrade_vertical(largeur, hauteur, (11, 17, 18), (9, 14, 15))

    # Lueur atmosphérique centrée (proportionnelle à la hauteur)
    cx = largeur // 2
    cy = hauteur // 2
    lueur = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lueur)
    dl.ellipse([cx - 170, -hauteur // 4, cx + 170, hauteur + hauteur // 4], fill=(22, 92, 86, 48))
    dl.ellipse([cx - 85, max(2, cy - hauteur // 3), cx + 85, min(hauteur - 2, cy + hauteur // 3)],
               fill=TURQUOISE + (38,))
    img = Image.alpha_composite(img, lueur.filter(ImageFilter.GaussianBlur(max(12, hauteur // 4))))

    src_path = _chemin_entete_illustree(chemin_flamme)
    if src_path.is_file():
        art = Image.open(src_path).convert("RGBA")
        # Recadrage de la brume périphérique vide avant mise à l'échelle
        art = art.crop((round(art.width * 0.08), round(art.height * 0.04),
                        round(art.width * 0.92), round(art.height * 0.97)))
        cible_h = max(40, hauteur - 6)
        cible_w = round(art.width * (cible_h / art.height))
        art = art.resize((cible_w, cible_h), Image.LANCZOS)
        # Fondu elliptique 2D + effacement doux des zones sombres périphériques : aucune trace de rectangle
        masque = Image.new("L", (cible_w, cible_h), 0)
        mpx = masque.load()
        apx = art.load()
        cx_a, cy_a = cible_w / 2.0, cible_h / 2.0
        rx_a, ry_a = max(1.0, cible_w / 2.0), max(1.0, cible_h / 2.0)
        for y in range(cible_h):
            dy = abs(y - cy_a) / ry_a
            for x in range(cible_w):
                dx = abs(x - cx_a) / rx_a
                d = (dx * dx * 0.95 + dy * dy * 1.05) ** 0.5
                if d <= 0.42:
                    f_geo = 1.0
                elif d >= 0.96:
                    f_geo = 0.0
                else:
                    t = (d - 0.42) / (0.96 - 0.42)
                    f_geo = (1.0 - t * t * (3.0 - 2.0 * t)) ** 1.35
                r, g, b, a = apx[x, y]
                lum = max(r, g, b)
                if lum < 30 and d > 0.30:
                    f_lum = max(0.0, (lum - 14) / 16.0)
                    mult = min(f_geo, max(0.0, f_geo * (0.35 + 0.65 * f_lum)))
                else:
                    mult = f_geo
                mpx[x, y] = max(0, min(255, round(a * mult)))
        art.putalpha(masque)
        img.alpha_composite(art, ((largeur - cible_w) // 2, (hauteur - cible_h) // 2))
    else:
        # Repli simple avec la flammèche pixel art si l'illustration est absente
        flamme = Image.open(chemin_flamme).convert("RGBA")
        flamme = flamme.resize((round(flamme.width * 1.15), round(flamme.height * 1.15)), Image.LANCZOS)
        fx, fy = cx - flamme.width // 2, max(4, (hauteur - flamme.height) // 2)
        img.alpha_composite(flamme, (fx, fy))

    _dessiner_cadre_bronze(img, coins=True, taille_coin=7)
    return img.convert("RGB")


@lru_cache(maxsize=64)
def image_onglet(largeur: int, hauteur: int, etat: str, fond: str = "#0a0f10") -> Image.Image:
    """Bouton d'onglet biseauté : etat = « actif » (turquoise lumineux), « survol » ou « repos » (acier antique)."""
    marge = 3
    largeur, hauteur = max(largeur, 24), max(hauteur, 20)
    img = _degrade_vertical(largeur, hauteur, (14, 21, 22), (8, 12, 13))
    w, h = largeur - 2 * marge, hauteur - 2 * marge
    rayon = 5
    if etat == "actif":
        halo = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
        ImageDraw.Draw(halo).rounded_rectangle([marge, marge, largeur - marge, hauteur - marge], radius=rayon,
                                               fill=TURQUOISE + (175,))
        img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(3.5)))
        bord = _degrade_vertical(w, h, (175, 253, 244), (40, 165, 150))
        dedans = _degrade_vertical(w, h, (42, 152, 138), (13, 72, 66))
    else:
        bord = _degrade_vertical(w, h, (132, 124, 98), (58, 56, 48))
        if etat == "survol":
            dedans = _degrade_vertical(w, h, (56, 68, 70), (28, 35, 37))
        else:
            dedans = _degrade_vertical(w, h, (42, 50, 52), (20, 25, 27))
    piece = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    piece.paste(bord, (0, 0), _masque_arrondi(w, h, rayon))
    piece.paste(dedans, (0, 0), _masque_arrondi(w, h, rayon, retrait=2))
    dp = ImageDraw.Draw(piece)
    # reflet métallique sur l'arête supérieure intérieure
    dp.line([(4, 2), (w - 5, 2)], fill=(210, 255, 248, 95) if etat == "actif" else (195, 200, 190, 55))
    dp.rounded_rectangle([0, 0, w - 1, h - 1], radius=rayon, outline=CONTOUR_NOIR)
    img.alpha_composite(piece, (marge, marge))
    return img.convert("RGB")


@lru_cache(maxsize=16)
def image_bouton_9patch(etat: str = "repos", variante: str = "normal") -> Image.Image:
    """Image 32x32 extensible (9-slice) pour boutons métalliques biseautés."""
    w, h = 32, 32
    rayon = 5
    if variante == "accent":
        if etat == "survol":
            bord = _degrade_vertical(w, h, (148, 250, 238), (44, 175, 158))
            dedans = _degrade_vertical(w, h, (34, 134, 122), (16, 78, 71))
        elif etat == "presse":
            bord = _degrade_vertical(w, h, (40, 145, 132), (80, 210, 195))
            dedans = _degrade_vertical(w, h, (12, 60, 55), (24, 102, 93))
        else:
            bord = _degrade_vertical(w, h, (95, 235, 218), (32, 132, 120))
            dedans = _degrade_vertical(w, h, (25, 104, 95), (12, 60, 55))
    elif variante == "quiet":
        if etat == "survol":
            bord = _degrade_vertical(w, h, (130, 122, 96), (62, 60, 52))
            dedans = _degrade_vertical(w, h, (36, 46, 48), (20, 27, 29))
        elif etat == "presse":
            bord = _degrade_vertical(w, h, (56, 54, 46), (110, 104, 84))
            dedans = _degrade_vertical(w, h, (16, 22, 23), (28, 36, 38))
        else:
            bord = _degrade_vertical(w, h, (102, 96, 76), (48, 46, 40))
            dedans = _degrade_vertical(w, h, (26, 34, 36), (16, 22, 23))
    else:
        if etat == "survol":
            bord = _degrade_vertical(w, h, (152, 142, 110), (70, 68, 58))
            dedans = _degrade_vertical(w, h, (48, 60, 62), (26, 33, 35))
        elif etat == "presse":
            bord = _degrade_vertical(w, h, (60, 58, 50), (120, 112, 88))
            dedans = _degrade_vertical(w, h, (20, 26, 28), (34, 44, 46))
        else:
            bord = _degrade_vertical(w, h, (128, 118, 92), (56, 54, 46))
            dedans = _degrade_vertical(w, h, (38, 48, 50), (21, 27, 29))

    img = Image.new("RGBA", (w, h), _rgb("#0a0f10") + (255,))
    piece = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    piece.paste(bord, (0, 0), _masque_arrondi(w, h, rayon))
    piece.paste(dedans, (0, 0), _masque_arrondi(w, h, rayon, retrait=2))
    dp = ImageDraw.Draw(piece)
    dp.line([(4, 2), (w - 5, 2)], fill=(230, 248, 244, 70))
    dp.rounded_rectangle([0, 0, w - 1, h - 1], radius=rayon, outline=CONTOUR_NOIR)
    img.alpha_composite(piece, (0, 0))
    return img.convert("RGB")


@lru_cache(maxsize=4)
def image_champ_9patch(focus: bool = False) -> Image.Image:
    """Image 24x24 extensible (9-slice) pour champs de saisie encastrés."""
    w, h = 24, 24
    img = Image.new("RGBA", (w, h), (10, 15, 16, 255))
    d = ImageDraw.Draw(img)
    bord = (70, 226, 208, 255) if focus else (74, 76, 66, 255)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=3, fill=(9, 14, 15, 255), outline=bord)
    d.line([(2, 1), (w - 3, 1)], fill=(4, 7, 8, 255))
    d.line([(2, h - 2), (w - 3, h - 2)], fill=(38, 48, 49, 255))
    return img.convert("RGB")


@lru_cache(maxsize=16)
def image_cadre_carte(largeur: int, hauteur: int, fond: str = "#111a1b") -> Image.Image:
    """Fond de carte orné : dégradé sombre texturé + double bordure bronze antique + équerres de coin."""
    largeur, hauteur = max(40, int(largeur)), max(40, int(hauteur))
    f = _rgb(fond)
    img = _degrade_vertical(largeur, hauteur, tuple(min(255, v + 5) for v in f), tuple(max(0, v - 3) for v in f))
    img = _ajouter_grain(img, amplitude=2)
    # léger halo turquoise discret en haut à gauche autour de la case d'icône
    lueur = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    ImageDraw.Draw(lueur).ellipse([-10, 10, 120, 120], fill=TURQUOISE + (18,))
    img = Image.alpha_composite(img, lueur.filter(ImageFilter.GaussianBlur(18)))
    _dessiner_cadre_bronze(img, coins=True, taille_coin=7)
    return img.convert("RGB")


def vers_photo(image: Image.Image, master):
    """Image Pillow -> tk.PhotoImage (sans ImageTk, comme le reste du programme)."""
    import base64
    import io
    import tkinter as tk
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(tampon.getvalue()), master=master)
