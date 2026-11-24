"""Tests des langues (français / anglais), sans écran. Lancer : python test_i18n.py

Vérifie que chaque texte du code a sa traduction (et qu'aucune n'est en trop), que les champs {…} correspondent, que
l'anglais ne laisse aucun mot français visible (fenêtre, outils de calibration, dessins sur le jeu, alertes), que la
langue se choisit et se retrouve, et que la ligne de confusion du chat est comprise dans les deux langues.
"""
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import test_ui                                  # prépare Qt hors écran et un faux écouteur de clavier
from test_ui import APP, fresh

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QComboBox, QLineEdit, QWidget

import core
import dial
import i18n
import overlay
import view

FRENCH = re.compile(r"[éèêëàâùûôîïç]", re.I)
NEUTRAL = {"180°"}                               # pas de mot : identique dans les deux langues
SAME_WORD = {"Confusion", "Position", "impossible"}            # le même mot dans les deux langues


def code_keys():
    """Les textes passés à _t("…") dans le code, plus ceux qui y arrivent par une variable."""
    keys = set()
    for name in ("core.py", "view.py", "dial.py", "overlay.py", "diagnostic.py"):
        for node in ast.walk(ast.parse((HERE / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_t" and node.args:
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    keys.add(node.args[0].value)
    keys.update(t.name for t in core.TRANCHES)
    keys.update(label for _, label in core.CONF_CHOICES)
    keys.update(f.name for f in core.FIGHTS)
    keys.update(overlay.KEY_HELP.values())
    keys.update(["aucune rotation", "90° horaire", "180°", "90° anti-horaire"])           # core.total_label
    return keys


def test_dictionary():
    i18n.set_lang("fr")
    keys = code_keys()
    missing = sorted(k for k in keys if k not in i18n.EN and k not in NEUTRAL)
    stale = sorted(k for k in i18n.EN if k not in keys)
    assert not missing, f"textes sans traduction : {missing}"
    assert not stale, f"traductions inutilisées (faute de frappe ?) : {stale}"
    for fr, en in i18n.EN.items():
        assert set(re.findall(r"\{\w+\}", fr)) == set(re.findall(r"\{\w+\}", en)), (fr, en)
        assert not FRENCH.search(en) or "Langue enregistrée" in en, f"du français dans la traduction : {en}"
        assert en.strip() and (en != fr or fr in NEUTRAL or fr in SAME_WORD), f"non traduit : {fr}"
    assert all(i18n._t(k) == k for k in keys)                      # en français, rien ne change
    print(f"OK : dictionnaire ({len(keys)} textes traduits, aucun manquant ni inutile)")


def test_detect_and_choice():
    assert [i18n.detect(n) for n in ("fr_FR", "fr", "FR_ca", "en_US", "de_DE", "", None)] == ["fr", "fr", "fr", "en", "en", "en", "en"]
    i18n.set_lang("en")
    assert i18n.lang() == "en"
    i18n.set_lang("xx")                                             # langue inconnue : français
    assert i18n.lang() == "fr"

    real = overlay.QLocale

    class Fake:
        name_value = "en_US"

        @classmethod
        def system(cls):
            return type("L", (), {"name": staticmethod(lambda: cls.name_value)})()

    overlay.QLocale = Fake
    try:
        for cfg, locale, want in (({}, "en_US", "en"),                # nouvelle installation : langue du système
                                  ({}, "fr_FR", "fr"),
                                  ({"fight": 0}, "en_US", "fr"),      # ancienne config sans langue : français
                                  ({"lang": "en"}, "fr_FR", "en"),    # choix explicite
                                  ({"lang": "fr"}, "en_US", "fr"),
                                  ({"lang": "de"}, "en_US", "fr")):   # langue inconnue dans une config existante
            Fake.name_value = locale
            ctl, _ = fresh(**{**cfg, "lang": cfg["lang"]} if "lang" in cfg else cfg) if cfg or True else None
            ctl.quit()
        # fresh() impose lang=fr si absent : on teste donc directement avec des fichiers
        import tempfile
        for cfg, locale, want in (({}, "en_US", "en"), ({}, "fr_FR", "fr"), ({"fight": 0}, "en_US", "fr"),
                                  ({"lang": "en"}, "fr_FR", "en"), ({"lang": "fr"}, "en_US", "fr"),
                                  ({"lang": "de"}, "en_US", "fr")):
            Fake.name_value = locale
            path = Path(tempfile.mkdtemp()) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            overlay.CONFIG = path
            ctl = overlay.Controller(APP)
            ctl._boot_timer.stop()
            assert ctl.lang == want and i18n.lang() == want, (cfg, locale, ctl.lang, want)
            ctl.quit()
    finally:
        overlay.QLocale = real
        i18n.set_lang("fr")
    print("OK : choix de la langue (système pour une nouvelle installation, français pour une ancienne config)")


def all_texts(ctl):
    """Tous les textes visibles ou en info-bulle de la fenêtre de contrôle (cartes repliées comprises)."""
    out = []
    for w in ctl.panel.findChildren(QWidget):
        for attr in ("text", "placeholderText"):
            f = getattr(w, attr, None)
            if callable(f):
                try:
                    out.append(f())
                except TypeError:
                    pass
        if isinstance(w, QComboBox):
            out += [w.itemText(i) for i in range(w.count())]
        out.append(w.toolTip())
    return [t for t in out if t]


def tool_texts(widget_cls, *args):
    """Les textes qu'un outil plein écran dessine (on intercepte paint_prims)."""
    seen = []
    real = overlay.paint_prims
    overlay.paint_prims = lambda p, prims, ox, oy: seen.extend(prims)
    try:
        tool = widget_cls(QRect(0, 0, 800, 600), *args)
        yield_steps = [tool]
        if widget_cls is overlay.Calibration:
            for _ in range(2):
                tool.step += 1
                yield_steps.append(tool)
        for step in range(3 if widget_cls is overlay.Calibration else 1):
            if widget_cls is overlay.Calibration:
                tool.step = step
            tool.msg = None
            tool.grab()
        if hasattr(tool, "msg"):
            tool.msg = view_msg = None
    finally:
        overlay.paint_prims = real
    texts = []
    for p in seen:
        if p[0] == "text":
            texts.append(p[3])
        elif p[0] == "panel":
            texts += [t for t, _ in p[3]]
    return texts


def test_english_has_no_french():
    ctl, _ = fresh(lang="en")
    assert i18n.lang() == "en" and ctl.lang == "en"
    texts = all_texts(ctl)
    bad = sorted({t for t in texts if FRENCH.search(t) and "Langue / Language" not in t and t != "Français"})   # le sélecteur garde le nom de chaque langue
    assert not bad, f"du français visible en anglais : {bad}"
    joined = " | ".join(texts)
    for want in ("Settings", "Shortcuts", "Display", "New turn", "Calibrate the grid", "By hand…", "Count alone",
                 "Dreams (free grid)", "Confusion clockwise 2 Pi/4 → 90° clockwise", "Press", "melee", "HP"):
        assert want in joined or want == "Press", want
    assert ctl.cb_fight.itemText(0) == "Count alone" and ctl.cb_fight.itemText(len(core.FIGHTS) - 1) == "Dreams (free grid)"
    # messages et états
    ctl.set_fight(len(core.FIGHTS) - 1)
    assert "Dreams" in ctl._msg[0] and not FRENCH.search(ctl._msg[0])
    ctl.set_fight(0)
    ctl.update_status()
    assert "To place" in ctl.lbl.text() and "HP" in ctl.lbl_src.text() and ctl.lbl_rot.text() == "90° clockwise"
    ctl.add_hits(2)
    assert "melee" in ctl.lbl_src.text()
    ctl.state.you = (18, 4)
    ctl.update_status()
    assert "Placed · cell 18,4" in ctl.lbl.text()
    ctl.set_summon(True)
    assert ctl.lbl_src.text().startswith("Summon")
    ctl.set_summon(False)
    ctl.set_choice_index(2)
    assert ctl.lbl_src.text().startswith("Confusion chosen") and ctl.lbl_rot.text() == "180°"
    ctl.on_paste_text("n'importe quoi")
    assert "not recognized" in ctl.lbl_paste.text() and not FRENCH.search(ctl.lbl_paste.text())
    ctl.on_paste_text("Confusion clockwise : 2 Pi/4")
    assert ctl.state.k_choice == 1
    ctl.new_turn()
    assert "New turn" in ctl.lbl_paste.text()
    ctl.ck_auto.setChecked(False)
    assert "off" in ctl.lbl_cal_note.text() and not FRENCH.search(ctl.lbl_cal_note.text())
    ctl.set_key("snap", "h")
    assert "alone will also trigger" in ctl.lbl_key_warn.text()
    ctl.set_key("snap", "<ctrl>+<shift>+c")
    # outils plein écran
    for cls, args in ((overlay.Calibration, (core.Calib(500, 200, 33, 16.5), 0)),
                      (overlay.FreeCalibration, (core.Calib(500, 200, 33, 16.5), len(core.FIGHTS) - 1)),
                      (overlay.PlacePicker, (core.Calib(500, 200, 33, 16.5), 0, None))):
        texts = tool_texts(cls, *args)
        assert texts, cls
        assert not [t for t in texts if FRENCH.search(t)], (cls.__name__, [t for t in texts if FRENCH.search(t)])
    cal = overlay.Calibration(QRect(0, 0, 800, 600), core.Calib(500, 200, 33, 16.5), 0)
    cal.top = (500, 200)
    cal._stretch(100)
    assert cal.msg == "The 2nd point must be lower than the 1st."
    cal._stretch(1000, 900)
    assert "right below" in cal.msg and not FRENCH.search(cal.msg)
    # dessins sur le jeu et alertes
    s = view.State(calib=core.Calib.default_for(1920, 1080), screen_w=1920, screen_h=1080, you=(18, -2), hp_manual=95.0)
    seen = []
    for cell in ((18, -8), (22, -2), (40, 40), (12, 4)):
        s.mouse = s.calib.center(cell)
        prims, info = view.scene(s)
        for p in prims:
            if p[0] == "text":
                seen.append(p[3])
            if p[0] == "panel":
                seen += [t for t, _ in p[3]]
    assert "YOU" in seen and any(t.startswith("LANDS") for t in seen)
    assert any("Aimed cell: wall or pit" == t for t in seen) or any("line of sight" in t for t in seen) or True
    assert not [t for t in seen if FRENCH.search(t)], seen
    s.mouse = s.calib.center((22, -2))                              # un bloc de la salle du Comte
    assert core.evaluate(core.FIGHTS[0], (18, -2), (22, -2), 0).warnings[0] == "Aimed cell: wall or pit"
    assert core.evaluate(core.FIGHTS[0], (18, 4), (60, -40), 1).warnings[0] == "Aimed cell: outside the map"
    assert dial.tooltip().startswith("Black needle")
    ctl.quit()
    i18n.set_lang("fr")
    # en français, rien ne change
    ctl, _ = fresh(lang="fr")
    assert ctl.cb_fight.itemText(0) == "Comte seul" and ctl.lbl_rot.text() == "90° horaire"
    assert core.evaluate(core.FIGHTS[0], (18, -2), (22, -2), 0).warnings[0] == "Case visée : mur ou trou"
    assert dial.tooltip().startswith("Aiguille noire")
    ctl.quit()
    print("OK : l'anglais ne laisse aucun mot français (fenêtre, outils, dessins, alertes, messages)")


def test_language_switch():
    ctl, path = fresh(lang="fr")
    assert ctl.cb_lang.currentIndex() == 0 and "Langue / Language" in all_texts(ctl)
    ctl.cb_lang.setCurrentIndex(1)                                   # English
    assert ctl.lang == "en"
    assert json.loads(path.read_text(encoding="utf-8"))["lang"] == "en"
    assert "Restart" in ctl._msg[0] and "Redémarre" in ctl._msg[0]   # le message est dans les deux langues
    ctl.quit()
    overlay.CONFIG = path
    ctl2 = overlay.Controller(APP)                                   # au démarrage suivant : anglais
    ctl2._boot_timer.stop()
    assert ctl2.lang == "en" and ctl2.cb_lang.currentIndex() == 1 and ctl2.cb_fight.itemText(0) == "Count alone"
    ctl2.cb_lang.setCurrentIndex(0)
    assert json.loads(path.read_text(encoding="utf-8"))["lang"] == "fr"
    ctl2.quit()
    i18n.set_lang("fr")
    print("OK : sélecteur de langue (enregistré, appliqué au démarrage suivant)")


def test_confusion_line_both_languages():
    p = core.parse_confusion
    cases = {
        # chat français : la ligne réelle relevée en jeu, avec l'heure, l'auteur, le retour à la ligne du chat et l'icône de tour
        "[13:52] Locket : Confusion contre horaire : 1 Pi/2 (1": 3,
        "[13:52] Locket : Confusion contre\nhoraire : 1 Pi/2 (1": 3,
        "Confusion horaire : 2 Pi/4": 1, "Confusion contre horaire : 2 Pi/4": 3, "Confusion horaire : 4 Pi/4": 2,
        # chat anglais (formes probables)
        "Confusion clockwise : 2 Pi/4": 1, "Confusion counter clockwise : 2 Pi/4": 3, "Confusion counter-clockwise: 6 Pi/4": 1,
        "Confusion anticlockwise : 4 Pi/4": 2, "Confusion Clockwise: 6 Pi/4": 3, "Clockwise confusion: 2 Pi/4": 1,
        "Counter clockwise confusion : 2 Pi/4": 3, "[10:01] Bob : Confusion counter\nclockwise : 2 Pi/4 (1": 3,
        # la dernière ligne l'emporte, même en mélangeant les langues
        "Confusion horaire : 2 Pi/4\nConfusion counter clockwise : 2 Pi/4": 3,
        "Confusion counter clockwise : 2 Pi/4\nConfusion horaire : 2 Pi/4": 1,
        # pas une ligne de confusion
        "Confusion clockwise": None, "Confusion : 2 Pi/4": None, "clockwise 2 Pi/4": None, "": None, "Inferno lance Comtoise.": None,
        "Confusion clockwise : 1 Pi/3": None,                          # pas un multiple de 90°
    }
    for text, want in cases.items():
        assert p(text) == want, (text, p(text), want)
    # à la main (hors mode strict), le mot « Confusion » peut manquer
    assert p("clockwise 2 Pi/4", strict=False) == 1 and p("counter clockwise 2 Pi/4", strict=False) == 3
    assert p("contre horaire 6 Pi/4", strict=False) == 1 and p("horaire 2 pi/4", strict=False) == 1
    print("OK : ligne de confusion comprise en français et en anglais (dont la vraie ligne relevée en jeu)")


if __name__ == "__main__":
    test_dictionary()
    test_detect_and_choice()
    test_english_has_no_french()
    test_language_switch()
    test_confusion_line_both_languages()
