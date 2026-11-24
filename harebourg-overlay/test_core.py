"""Tests de la logique. Lancer : python test_core.py"""
import itertools
from core import *


def main():
    # Carte : 292 cases, parité respectée, obstacles tous dans la salle
    assert len(ARENA) == 292, len(ARENA)
    assert all((a + b) % 2 == 0 for a, b in ARENA)
    for f in FIGHTS:
        # (7, 13) est dans les données du simulateur pour Klime mais hors de la salle : on le garde tel quel
        assert f.blocks - ARENA <= {(7, 13)} and f.pits <= ARENA, f.name
        assert not (f.blocks & f.pits), f.name
    assert [len(f.blocks) for f in FIGHTS] == [18, 11, 17, 18, 0], [len(f.blocks) for f in FIGHTS]

    # Tranches : chaque pourcentage entier a une tranche, aux bonnes bornes
    assert [tranche_of(p).base for p in (100, 90, 89, 75, 74, 45, 44, 30, 29, 0)] == [1, 1, -1, -1, 2, 2, -1, -1, 1, 1]
    assert tranche_of(74.9).base == 2 and tranche_of(75.0).base == -1

    # Cas relevé sur le simulateur : tranche 90-100, 0 coup, toi 18,4, monstre 12,4 -> taper 18,-2
    assert quarter_turns(95, 0) == 1
    assert tap_cell((18, 4), (12, 4), 1) == (18, -2), tap_cell((18, 4), (12, 4), 1)
    # Autres cas relevés sur le simulateur (même positions) : tranche 75-89 sans coup, et tranche 0-29 avec 2 coups
    assert tap_cell((18, 4), (12, 4), quarter_turns(80, 0)) == (18, 10)
    assert tap_cell((18, 4), (12, 4), quarter_turns(10, 2)) == (18, 10)
    # 180° avec ces positions : le simulateur annonce une case hors de la carte
    assert tap_cell((18, 4), (12, 4), quarter_turns(60, 0)) not in ARENA

    # Cliquer la case calculée fait toujours atterrir sur le monstre (toutes tranches, 0 à 8 coups)
    cells = sorted(ARENA)
    you, mon = (18, 4), (12, 4)
    for pct, hits in itertools.product((95, 80, 60, 35, 10), range(9)):
        k = quarter_turns(pct, hits)
        assert landing_cell(you, tap_cell(you, mon, k), k) == mon
    for y, m in itertools.islice(itertools.product(cells[::7], cells[::11]), 400):
        for k in range(4):
            assert landing_cell(y, tap_cell(y, m, k), k) == m

    # 180° : le sort atterrit à l'opposé exact de la case visée, par rapport à toi
    y, aim = (10, 0), (10, 4)
    assert landing_cell(y, aim, 2) == (10, -4)

    # Chaque coup au corps à corps retire un quart de tour
    assert quarter_turns(95, 1) == 0 and quarter_turns(95, 2) == 3 and quarter_turns(60, 2) == 0

    # Ligne de vue : un bloc 1x1 entre deux cases coupe, ses extrémités ne comptent pas
    f = FIGHTS[0]
    assert not has_los(f, (22, -6), (22, 2))          # le bloc 22,-2 est sur le chemin
    assert has_los(f, (22, -2), (22, 2))              # on part du bloc lui-même
    assert has_los(f, (18, 0), (18, 6))               # rien à cet endroit

    # Calibration : aller-retour cellule -> pixel -> cellule
    cal = Calib.default_for(1920, 1080)
    for c in cells[::5]:
        x, y2 = cal.center(c)
        assert cal.cell_at(x, y2) == c
        # un point proche du centre reste dans la même case
        assert cal.cell_at(x + cal.kx * 0.4, y2) == c
    assert cal.cell_at(-50, -50) is None

    # Calibration en 2 clics : retrouver une grille connue à partir des centres des deux pointes
    ref = Calib(937.92, 276.02, 44.05, 22.025)
    got = Calib.from_anchors(ref.center(CAL_TOP), ref.center(CAL_BOTTOM))
    assert all(abs(u - v) < 1e-6 for u, v in zip((got.x0, got.y0, got.kx, got.ky), (ref.x0, ref.y0, ref.kx, ref.ky))), got
    assert CAL_TOP in ARENA and CAL_BOTTOM in ARENA
    assert Calib.from_anchors((900, 800), (900, 300)) is None      # clics inversés : refusé

    # Ligne de confusion copiée / collée
    cases = {
        "Confusion horaire : 2 Pi/4": 1, "Confusion horaire : 4 Pi/4": 2,
        "Confusion horaire : 6 Pi/4": 3, "Confusion horaire : Pi/4": None,
        "Confusion contre horaire : 2 Pi/4": 3, "Confusion anti horaire : 2 Pi/4": 3,
        "Confusion horaire : 8 Pi/4": 0, "[21:04] Confusion contre horaire : 6 Pi/4": 1,
        "": None, "bla bla": None, "contre horaire : 6 Pi/4": None,   # strict : il faut « Confusion »
    }
    for txt, want in cases.items():
        assert parse_confusion(txt) == want, (txt, parse_confusion(txt), want)
    assert parse_confusion("contre horaire : 6 Pi/4", strict=False) == 1
    assert parse_confusion("horaire 2 pi/4", strict=False) == 1
    two_lines = "Confusion horaire : 2 Pi/4" + chr(10) + "Confusion contre horaire : 2 Pi/4"
    assert parse_confusion(two_lines) == 3                         # la dernière ligne l'emporte
    # le menu propose chaque rotation une fois, plus « d'après les PV »
    assert sorted(k for k, _ in CONF_CHOICES if k is not None) == [0, 1, 2, 3] and CONF_CHOICES[0][0] is None

    # Relevé sur le simulateur en ligne (Comte seul) : case « Hit here » pour chaque tranche (95, 82, 60, 37, 14 %)
    # et 0 à 3 lignes au corps à corps ; « - » = hors de la carte. Positions du screen de combat réel.
    sim = [
        ((18, -2), (10, 2), True, "14,-10 10,2 22,6 - 22,6 - 14,-10 10,2 - 14,-10 10,2 22,6 22,6 - 14,-10 10,2 14,-10 10,2 22,6 -"),
        ((18, -2), (16, -6), False, "22,-4 16,-6 14,0 20,2 14,0 20,2 22,-4 16,-6 20,2 22,-4 16,-6 14,0 14,0 20,2 22,-4 16,-6 22,-4 16,-6 14,0 20,2"),
        ((18, -2), (10, -8), False, "- 10,-8 12,6 - 12,6 - - 10,-8 - - 10,-8 12,6 12,6 - - 10,-8 - 10,-8 12,6 -"),
        ((14, -4), (24, 0), False, "10,6 24,0 - 4,-8 - 4,-8 10,6 24,0 4,-8 10,6 24,0 - - 4,-8 10,6 24,0 10,6 24,0 - 4,-8"),
    ]
    for you, mon, blocked, taps in sim:
        assert has_los(FIGHTS[0], you, mon) != blocked, (you, mon)
        for i, t in enumerate(taps.split()):
            pct, hits = (95, 82, 60, 37, 14)[i // 4], i % 4
            got = tap_cell(you, mon, quarter_turns(pct, hits))
            want = None if t == "-" else tuple(map(int, t.split(",")))
            assert (got if got in ARENA else None) == want, (you, mon, pct, hits, got, want)

    # Contour de la salle : une courbe fermée (chaque sommet touche un nombre pair de côtés), à la bonne taille
    from collections import Counter
    deg = Counter(v for e in ARENA_OUTLINE for v in e)
    assert ARENA_OUTLINE and all(n % 2 == 0 for n in deg.values()), "contour non fermé"
    assert len(set(ARENA_OUTLINE)) == len(ARENA_OUTLINE)
    ys = [v[0] for e in ARENA_OUTLINE for v in e]
    assert min(ys) == -3 and max(ys) == 25         # de la pointe haute (ligne -2) à la pointe basse (ligne 24), plus un sommet

    # Mode Songes : la dernière entrée est une grille libre, sans carte, sans murs et sans limite de salle
    songes = FIGHTS[-1]
    assert songes.free and not songes.blocks and not songes.pits and not any(f.free for f in FIGHTS[:-1])
    far = (60, -40)                                                # bien hors de la salle du Comte
    assert far not in ARENA and is_free(songes, far) and not is_free(FIGHTS[0], far)
    ev = evaluate(songes, (40, 10), (50, 20), 1)
    assert not ev.warnings and ev.landing_on_map and ev.los_aim and ev.los_landing
    assert evaluate(FIGHTS[0], (18, 4), far, 1).warnings          # dans la salle du Comte : toujours une alerte
    g = Calib(500.0, 300.0, 44.0, 22.0)
    for cell in (far, (-10, 8), (100, 4), (30, -50), (12, 4)):     # n'importe quelle case, loin dans tous les sens
        x, y = g.center(cell)
        assert g.cell_at(x + 9, y - 5, free=True) == cell
        assert g.cell_at(x, y) == (cell if cell in ARENA else None)
    # les rotations ne dépendent pas de la salle : le sort atterrit où on l'attend, même hors de la salle du Comte
    for k in range(4):
        assert landing_cell(far, tap_cell(far, (58, -38), k), k) == (58, -38)

    print("OK : carte, tranches, rotations, ligne de vue, calibration, confusion collée, simulateur en ligne, mode Songes")


if __name__ == "__main__":
    main()
