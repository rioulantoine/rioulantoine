#!/usr/bin/env python3
"""Dessine les cartes SVG du README dans la charte du portfolio (antlabs.fr).

Chaque carte existe en deux thèmes (sombre : encre et crème, clair : papier beige et encre),
servis par <picture> selon le thème GitHub du visiteur. Le texte est converti en tracés :
les SVG s'affichent avec Archivo Expanded et Geist partout, sans police à charger.
Le contenu se modifie dans donnees/profil.json, les chiffres viennent de donnees/contributions.json.
"""
import datetime as dt
import json
import math
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "cartes"
PROFIL = json.loads((RACINE / "donnees" / "profil.json").read_text())
CONTRIB = json.loads((RACINE / "donnees" / "contributions.json").read_text())
ICONES = json.loads((RACINE / "donnees" / "icones.json").read_text())

L = 880  # largeur commune, comme la colonne d'un README
MARGE = 5
THEMES = {
    "sombre": {"fond": "#050507", "fond2": "#0c0c10", "fond3": "#14141a", "texte": "#eeece6", "doux": "#a09fa6",
               "sourd": "#6b6a72", "trait": "#24242c", "bord": "#34343e", "fort": "#5c5b66"},
    "clair": {"fond": "#f8f6f0", "fond2": "#f1eee6", "fond3": "#e8e4da", "texte": "#0b0b0f", "doux": "#55545c",
              "sourd": "#86858d", "trait": "#dfdace", "bord": "#d2cdc1", "fort": "#98969e"},
}
MOIS = ["JANV", "FÉVR", "MARS", "AVR", "MAI", "JUIN", "JUIL", "AOÛT", "SEPT", "OCT", "NOV", "DÉC"]


class Police:
    """Une police, mise en forme par HarfBuzz (crénage compris) et dessinée en tracés."""

    def __init__(self, fichier):
        chemin = RACINE / "polices" / fichier
        self.tt = TTFont(chemin)
        self.glyphes = self.tt.getGlyphSet()
        self.ordre = self.tt.getGlyphOrder()
        self.em = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(chemin))))
        self.cache = {}

    def _forme(self, texte):
        tampon = hb.Buffer()
        tampon.add_str(texte)
        tampon.guess_segment_properties()
        hb.shape(self.hb, tampon, {"kern": True, "liga": True})
        return list(zip(tampon.glyph_infos, tampon.glyph_positions))

    def largeur(self, texte, taille, interlettre=0.0):
        g = self._forme(texte)
        return sum(p.x_advance for _, p in g) * taille / self.em + interlettre * taille * max(len(g) - 1, 0)

    def _contour(self, gid):
        if gid not in self.cache:
            stylo = SVGPathPen(self.glyphes)
            self.glyphes[self.ordre[gid]].draw(stylo)
            self.cache[gid] = stylo
        return self.cache[gid]

    def trace(self, texte, taille, x, y, ancre="start", interlettre=0.0):
        """Renvoie l'attribut d d'un chemin ; y est la ligne de base."""
        w = self.largeur(texte, taille, interlettre)
        x -= {"start": 0, "middle": w / 2, "end": w}[ancre]
        k = taille / self.em
        morceaux = []
        for info, pos in self._forme(texte):
            stylo = SVGPathPen(self.glyphes, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
            nom = self.ordre[info.codepoint]
            transforme = TransformPen(stylo, (k, 0, 0, -k, x + pos.x_offset * k, y - pos.y_offset * k))
            self.glyphes[nom].draw(transforme)
            morceaux.append(stylo.getCommands())
            x += pos.x_advance * k + interlettre * taille
        return "".join(morceaux)


TITRE = Police("Archivo-ExpandedExtraBold.ttf")
CORPS = Police("Geist-Regular.ttf")
MOYEN = Police("Geist-Medium.ttf")
MONO = Police("GeistMono-Regular.ttf")


def texte(police, chaine, taille, x, y, couleur, ancre="start", interlettre=0.0, classe=""):
    c = f' class="{classe}"' if classe else ""
    return f'<path{c} fill="{couleur}" d="{police.trace(chaine, taille, x, y, ancre, interlettre)}"/>'


def couper(police, chaine, taille, largeur):
    lignes, ligne = [], ""
    for mot in chaine.split():
        essai = f"{ligne} {mot}".strip()
        if ligne and police.largeur(essai, taille) > largeur:
            lignes.append(ligne)
            ligne = mot
        else:
            ligne = essai
    return lignes + ([ligne] if ligne else [])


def svg(largeur, hauteur, titre, corps, style=""):
    # Le mouvement s'arrête pour les visiteurs qui demandent moins d'animations.
    calme = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    titre = titre.replace("&", "&amp;").replace("<", "&lt;")
    # 5 px de vide autour de chaque carte : posées bord à bord, elles laissent une gouttière de 10 px.
    hauteur += 2 * MARGE
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur:g}" height="{hauteur}" viewBox="0 0 {largeur:g} {hauteur}" '
            f'role="img" aria-label="{titre}"><title>{titre}</title><style>{style}{calme}</style>'
            f'<g transform="translate(0 {MARGE})">{corps}</g></svg>')


def cadre(largeur, hauteur, t, marge=5, rayon=18):
    return (f'<rect x="{marge + 0.5:g}" y="0.5" width="{largeur - 2 * marge - 1:g}" height="{hauteur - 1}" rx="{rayon}" '
            f'fill="{t["fond"]}" stroke="{t["trait"]}"/>')


def fleche(x, y, couleur, taille=12):
    # Flèche en biais, dessinée au trait comme les pictogrammes du site.
    s = taille
    return (f'<path fill="none" stroke="{couleur}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            f'd="M{x:.1f} {y + s:.1f}L{x + s:.1f} {y:.1f}M{x + s * 0.3:.1f} {y:.1f}H{x + s:.1f}V{y + s * 0.7:.1f}"/>')


def coin_points(x, y, t, pas=7, n=6):
    """Le triangle de points du monogramme AR : dense dans l'angle, qui s'efface vers l'intérieur."""
    ronds = []
    for i in range(n):
        for j in range(n):
            if i + j < n - 1:
                continue
            r = 0.35 * (i + j - n + 2) + 0.2
            ronds.append(f'<circle cx="{x - (n - 1 - i) * pas:.1f}" cy="{y - (n - 1 - j) * pas:.1f}" r="{r:.2f}"/>')
    return f'<g fill="{t["texte"]}" opacity=".28">{"".join(ronds)}</g>'


# --- Cartes -----------------------------------------------------------------------------

def hero(t):
    h = 300
    pas = 10
    colonnes = []
    # La trame de la bannière LinkedIn : points crème, gros à gauche, qui s'effacent avant le nom.
    for ci, x in enumerate(range(12, 600, pas)):
        ronds = []
        for y in range(6, h, pas):
            onde = 0.12 * math.sin(y / 38 + x / 90) + 0.08 * math.sin(y / 17 - x / 55)
            force = max(0.0, 1 - x / 560 + onde)
            r = 3.2 * force ** 1.6
            if r > 0.35:
                ronds.append(f'<circle cx="{x}" cy="{y}" r="{r:.2f}"/>')
        if ronds:
            colonnes.append(f'<g class="c" style="animation-delay:{-ci * 0.09:.2f}s">{"".join(ronds)}</g>')
    trame = f'<g clip-path="url(#bord)" fill="{t["texte"]}" opacity=".55">{"".join(colonnes)}</g>'
    nom1, nom2 = PROFIL["nom"]
    corps = [
        f'<defs><clipPath id="bord"><rect x="6" y="1" width="{L - 12}" height="{h - 2}" rx="17"/></clipPath>'
        f'<linearGradient id="voile" x1="0" x2="1"><stop offset=".35" stop-color="{t["fond"]}" stop-opacity="0"/>'
        f'<stop offset=".7" stop-color="{t["fond"]}"/></linearGradient></defs>',
        cadre(L, h, t), trame,
        f'<rect x="6" y="1" width="{L - 12}" height="{h - 2}" rx="17" fill="url(#voile)"/>',
        texte(MONO, PROFIL["site"].replace("https://", "").upper(), 11, L - 44, 46, t["sourd"], "end", 0.08),
        texte(TITRE, nom1, 66, L - 40, 148, t["texte"], "end", -0.02, "n"),
        texte(TITRE, nom2, 66, L - 40, 208, t["texte"], "end", -0.02, "n"),
        texte(MOYEN, PROFIL["metier"], 17, L - 44, 248, t["texte"], "end"),
        texte(CORPS, PROFIL["situation"], 14, L - 44, 270, t["doux"], "end"),
    ]
    style = (".c{animation:respire 7s ease-in-out infinite}"
             "@keyframes respire{0%,100%{opacity:.55}50%{opacity:1}}"
             ".n{animation:entre .9s cubic-bezier(.23,1,.32,1) both}"
             "@keyframes entre{from{opacity:0;transform:translateY(10px)}}")
    return svg(L, h, f'{nom1.title()} {nom2.title()}. {PROFIL["metier"]}, {PROFIL["situation"]}.', "".join(corps), style)


def grille(t):
    jours = CONTRIB["jours"]
    h = 200
    debut = dt.date.fromisoformat(jours[0]["date"])
    decalage = (debut.weekday() + 1) % 7  # les semaines GitHub commencent le dimanche
    semaines = (len(jours) + decalage + 6) // 7
    x0, y0 = 40, 82
    pas = min(15.4, (L - 80) / semaines)
    rayons = [1.1, 2.4, 3.6, 4.8, 6.0]
    ronds, etiquettes, vu = [], [], set()
    for k, j in enumerate(jours):
        s, d = divmod(k + decalage, 7)
        cx, cy = x0 + s * pas + pas / 2, y0 + d * pas + pas / 2
        couleur = t["fort"] if j["niveau"] == 0 else t["texte"]
        ronds.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rayons[j["niveau"]]}" fill="{couleur}" '
                     f'style="animation-delay:{s * 0.018:.2f}s"/>')
        date = dt.date.fromisoformat(j["date"])
        if date.day <= 7 and d == 0 and (date.year, date.month) not in vu and s < semaines - 2:
            vu.add((date.year, date.month))
            etiquettes.append(texte(MONO, MOIS[date.month - 1], 9.5, x0 + s * pas + 2, y0 - 10, t["sourd"], interlettre=0.06))
    total = f'{CONTRIB["total"]:,}'.replace(",", " ")
    corps = [
        cadre(L, h, t),
        texte(MONO, "CONTRIBUTIONS · 12 DERNIERS MOIS", 11, x0 + 2, 44, t["sourd"], interlettre=0.08),
        texte(MOYEN, f"{total} contributions", 15, L - 42, 45, t["texte"], "end"),
        "".join(etiquettes), f'<g class="p">{"".join(ronds)}</g>',
    ]
    style = (".p circle{transform-box:fill-box;transform-origin:center;animation:pousse .6s cubic-bezier(.23,1,.32,1) both}"
             "@keyframes pousse{from{transform:scale(0)}}")
    return svg(L, h, f"Contributions GitHub des 12 derniers mois : {CONTRIB['total']}, en trame de points.", "".join(corps), style)


def activite(t):
    h = 200
    mois = CONTRIB["mois"][-12:]
    haut = max(m["n"] for m in mois) or 1
    x0, base, pas = 40, 160, 34
    colonnes = []
    for i, m in enumerate(mois):
        # Chaque mois est une pile de points, comme la trame : un point pour une part du record.
        n = round(m["n"] / haut * 9) if m["n"] else 0
        cx = x0 + i * pas + 8
        ronds = "".join(f'<circle cx="{cx}" cy="{base - 6 - k * 10}" r="3.6"/>' for k in range(n))
        if not n:
            ronds = f'<circle cx="{cx}" cy="{base - 6}" r="1.2" fill="{t["fort"]}"/>'
        colonnes.append(f'<g style="animation-delay:{i * 0.05:.2f}s">{ronds}</g>')
        mo = int(m["mois"][5:])
        colonnes.append(texte(MONO, MOIS[mo - 1][:1], 9.5, cx, base + 18, t["sourd"], "middle"))
    meilleur = dt.date.fromisoformat(CONTRIB["meilleur_jour"]["date"])
    chiffres = [
        ("SÉRIE ACTUELLE", str(CONTRIB["serie_actuelle"]), "jours d’affilée"),
        ("RECORD", str(CONTRIB["serie_longue"]), "jours d’affilée"),
        ("MEILLEUR JOUR", str(CONTRIB["meilleur_jour"]["n"]), f"le {meilleur.day} {MOIS[meilleur.month - 1].lower()}. {meilleur.year}".replace("mai.", "mai")),
    ]
    blocs = [f'<line x1="470" y1="36" x2="470" y2="{h - 36}" stroke="{t["trait"]}"/>']
    for i, (etiquette, valeur, sous) in enumerate(chiffres):
        x = 500 + i * 120
        blocs.append(texte(MONO, etiquette, 9.5, x, 62, t["sourd"], interlettre=0.08))
        blocs.append(texte(TITRE, valeur, 40, x, 118, t["texte"], interlettre=-0.02))
        blocs.append(texte(CORPS, sous, 12.5, x, 142, t["doux"]))
    corps = [cadre(L, h, t), texte(MONO, "ACTIVITÉ PAR MOIS", 11, x0, 44, t["sourd"], interlettre=0.08),
             f'<g class="m" fill="{t["texte"]}">{"".join(colonnes)}</g>', "".join(blocs)]
    style = (".m g{animation:monte .8s cubic-bezier(.23,1,.32,1) both}"
             "@keyframes monte{from{opacity:0;transform:translateY(8px)}}")
    return svg(L, h, f"Série actuelle {CONTRIB['serie_actuelle']} jours, record {CONTRIB['serie_longue']} jours.", "".join(corps), style)


def tuile(t, tu):
    w, h, m = L / 3, 170, 5
    corps = [
        cadre(w, h, t, m),
        texte(MONO, tu["etiquette"], 10.5, m + 24, 40, t["sourd"], interlettre=0.08),
        fleche(w - m - 36, 29, t["sourd"]),
        texte(TITRE, tu["valeur"], 40, m + 22, 98, t["texte"], interlettre=-0.02),
        *[texte(CORPS, ligne, 13, m + 24, 126 + i * 18, t["doux"]) for i, ligne in enumerate(tu["texte"])],
        coin_points(w - m - 16, h - 16, t),
    ]
    return svg(w, h, f'{tu["etiquette"]} : {tu["valeur"]}, {" ".join(tu["texte"])}', "".join(corps))


def titre_section(t, titre, sous):
    h = 96
    corps = [
        f'<line x1="6" y1="18" x2="{L - 6}" y2="18" stroke="{t["trait"]}"/>',
        texte(TITRE, titre, 26, 6, 66, t["texte"], interlettre=-0.01),
        texte(MONO, sous, 10.5, L - 6, 64, t["sourd"], "end", 0.08),
    ]
    return svg(L, h, titre.title(), "".join(corps))


def projet(t, p):
    w, h, m = L / 3, 224, 5
    pub = bool(p["depot"])
    x = m + 22
    corps = [cadre(w, h, t, m),
             texte(MONO, f'{p["annee"]} · {"CODE SUR GITHUB" if pub else "PAGE DU PROJET"}', 9.5, x + 2, 38, t["sourd"], interlettre=0.08),
             fleche(w - m - 34, 28, t["sourd"], 11)]
    taille = 19 if TITRE.largeur(p["titre"].upper(), 19) < w - 60 else 15
    corps.append(texte(TITRE, p["titre"].upper(), taille, x, 76, t["texte"], interlettre=-0.01))
    for i, ligne in enumerate(couper(CORPS, p["resume"], 13, w - 2 * m - 46)[:3]):
        corps.append(texte(CORPS, ligne, 13, x + 1, 102 + i * 19, t["doux"]))
    # Les technologies en pastilles mono, comme les légendes du site.
    cx, cy = x, 168
    for nom in p["stack"]:
        lw = MONO.largeur(nom, 9.5) + 14
        if cx + lw > w - m - 20:
            cx, cy = x, cy + 26
        corps.append(f'<rect x="{cx:.1f}" y="{cy}" width="{lw:.1f}" height="20" rx="10" fill="none" stroke="{t["bord"]}"/>')
        corps.append(texte(MONO, nom, 9.5, cx + 7, cy + 13.5, t["doux"]))
        cx += lw + 5
    return svg(w, h, f'{p["titre"]} : {p["resume"]}', "".join(corps))


def competences(t):
    lignes, y = [], 46
    x0, xi = 40, 200
    for bloc in PROFIL["competences"]:
        lignes.append(texte(MONO, bloc["titre"], 10.5, x0, y + 4, t["sourd"], interlettre=0.08))
        x, ligne_y = xi, y
        for nom in bloc["items"]:
            lw = 18 + 8 + MOYEN.largeur(nom, 13) + 22
            if x + lw > L - 30:
                x, ligne_y = xi, ligne_y + 30
            ic = ICONES.get(nom, {})
            tr = f'transform="translate({x:.1f} {ligne_y - 10}) scale(.6667)"'
            if "plein" in ic:
                lignes.append(f'<path {tr} fill="{t["texte"]}" d="{ic["plein"]}"/>')
            elif "trait" in ic:
                lignes.append(f'<path {tr} fill="none" stroke="{t["texte"]}" stroke-width="2.2" stroke-linecap="round" '
                              f'stroke-linejoin="round" d="{ic["trait"]}"/>')
            lignes.append(texte(MOYEN, nom, 13, x + 26, ligne_y + 4.5, t["texte"]))
            x += lw
        y = ligne_y + 30
        lignes.append(f'<line x1="{x0}" y1="{y - 12}" x2="{L - 40}" y2="{y - 12}" stroke="{t["trait"]}"/>')
        y += 14
    lignes.pop()  # pas de filet sous le dernier bloc
    h = y + 6
    corps = [cadre(L, h, t), "".join(lignes)]
    return svg(L, h, "Compétences : " + ", ".join(i for b in PROFIL["competences"] for i in b["items"]), "".join(corps))


def ecrire(nom, contenu):
    (DOSSIER / nom).write_text(contenu)


def image(nom, alt, largeur="100%", lien=None):
    """Une carte dans ses deux thèmes : GitHub choisit selon le thème du visiteur."""
    alt = alt.replace('"', "&quot;")
    balise = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="./cartes/{nom}-sombre.svg" />'
              f'<img src="./cartes/{nom}-clair.svg" width="{largeur}" alt="{alt}" /></picture>')
    return f'<a href="{lien}">{balise}</a>' if lien else balise


def readme():
    # Le README est généré lui aussi : les cartes d'une même rangée doivent se suivre sans espace.
    tiers = "33.333%"
    site = PROFIL["site"]
    lignes = [
        "<!-- Généré par scripts/cartes.py à partir de donnees/profil.json : modifier ces fichiers, pas celui-ci.",
        "     Les cartes sont redessinées chaque jour par .github/workflows/cartes.yml. -->",
        '<div align="center">',
        image("hero", f'{" ".join(PROFIL["nom"]).title()}. {PROFIL["metier"]}, {PROFIL["situation"]}.', lien=site) + "<br>",
        image("contributions", "Contributions des 12 derniers mois, en trame de points") + "<br>",
        image("activite", "Activité par mois, série en cours et record") + "<br>",
        "".join(image(f"tuile-{i + 1}", f'{tu["etiquette"]} : {tu["valeur"]}', tiers, tu["lien"])
                for i, tu in enumerate(PROFIL["tuiles"])) + "<br>",
        image("titre-projets", "Projets", lien=f"{site}/#projets") + "<br>",
    ]
    projets = PROFIL["projets"]
    for r in range(0, len(projets), 3):
        lignes.append("".join(image(f"projet-{i + 1}", f'{p["titre"]} : {p["resume"]}', tiers, p["depot"] or p["page"])
                              for i, p in enumerate(projets[r:r + 3], start=r)) + "<br>")
    lignes += [
        image("titre-competences", "Compétences", lien=f"{site}/#competences") + "<br>",
        image("competences", "Compétences : " + ", ".join(i for b in PROFIL["competences"] for i in b["items"])),
        "</div>",
        "",
        '<p align="center">',
        f'<a href="{site}">antlabs.fr</a> &nbsp;·&nbsp; <a href="{PROFIL["linkedin"]}">LinkedIn</a> &nbsp;·&nbsp; '
        f'<a href="{site}/cv-antoine-rioul.pdf">CV</a> &nbsp;·&nbsp; <a href="mailto:{PROFIL["email"]}">{PROFIL["email"]}</a>',
        "</p>",
        "",
    ]
    (RACINE / "README.md").write_text("\n".join(lignes))


def main():
    DOSSIER.mkdir(exist_ok=True)
    for cle, t in THEMES.items():
        ecrire(f"hero-{cle}.svg", hero(t))
        ecrire(f"contributions-{cle}.svg", grille(t))
        ecrire(f"activite-{cle}.svg", activite(t))
        for i, tu in enumerate(PROFIL["tuiles"]):
            ecrire(f"tuile-{i + 1}-{cle}.svg", tuile(t, tu))
        ecrire(f"titre-projets-{cle}.svg", titre_section(t, "PROJETS", "LE RESTE SUR ANTLABS.FR"))
        for i, p in enumerate(PROFIL["projets"]):
            ecrire(f"projet-{i + 1}-{cle}.svg", projet(t, p))
        ecrire(f"titre-competences-{cle}.svg", titre_section(t, "COMPÉTENCES", "EN COURS, EN ENTREPRISE, EN PROJET"))
        ecrire(f"competences-{cle}.svg", competences(t))
    readme()
    print(f"{len(list(DOSSIER.glob('*.svg')))} cartes dans {DOSSIER.relative_to(RACINE)}/")


if __name__ == "__main__":
    main()
