#!/usr/bin/env python3
"""Récupère le calendrier de contributions public et écrit donnees/contributions.json.

On lit la même page que le profil GitHub affiche (sans jeton), pour que les chiffres
soient ceux que voient les visiteurs. Si la page change de forme, on se rabat sur
l'API GraphQL avec GITHUB_TOKEN. Lancé chaque jour par le workflow « cartes ».
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "donnees" / "contributions.json"
UTILISATEUR = json.loads((RACINE / "donnees" / "profil.json").read_text())["utilisateur"]


def lire(url, donnees=None, entetes=None):
    req = urllib.request.Request(url, data=donnees, headers={"User-Agent": "profil-readme", **(entetes or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def depuis_page():
    html = lire(f"https://github.com/users/{UTILISATEUR}/contributions")
    bulles = {m[0]: m[1] for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html)}
    jours = []
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        date = re.search(r'data-date="([^"]+)"', td)
        if not date:
            continue
        ident = re.search(r'id="([^"]+)"', td)
        niveau = re.search(r'data-level="(\d)"', td)
        texte = bulles.get(ident.group(1) if ident else "", "")
        n = re.match(r"(\d+)", texte.replace(",", ""))
        jours.append({"date": date.group(1), "n": int(n.group(1)) if n else 0, "niveau": int(niveau.group(1)) if niveau else 0})
    return jours


def depuis_api():
    jeton = os.environ.get("GITHUB_TOKEN")
    if not jeton:
        return []
    requete = '{user(login:"%s"){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel}}}}}}' % UTILISATEUR
    rep = json.loads(lire("https://api.github.com/graphql", json.dumps({"query": requete}).encode(), {"Authorization": f"bearer {jeton}"}))
    niveaux = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    semaines = rep["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [{"date": j["date"], "n": j["contributionCount"], "niveau": niveaux[j["contributionLevel"]]} for s in semaines for j in s["contributionDays"]]


def series(jours):
    # La série en cours ne se casse pas sur aujourd'hui : la journée n'est pas finie.
    i = len(jours) - 1
    if i >= 0 and jours[i]["n"] == 0:
        i -= 1
    actuelle = 0
    while i >= 0 and jours[i]["n"] > 0:
        actuelle, i = actuelle + 1, i - 1
    longue = courante = 0
    for j in jours:
        courante = courante + 1 if j["n"] > 0 else 0
        longue = max(longue, courante)
    return actuelle, longue


def main():
    try:
        jours = depuis_page()
    except Exception as e:  # réseau ou page indisponible
        print(f"page illisible : {e}", file=sys.stderr)
        jours = []
    if not jours:
        jours = depuis_api()
    if not jours:
        sys.exit("aucune donnée de contribution")
    jours.sort(key=lambda j: j["date"])
    actuelle, longue = series(jours)
    meilleur = max(jours, key=lambda j: j["n"])
    mois = {}
    for j in jours:
        mois[j["date"][:7]] = mois.get(j["date"][:7], 0) + j["n"]
    donnees = {
        "genere": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": sum(j["n"] for j in jours),
        "jours_actifs": sum(1 for j in jours if j["n"] > 0),
        "serie_actuelle": actuelle,
        "serie_longue": longue,
        "meilleur_jour": {"date": meilleur["date"], "n": meilleur["n"]},
        "mois": [{"mois": k, "n": v} for k, v in sorted(mois.items())],
        "jours": jours,
    }
    SORTIE.write_text(json.dumps(donnees, indent=1, ensure_ascii=False))
    print(f"{donnees['total']} contributions, série {actuelle}, record {longue}")


if __name__ == "__main__":
    main()
