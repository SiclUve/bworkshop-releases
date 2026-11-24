"""Langues de l'application : français (la langue du code source) et anglais.

Les textes du code sont écrits en français. `_t("texte")` renvoie le texte tel quel en français, ou sa traduction
anglaise (dictionnaire EN plus bas). Un texte absent du dictionnaire reste en français : test_i18n.py vérifie qu'il n'en
manque aucun. Les textes qui contiennent une valeur utilisent des champs nommés : `_t("Placé · case {a},{b}").format(...)`.

La langue se choisit au démarrage (config.json : "lang"), ou avec le sélecteur de la carte Réglages (un redémarrage
est nécessaire). L'installateur écrit la langue choisie dans config.json.
"""

LANGS = {"fr": "Français", "en": "English"}
_lang = "fr"


def set_lang(code):
    """Choisit la langue ('fr' ou 'en') ; tout autre code donne le français."""
    global _lang
    _lang = code if code in LANGS else "fr"


def lang():
    return _lang


def detect(locale_name):
    """Langue à proposer d'après le nom de la langue du système (« fr_FR », « en_US »…) : français, sinon anglais."""
    return "fr" if str(locale_name).lower().startswith("fr") else "en"


def _t(text):
    """Le texte dans la langue choisie."""
    if _lang == "en":
        return EN.get(text, text)
    return text


EN = {
    # --- combats et rotations (core.py)
    "Comte seul": "Count alone",
    "Comte + Nileza": "Count + Nileza",
    "Comte + Klime": "Count + Klime",
    "Comte + Sylargh": "Count + Sylargh",
    "Songes (grille libre)": "Dreams (free grid)",
    "90° horaire": "90° clockwise",
    "90° anti-horaire": "90° counter-clockwise",
    "aucune rotation": "no rotation",
    "Confusion : selon mes PV": "Confusion: from my HP",
    "Confusion horaire 2 Pi/4 → 90° horaire": "Confusion clockwise 2 Pi/4 → 90° clockwise",
    "Confusion horaire 4 Pi/4 → 180°": "Confusion clockwise 4 Pi/4 → 180°",
    "Confusion horaire 6 Pi/4 → 90° anti-horaire": "Confusion clockwise 6 Pi/4 → 90° counter-clockwise",
    "Confusion 0 Pi/4 → aucune rotation": "Confusion 0 Pi/4 → no rotation",
    "Case visée : hors de la carte": "Aimed cell: outside the map",
    "Case visée : mur ou trou": "Aimed cell: wall or pit",
    "Le sort atterrit hors de la carte": "The spell lands outside the map",
    "Pas de ligne de vue vers la case visée": "No line of sight to the aimed cell",
    "Pas de ligne de vue vers la case d'atterrissage": "No line of sight to the landing cell",
    # --- dessins sur le jeu (view.py)
    "TOI": "YOU",
    "ATTERRIT ICI": "LANDS HERE",
    "ATTERRIT SUR LA CASE VISÉE": "LANDS ON THE AIMED CELL",
    # --- cadran (dial.py)
    "Aiguille noire : où part ton sort.\nRepère cyan : où tu vises.\n"
    "Sans visée (pas placé, souris hors de la salle), le repère reste en haut et l'aiguille\n"
    "montre la rotation : si tu vises en haut, le sort part là où elle pointe.":
        "Black needle: where your spell goes.\nCyan marker: where you aim.\n"
        "Without aim (not placed, mouse outside the room), the marker stays at the top and the needle\n"
        "shows the rotation: if you aim up, the spell goes where it points.",
    # --- raccourcis : libellés
    "me placer : souris sur ta case": "place me: mouse on your cell",
    "retirer ma position (pendant que tu te déplaces)": "clear my position (while you move)",
    "confusion suivante dans le menu": "next confusion in the menu",
    "nouveau tour : lignes à 0, confusion à rechoisir": "new turn: lines back to 0, pick your confusion again",
    "+1 ligne de dégâts que TU infliges au corps à corps (un sort à 2 lignes = 2)":
        "+1 line of melee damage YOU deal (a 2-line spell = 2)",
    "-1 ligne de dégâts au corps à corps": "-1 line of melee damage",
    "je joue une invocation (aucune confusion) : activer / désactiver": "I'm playing a summon (no confusion): on / off",
    "calibrer la grille (automatique)": "calibrate the grid (automatic)",
    "afficher / masquer l'overlay": "show / hide the overlay",
    "grille : caler sur la case sous la souris (pour affiner à la main)":
        "grid: snap to the cell under the mouse (to fine-tune by hand)",
    "grille : décaler à gauche (1 px, accélère si tu insistes)": "grid: shift left (1 px, speeds up if you keep pressing)",
    "grille : décaler à droite": "grid: shift right",
    "grille : décaler vers le haut": "grid: shift up",
    "grille : décaler vers le bas": "grid: shift down",
    "grille : agrandir autour de la souris": "grid: enlarge around the mouse",
    "grille : rapetisser autour de la souris": "grid: shrink around the mouse",
    "aucune": "none",
    "Clique puis appuie sur une touche (ex. F6, Ctrl + F9). Échap = annuler, Suppr = aucune touche":
        "Click, then press a key (e.g. F6, Ctrl + F9). Esc = cancel, Del = no key",
    "Appuie sur une touche…": "Press a key…",
    "Clique une touche, puis appuie sur la nouvelle.": "Click a key, then press the new one.",
    "Attention : « {key} » seule marchera aussi quand tu écris dans le chat. Préfère une touche F ou Ctrl + touche.":
        "Careful: “{key}” alone will also trigger while you type in the chat. Prefer an F key or Ctrl + key.",
    # --- calibration à la main (étapes)
    "Le 2e point doit être plus bas que le 1er.": "The 2nd point must be lower than the 1st.",
    "Le 2e point doit être juste sous le 1er (la case du milieu, même colonne).":
        "The 2nd point must be right below the 1st (the middle cell, same column).",
    "Ces deux points sont trop proches ou trop éloignés pour une salle entière.":
        "These two points are too close or too far apart for a whole room.",
    "Repère approximatif": "Rough marker",
    "Doit être la case du milieu, en bas": "Must be the middle cell, at the bottom",
    "1/3 · Clique sur le SOL de la case du milieu, tout en HAUT de la salle":
        "1/3 · Click the FLOOR of the middle cell, at the very TOP of the room",
    "Les 3 cases du bord haut : prends celle du milieu. Vise le sol (les pieds), pas le personnage.":
        "The 3 cells on the top edge: take the middle one. Aim at the floor (the feet), not the character.",
    "2/3 · Descends la souris : la grille s'étire. Clique quand la case jaune est celle du milieu, tout en BAS":
        "2/3 · Move the mouse down: the grid stretches. Click when the yellow cell is the middle one, at the very BOTTOM",
    "Le contour cyan doit longer le bord du carrelage. Retour arrière ou clic droit = refaire le 1er point.":
        "The cyan outline must follow the edge of the tiles. Backspace or right-click = redo the 1st point.",
    "3/3 · Fais coller le contour cyan au bord du carrelage (les dents du zigzag), puis Entrée":
        "3/3 · Make the cyan outline match the edge of the tiles (the zigzag teeth), then Enter",
    "Glisser = déplacer · molette = taille · flèches = 1 pixel (Maj = 10) · retour arrière = tout refaire":
        "Drag = move · wheel = size · arrows = 1 pixel (Shift = 10) · Backspace = start over",
    "Regarde surtout les pointes à gauche et à droite : c'est là qu'un décalage de côté se voit le mieux.":
        "Look mainly at the tips on the left and right: that is where a sideways offset shows best.",
    "Entrée = valider · Échap = annuler": "Enter = confirm · Esc = cancel",
    "Échap = annuler": "Esc = cancel",
    # --- calage à la main du mode Songes
    "Songes : fais coller la grille aux carreaux du jeu, sur tout l'écran":
        "Dreams: make the grid match the game's tiles, across the whole screen",
    "Glisser = déplacer · molette = taille (autour de la souris) · flèches = 1 pixel (Maj = 10)":
        "Drag = move · wheel = size (around the mouse) · arrows = 1 pixel (Shift = 10)",
    "Règle d'abord la position sur un carreau, puis regarde un carreau tout au bord de l'écran : "
    "s'il dérive, corrige la taille.":
        "First set the position on one tile, then look at a tile right at the edge of the screen: "
        "if it drifts, fix the size.",
    # --- placement au clic
    "Clique sur la case de ton personnage": "Click your character's cell",
    "Hors de la salle (si la grille est décalée, calibre-la d'abord)":
        "Outside the room (if the grid is offset, calibrate it first)",
    "Cette case est un bloc ou un trou": "This cell is a block or a pit",
    # --- fenêtre de contrôle
    "Fermer l'overlay": "Close the overlay",
    "Confusion": "Confusion",
    "Tour": "Turn",
    "PV": "HP",
    "Position": "Position",
    "Affichage": "Display",
    "Réglages": "Settings",
    "Raccourcis": "Shortcuts",
    "Le jeu écrit la rotation de deux façons : « horaire 2 Pi/4 » = « contre horaire 6 Pi/4 »,\n"
    "« horaire 6 Pi/4 » = « contre horaire 2 Pi/4 ». Les deux donnent le même résultat.":
        "The game writes the rotation in two ways: “clockwise 2 Pi/4” = “counter-clockwise 6 Pi/4”,\n"
        "“clockwise 6 Pi/4” = “counter-clockwise 2 Pi/4”. Both give the same result.",
    "Colle ici la ligne de confusion": "Paste the confusion line here",
    "Colle « Confusion horaire : 2 Pi/4 » (la copier dans le chat suffit, c'est automatique)":
        "Paste “Confusion clockwise: 2 Pi/4” (copying it from the chat is enough, it's automatic)",
    "Ligne non reconnue (ex. « Confusion horaire : 2 Pi/4 »)":
        "Line not recognized (e.g. “Confusion clockwise: 2 Pi/4”)",
    "Nouveau tour : choisis ou copie ta nouvelle confusion": "New turn: pick or copy your new confusion",
    "Lignes càc": "Melee lines",
    "Lignes de dégâts que tu infliges au corps à corps ce tour": "Lines of melee damage you deal this turn",
    "Nouveau tour": "New turn",
    "Lignes à 0, confusion à rechoisir": "Lines back to 0, pick your confusion again",
    "Invocation (aucune confusion)": "Summon (no confusion)",
    "Utilisés seulement si aucune confusion n'est choisie.": "Used only when no confusion is chosen.",
    "PV à la main": "HP by hand",
    "{hi} % à {lo} % : {name}": "{hi} % to {lo} %: {name}",
    "Me placer (clic)": "Place me (click)",
    "Retirer": "Clear",
    "Efface ta case et les traits pendant que tu te déplaces ; replace-toi ensuite":
        "Clears your cell and the lines while you move; place yourself again afterwards",
    "Fenêtre": "Window",
    "Dessins": "Drawings",
    "Grille": "Grid",
    "Calibrer la grille": "Calibrate the grid",
    "À la main…": "By hand…",
    "Calibration en 2 clics, si le calage automatique ne marche pas":
        "2-click calibration, in case automatic calibration doesn't work",
    "Calage automatique (au lancement et à « Me placer »)": "Automatic calibration (at launch and on “Place me”)",
    "Décoche-la si la grille bouge trop quand tu te places : « Calibrer la grille » reste disponible":
        "Untick it if the grid moves too much when you place yourself: “Calibrate the grid” stays available",
    "Combat": "Fight",
    "Écran": "Screen",
    "Écran {n} ({w}×{h})": "Screen {n} ({w}×{h})",
    "Tout réafficher": "Show everything",
    "Mode mini : ne garder que le cadran et la rotation": "Mini mode: keep only the dial and the rotation",
    "Mode Songes : la grille ne se recale jamais toute seule et garde sa taille. « Calibrer la grille » "
    "ouvre le calage à la main : fais coller la grille aux carreaux du jeu.":
        "Dreams mode: the grid never recalibrates on its own and keeps its size. “Calibrate the grid” opens the "
        "by-hand calibration: make the grid match the game's tiles.",
    "Calage automatique désactivé : la grille ne bouge que si tu cliques sur « Calibrer la grille ».":
        "Automatic calibration is off: the grid only moves when you click “Calibrate the grid”.",
    "La grille se cale toute seule quand tu fais « Me placer » (et au lancement). Ouvre ton combat d'abord.":
        "The grid calibrates itself when you “Place me” (and at launch). Open your fight first.",
    "Ouvre le calage à la main de la grille libre": "Opens the by-hand calibration of the free grid",
    "Retrouve la salle sur ton écran et cale la grille toute seule":
        "Finds the room on your screen and calibrates the grid on its own",
    "Toujours affichée en mode Songes": "Always shown in Dreams mode",
    "Mode Songes : grande grille libre, jamais recalée toute seule.":
        "Dreams mode: big free grid, never recalibrated on its own.",
    # --- messages du calage automatique
    "Impossible de capturer l'écran.": "Unable to capture the screen.",
    "Recherche de la salle sur ton écran…": "Looking for the room on your screen…",
    "Grille calée automatiquement.": "Grid calibrated automatically.",
    "La grille est déjà bien calée.": "The grid is already well calibrated.",
    "Salle non reconnue sur cet écran. Ouvre ton combat (jeu en fenêtre, sur l'écran choisi dans Réglages), "
    "ou calibre à la main.":
        "Room not recognized on this screen. Open your fight (game in windowed mode, on the screen chosen in "
        "Settings), or calibrate by hand.",
    # --- état affiché à côté du cadran
    "Invocation": "Summon",
    "Confusion choisie": "Confusion chosen",
    "PV {pv} %": "HP {pv} %",
    " · {n} càc": " · {n} melee",
    "Déplacement · <b>{key}</b> sur ta case": "Moving · <b>{key}</b> on your cell",
    "À placer · <b>{key}</b> sur ta case": "To place · <b>{key}</b> on your cell",
    "Placé · case {a},{b}": "Placed · cell {a},{b}",
    "Raccourcis indisponibles ({err})": "Shortcuts unavailable ({err})",
    # --- robustesse et diagnostic (safety.py, diagnostic.py)
    "Impossible d'enregistrer les réglages (dossier protégé ?). Ils ne seront pas gardés.": 'Unable to save the settings (protected folder?). They will not be kept.',
    'Rapport écrit :\n{path}': 'Report written:\n{path}',
    'Diagnostic de Harebourg Overlay {version}': 'Harebourg Overlay diagnostic {version}',
    'Écrans :': 'Screens:',
    'écran {n} : {w}x{h} en ({x},{y}), {dpr} pixel(s) par point': 'screen {n}: {w}x{h} at ({x},{y}), {dpr} pixel(s) per point',
    'Jeu :': 'Game:',
    'aucune fenêtre Dofus visible': 'no visible Dofus window',
    "Le jeu n'est pas visible : lance le diagnostic pendant un combat, avec le jeu devant.": 'The game is not visible: run the diagnostic during a fight, with the game in front.',
    'fenêtré': 'windowed',
    'plein écran sans bordure (compatible)': 'borderless fullscreen (compatible)',
    "sans bordure, plus petit que l'écran (compatible)": 'borderless, smaller than the screen (compatible)',
    "mode d'affichage inconnu": 'unknown display mode',
    '« {title} » : {w}x{h} en ({x},{y}), {mode}': '“{title}”: {w}x{h} at ({x},{y}), {mode}',
    'lancé en administrateur : {answer}': 'run as administrator: {answer}',
    'oui': 'yes',
    'non': 'no',
    'inconnu': 'unknown',
    "Le jeu tourne en administrateur : les raccourcis clavier ne marcheront que si l'overlay l'est aussi.": 'The game runs as administrator: keyboard shortcuts will only work if the overlay does too.',
    "Capture d'écran :": 'Screen capture:',
    'impossible': 'impossible',
    "La capture d'écran est impossible : le calage automatique ne marchera pas (calibre à la main).": 'Screen capture is impossible: automatic calibration will not work (calibrate by hand).',
    '{w}x{h} en {ms} ms, luminosité moyenne {mean}/255, pixels bruns {brown} %': '{w}x{h} in {ms} ms, average brightness {mean}/255, brown pixels {brown} %',
    'La capture est toute noire (jeu en plein écran exclusif ?) : passe le jeu en fenêtre sans bordure.': 'The capture is all black (exclusive fullscreen?): switch the game to borderless windowed mode.',
    'Reconnaissance de la salle :': 'Room recognition:',
    'salle non reconnue (score {score})': 'room not recognized (score {score})',
    "La salle n'est pas reconnue : ouvre un combat du Comte, bien visible, puis relance.": 'The room is not recognized: open a Count fight, fully visible, then run it again.',
    'salle reconnue : score {score}, case {cell} px, x0={x0}, y0={y0}': 'room recognized: score {score}, cell {cell} px, x0={x0}, y0={y0}',
    'ta grille enregistrée est écartée de {dx} px (x), {dy} px (y), taille {dk} %': 'your saved grid is off by {dx} px (x), {dy} px (y), size {dk} %',
    'Ta grille enregistrée est décalée : appuie sur F6 (ou « Calibrer la grille »).': 'Your saved grid is offset: press F6 (or “Calibrate the grid”).',
    'Raccourcis clavier globaux :': 'Global keyboard shortcuts:',
    'installés sans erreur': 'installed without error',
    'erreur : {err}': 'error: {err}',
    "Les raccourcis clavier ne s'installent pas : {err}": 'Keyboard shortcuts cannot be installed: {err}',
    'Réglages :': 'Settings:',
    'fichier : {path} ({state})': 'file: {path} ({state})',
    'inscriptible': 'writable',
    'protégé': 'protected',
    'Le dossier des réglages est protégé : tes réglages ne seront pas gardés.': 'The settings folder is protected: your settings will not be kept.',
    'valeurs invalides ignorées : {keys}': 'invalid values ignored: {keys}',
    'Résultat :': 'Result:',
    'tout est bon pour jouer.': 'everything is fine to play.',
    '{n} point(s) à voir :': '{n} point(s) to check:',
}
