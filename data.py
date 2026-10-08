"""
data.py
Module chargé de récupérer les données de marché et de construire le portefeuille.
Il ne fait AUCUN calcul de risque : il prépare seulement les données.
"""

import numpy as np
import pandas as pd
import yfinance as yf


def telecharger_prix(tickers, debut, fin=None):
    """
    Télécharge les prix de clôture ajustés d'une liste d'actions.

    Paramètres
    ----------
    tickers : liste de textes, ex. ["MC.PA", "AIR.PA"]
    debut   : date de début, ex. "2020-01-01"
    fin     : date de fin (None = jusqu'à aujourd'hui)

    Renvoie
    -------
    Un tableau (DataFrame) : une colonne par action, une ligne par jour.
    """
    donnees = yf.download(tickers, start=debut, end=fin,
                          auto_adjust=True, progress=False)
    prix = donnees["Close"]

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
        raise ValueError(f"Aucune donnée trouvée pour : {manquants}")

    prix = prix[tickers]    # on remet les colonnes dans l'ordre demandé
    prix = prix.dropna()    # on enlève les jours où une action n'a pas coté
    return prix


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
