"""Filtres de calcul en mémoire : les lignes originales du registre restent intactes."""

def passe_exploitable(r):
    if r.get('q_etat') == 'incoherent':
        return False
    # Anciens gains attribués par défaut à une petite rune : ne pas réapprendre cette supposition.
    if r.get('certitude') == 'lue' and r.get('effets'):
        from forge.cout import nom_de_gain
        gains = [(i, e) for i, e in enumerate(r['effets']) if e[1] > 0]
        if gains:
            if len(gains) != 1:
                return False
            i, e = gains[0]
            pct = r.get('effets_pct') or []
            nom = nom_de_gain(e[0], e[1], pct[i] if i < len(pct) else False)
            return nom is not None and nom == r.get('rune')
    return True
