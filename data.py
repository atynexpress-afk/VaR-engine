"""
data.py
Module chargé de récupérer les données de marché et de construire le portefeuille.
Il ne fait AUCUN calcul de risque : il prépare seulement les données.
"""

import time
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf

TENTATIVES = 3          # nombre d'essais si Yahoo Finance ne répond pas
PAUSE = 2               # secondes d'attente entre deux essais (doublées à chaque fois)


def _telecharger(tickers, debut, fin, tentatives=TENTATIVES):
    """
    Appelle Yahoo Finance, en réessayant si le service ne répond pas.
    Sur un serveur partagé comme Streamlit Cloud, Yahoo limite parfois le nombre
    de requêtes : un nouvel essai quelques secondes plus tard suffit souvent.
    Renvoie les prix de clôture, ou None si tous les essais ont échoué.
    """
    for essai in range(tentatives):
        try:
            donnees = yf.download(tickers, start=debut, end=fin,
                                  auto_adjust=True, progress=False)
            if len(donnees) > 0:
                return donnees["Close"]
        except Exception:               # coupure réseau, limite de requêtes…
            pass
        if essai < tentatives - 1:
            time.sleep(PAUSE * 2 ** essai)
    return None


def telecharger_prix(tickers, debut, fin=None, tentatives=TENTATIVES):
    """
    Télécharge les prix de clôture ajustés d'une liste d'actions.

    Paramètres
    ----------
    tickers : liste de textes, ex. ["MC.PA", "AIR.PA"]
    debut   : date de début, ex. "2020-01-01"
    fin     : date de fin (None = jusqu'à aujourd'hui)
    tentatives : nombre d'essais si Yahoo Finance ne renvoie rien

    Renvoie
    -------
    Un tableau (DataFrame) : une colonne par action, une ligne par jour.
    """
    prix = _telecharger(tickers, debut, fin, tentatives)
    if prix is None:
        raise ValueError("Yahoo Finance ne répond pas pour le moment (service indisponible ou "
                         "trop de requêtes). Réessaie dans quelques minutes, ou vérifie les "
                         f"codes des actions : {', '.join(tickers)}.")

    # Si une seule action est demandée, yfinance peut renvoyer une Series :
    # on la transforme en tableau à une colonne pour toujours avoir le même format.
    if isinstance(prix, pd.Series):
        prix = prix.to_frame(name=tickers[0])

    # On repère les tickers pour lesquels on n'a reçu aucune donnée.
    manquants = []
    for t in tickers:
        if t not in prix.columns or prix[t].isna().all():
            manquants.append(t)
    if len(manquants) > 0:
        raise ValueError(f"Aucune donnée trouvée pour : {', '.join(manquants)}. "
                         "Vérifie le code de l'action sur finance.yahoo.com.")

    prix = prix[tickers]    # on remet les colonnes dans l'ordre demandé
    prix = prix.dropna()    # on enlève les jours où une action n'a pas coté
    return prix


# ---------------------------------------------------------------------------
# CONVERSION EN EUROS
# Un portefeuille en euros qui contient Apple (cotée en dollars) est exposé au
# risque de change : si le dollar baisse, l'action perd de la valeur en euros
# même si son cours en dollars ne bouge pas. On convertit donc chaque cours en
# euros, jour par jour, avant de calculer les rendements.
# ---------------------------------------------------------------------------
# Certaines places cotent en centièmes de devise (Londres : pence, « GBp »)
SOUS_UNITES = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ZAc": ("ZAR", 100),
               "ILA": ("ILS", 100)}


@lru_cache(maxsize=None)
def devise(ticker):
    """
    Devise de cotation d'un titre, ex. 'AAPL' -> 'USD', 'MC.PA' -> 'EUR'.
    lru_cache garde la réponse en mémoire : Yahoo n'est interrogé qu'une fois par titre.
    En cas d'échec, on suppose l'euro.
    """
    try:
        return yf.Ticker(ticker).fast_info["currency"] or "EUR"
    except Exception:
        return "EUR"


def convertir_en_euros(prix, devises, taux):
    """
    Convertit chaque colonne de prix en euros.

    prix    : DataFrame des cours (une colonne par titre)
    devises : {titre: devise de cotation}, ex. {"AAPL": "USD"}
    taux    : DataFrame des taux de change, une colonne par devise, exprimés en
              unités de devise pour 1 euro (ex. colonne "USD" = 1,10 dollar pour 1 €)
    Prix en euros = prix en devise / taux du même jour.
    """
    en_euros = prix.copy()
    for titre, dev in devises.items():
        diviseur = 1
        if dev in SOUS_UNITES:                     # pence -> livres, etc.
            dev, diviseur = SOUS_UNITES[dev]
        if dev == "EUR":
            continue
        # Le change cote presque tous les jours : on reprend le dernier taux connu
        # pour les jours où il manquerait (ffill = « forward fill »).
        taux_du_jour = taux[dev].reindex(prix.index).ffill()
        en_euros[titre] = prix[titre] / diviseur / taux_du_jour
    return en_euros.dropna()


def telecharger_prix_euros(tickers, debut, fin=None, tentatives=TENTATIVES):
    """
    Comme telecharger_prix, mais avec des cours convertis en euros.
    Renvoie aussi les devises d'origine : (prix en euros, {titre: devise}).
    """
    prix = telecharger_prix(tickers, debut, fin, tentatives)
    devises = {t: devise(t) for t in tickers}
    a_convertir = sorted({SOUS_UNITES.get(d, (d, 1))[0] for d in devises.values()} - {"EUR"})
    if len(a_convertir) == 0:
        return prix, devises

    paires = [f"EUR{d}=X" for d in a_convertir]          # ex. EURUSD=X : dollars pour 1 €
    taux = _telecharger(paires, debut, fin, tentatives)
    if taux is None:
        raise ValueError("Impossible de récupérer les taux de change pour convertir en euros : "
                         f"{', '.join(paires)}. Réessaie dans quelques minutes.")
    if isinstance(taux, pd.Series):
        taux = taux.to_frame(name=paires[0])
    taux = taux.rename(columns=lambda paire: paire[3:6])  # "EURUSD=X" -> "USD"
    return convertir_en_euros(prix, devises, taux), devises


def calculer_rendements(prix, methode="simple"):
    """
    Calcule les rendements journaliers à partir des prix.

    methode = "simple" : r = P_t / P_(t-1) - 1
    methode = "log"    : r = ln(P_t / P_(t-1))
    """
    if methode == "simple":
        rendements = prix / prix.shift(1) - 1
    elif methode == "log":
        rendements = np.log(prix / prix.shift(1))
    else:
        raise ValueError("methode doit valoir 'simple' ou 'log'")
    return rendements.dropna()


def normaliser_poids(poids):
    """
    Transforme une liste de poids quelconques en poids qui somment à 1.
    Exemple : [2, 1, 1] devient [0.5, 0.25, 0.25].
    """
    poids = np.array(poids, dtype=float)
    if np.any(poids < 0):
        raise ValueError("Les poids doivent être positifs (pas de vente à découvert).")
    if poids.sum() == 0:
        raise ValueError("La somme des poids ne peut pas être nulle.")
    return poids / poids.sum()


def rendements_portefeuille(rendements, poids):
    """
    Calcule le rendement journalier du portefeuille :
    r_portefeuille = somme des (poids_i x rendement_i).

    rendements : DataFrame des rendements SIMPLES (une colonne par action)
    poids      : liste des poids, dans le même ordre que les colonnes
    """
    poids = normaliser_poids(poids)
    if len(poids) != rendements.shape[1]:
        raise ValueError("Il faut exactement un poids par action.")
    r_ptf = rendements @ poids          # produit matriciel
    r_ptf.name = "Portefeuille"
    return r_ptf


# ---------------------------------------------------------------------------
# Ce bloc ne s'exécute QUE si on lance ce fichier directement
# (python data.py). Il sert à tester le module.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tickers = ["BNP.PA", "AIR.PA", "TTE.PA"]     # LVMH, Airbus, TotalEnergies
    poids = [0.9, 0.05, 0.05]

    prix = telecharger_prix(tickers, debut="2020-01-01")
    print("Aperçu des prix :")
    print(prix.tail())                          # les 5 dernières lignes

    rendements = calculer_rendements(prix)
    r_ptf = rendements_portefeuille(rendements, poids)
    print("\nAperçu des rendements du portefeuille :")
    print(r_ptf.tail())
    print(f"\nRendement journalier moyen : {r_ptf.mean():.4%}")
    print(f"Volatilité journalière     : {r_ptf.std():.4%}")
