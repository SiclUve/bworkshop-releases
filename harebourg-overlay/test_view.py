"""Tests de l'overlay sans écran. Lancer : python test_view.py [aperçu.png]

Avec un nom de fichier, écrit aussi un aperçu de ce que l'overlay dessinerait.
"""
import random
import sys

import core
import view


def bold_font(size):
    """Police grasse disponible sur Linux, Windows ou Mac."""
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                 "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_state(**kw):
    cal = core.Calib.default_for(1920, 1080)
    s = view.State(calib=cal, screen_w=1920, you=(18, 4), hp_manual=95.0, hits=0)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def at(s, cell):
    s.mouse = s.calib.center(cell)
    return s


def test_scene():
    # 95 % = 90° horaire : viser (18,-2) depuis (18,4) fait atterrir en (12,4) (cas relevé sur le simulateur)
    s = at(make_state(), (18, -2))
    prims, info = view.scene(s)
    assert info["k"] == 1 and info["source"] == "pv"
    assert info["aim"] == (18, -2) and info["landing"] == (12, 4), info
    assert info["warnings"] == []

    # Sans position, ou souris hors de la salle : pas de case d'atterrissage
    assert view.scene(at(make_state(you=None), (18, -2)))[1]["landing"] is None
    s = make_state()
    s.mouse = (5, 5)
    assert view.scene(s)[1]["aim"] is None

    # Mur visé, sort hors de la carte : avertissements
    s = at(make_state(hp_manual=60.0), (22, -2))        # 180°, bloc en 22,-2
    assert any("mur" in w.lower() for w in view.scene(s)[1]["warnings"])
    s = at(make_state(you=(2, 0), hp_manual=60.0), (6, 2))
    assert view.scene(s)[1]["landing"] == (-2, -2)
    s = at(make_state(you=(1, 1), hp_manual=60.0), (10, 4))
    assert any("hors de la carte" in w for w in view.scene(s)[1]["warnings"])

    # Grille affichée : toutes les cases + obstacles ; aucune trace du Comte
    prims, _ = view.scene(make_state(show_grid=True))
    assert sum(1 for p in prims if p[0] == "poly") >= len(core.ARENA)
    assert not any("COMTE" in str(p) or "CLIQUE" in str(p) for p in prims)
    print("OK : scène de l'overlay")


def test_rotation_sources():
    s = make_state(hp_manual=100.0)
    assert s.rotation() == (1, "pv")
    s.hits = 1
    assert s.rotation() == (0, "pv")             # chaque ligne au corps à corps : -90°
    s.hits = 0
    s.k_choice = 3
    assert s.rotation() == (3, "choisie")        # la confusion choisie prime sur les PV
    s.hits = 1
    assert s.rotation() == (2, "choisie")
    s.k_choice = 0
    assert s.rotation() == (3, "choisie")        # « aucune rotation » choisie + 1 ligne = 90° anti-horaire
    s.no_confusion = True
    assert s.rotation() == (0, "invocation")     # invocation : aucune confusion
    assert view.scene(s)[1]["source"] == "invocation"
    print("OK : sources de rotation (choisie / PV / invocation)")


def test_dial():
    # Au repos (souris hors de la salle) : le repère reste en haut, l'aiguille montre seulement la rotation
    info = view.dial_info(make_state())                    # 95 % : 90° horaire
    assert not info["live"] and info["aim_angle"] == 0 and info["needle_angle"] == 90

    # Visée à gauche de toi : le sort part vers le haut (90° horaire), comme sur le simulateur (18,-2 -> 12,4)
    info = view.dial_info(at(make_state(), (18, -2)))
    assert info["live"] and abs(info["aim_angle"] - 270) < 1e-9 and abs(info["needle_angle"] % 360) < 1e-9, info
    assert info["ok"]
    # Visée sur ta propre case ou sur un mur : pas de visée, ou alerte
    assert not view.dial_info(at(make_state(), (18, 4)))["live"]
    assert not view.dial_info(at(make_state(hp_manual=60.0), (22, -2)))["ok"]
    assert not view.dial_info(make_state(you=None))["live"]

    # L'aiguille pointe exactement vers la vraie case d'atterrissage, pour toutes les rotations
    random.seed(3)
    cells = sorted(core.ARENA)
    for _ in range(400):
        you, aim = random.choice(cells), random.choice(cells)
        for k in range(4):
            s = at(make_state(you=you, k_choice=k), aim)
            land = core.landing_cell(you, aim, k)
            if aim == you or land == you:
                continue
            want = view.cell_angle(you, land)
            got = view.dial_info(s)["needle_angle"]
            assert abs((want - got + 180) % 360 - 180) < 1e-6, (you, aim, k, want, got)
    print("OK : cadran (aiguille = direction d'atterrissage)")


def test_free_grid():
    """Mode Songes : une grande grille sur tout l'écran, sans carte, qui ne change pas."""
    free = len(core.FIGHTS) - 1
    cal = core.Calib(800.0, 300.0, 44.0, 22.0)
    rect = (0, 0, 1920, 1080)
    lines = view.free_grid_prims(cal, rect)
    assert 60 < len(lines) < 200 and all(p[0] == "line" for p in lines)

    def dist(pt, p, q):                                             # distance d'un point à la droite (p, q)
        (x, y), (x1, y1), (x2, y2) = pt, p, q
        return abs((y2 - y1) * (x - x1) - (x2 - x1) * (y - y1)) / ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    # chaque côté de case visible, y compris loin hors de la salle du Comte, est sur une des droites tracées
    for cell in [(a, b) for a in range(-6, 46, 5) for b in range(-20, 20, 4) if (a + b) % 2 == 0]:
        poly = cal.polygon(cell)
        if not all(0 <= x <= 1920 and 0 <= y <= 1080 for x, y in poly):
            continue
        for i in range(4):
            p, q = poly[i], poly[(i + 1) % 4]
            assert any(dist(p, a, b) < 1e-6 and dist(q, a, b) < 1e-6 for _, a, b, *_ in lines), (cell, i)
    # et il n'y a pas de droite inutile : toutes traversent l'écran, à une demi-case de marge près
    for _, a, b, *_ in lines:
        assert max(a[1], b[1]) >= -cal.ky - 1e-6 and min(a[1], b[1]) <= 1080 + cal.ky + 1e-6
        assert a[0] <= 0 and b[0] >= 1920                             # et elles couvrent toute la largeur

    # la scène : grille toujours là (même sans « Grille »), aucun bloc ni trou, aucune alerte de carte
    s = make_state(fight=free, show_grid=False, you=(18, 4))
    s.origin, s.screen_h = (0, 0), 1080
    prims, info = view.scene(at(s, (40, 20)))
    assert sum(1 for p in prims if p[0] == "line" and p[3] == view.GRID_FREE) > 60
    assert not any(p[0] == "poly" and p[2] in (view.BLOCK_FILL, view.PIT_FILL) for p in prims)
    assert info["aim"] == (40, 20) and info["landing"] is not None and info["warnings"] == []
    s.flash = True                                                  # le contour de la salle du Comte n'a pas de sens ici
    assert not any(p[0] == "line" and p[3] == view.OUTLINE for p in view.scene(s)[0])
    assert view.dial_info(at(s, (40, 20)))["live"]
    # dans la salle du Comte, la même case lointaine n'est pas ciblable
    assert view.scene(at(make_state(fight=0, you=(18, 4)), (40, 20)))[1]["aim"] is None
    # la grille ne bouge pas : mêmes droites tant que la calibration est la même
    assert view.free_grid_prims(cal, rect) == lines
    print("OK : grande grille du mode Songes (tout l'écran, bonnes droites, sans carte)")


def render_preview(prims, path, size=(1920, 1080)):
    from PIL import Image, ImageDraw, ImageFont
    bg = Image.new("RGBA", size, (58, 74, 52, 255))
    d0 = ImageDraw.Draw(bg)
    for y in range(size[1]):
        shade = int(40 * y / size[1])
        d0.line([(0, y), (size[0], y)], fill=(58 - shade // 2, 74 - shade // 2, 52 + shade // 3, 255))
    over = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over, "RGBA")
    font = lambda n: bold_font(int(n * 1.15))
    for p in prims:
        if p[0] == "poly":
            _, pts, fill, stroke, w, _dash = p
            d.polygon(pts, fill=fill)
            if stroke:
                d.line(pts + [pts[0]], fill=stroke, width=max(1, int(w)))
        elif p[0] == "line":
            _, a, b, col, w, _dash = p
            d.line([a, b], fill=col, width=max(1, int(w)))
        elif p[0] == "text":
            _, x, y, txt, col, size_, bgc = p
            f = font(size_)
            l, t, r, b = d.textbbox((0, 0), txt, font=f)
            if bgc:
                d.rounded_rectangle((x - (r - l) / 2 - 6, y - (b - t) / 2 - 4, x + (r - l) / 2 + 6, y + (b - t) / 2 + 6), 4, fill=bgc)
            d.text((x - (r - l) / 2 - l, y - (b - t) / 2 - t), txt, font=f, fill=col)
        elif p[0] == "panel":
            _, x, y, lines = p
            f = font(13)
            widths = [d.textbbox((0, 0), t, font=f)[2] for t, _ in lines]
            w = max(widths) + 24
            h = 24 * len(lines) + 12
            d.rounded_rectangle((x - w / 2, y, x + w / 2, y + h), 8, fill=view.LABEL_BG)
            for i, (t, col) in enumerate(lines):
                d.text((x - w / 2 + 12, y + 8 + 24 * i), t, font=f, fill=col)
    Image.alpha_composite(bg, over).convert("RGB").save(path)


if __name__ == "__main__":
    test_scene()
    test_rotation_sources()
    test_dial()
    test_free_grid()
    if len(sys.argv) > 1:
        s = make_state(show_grid=True)
        s = at(s, (14, 8))
        render_preview(view.scene(s)[0], sys.argv[1])
        print("Aperçu écrit :", sys.argv[1])
