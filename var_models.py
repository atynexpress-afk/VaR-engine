"""
var_models.py
Calcul de la Value at Risk (VaR) et de l'Expected Shortfall (ES)
selon trois méthodes : historique, paramétrique et Monte Carlo.

Conventions utilisées dans tout le projet :
- alpha = niveau de confiance (ex. 0.99 pour 99 %)
- la VaR et l'ES sont des PERTES POSITIVES, exprimées en fraction de la
  valeur du portefeuille (0.025 signifie une perte de 2,5 %)
- les calculs se font à l'horizon 1 jour, puis on peut changer d'horizon
"""

import numpy as np
import pandas as pd
from scipy import stats

from data import normaliser_poids, rendements_portefeuille


# ---------------------------------------------------------------------------
# 1. VaR HISTORIQUE
# ---------------------------------------------------------------------------
def var_historique(r_ptf, alpha=0.99):
    """
    VaR historique : on suppose que le futur ressemblera au passé.
    On regarde les pertes réellement observées et on prend leur quantile.

    r_ptf : rendements journaliers du portefeuille
    Renvoie un dictionnaire {"VaR": ..., "ES": ...}
    """
    pertes = -np.asarray(r_ptf)           # perte = - rendement
    var = np.quantile(pertes, alpha)      # quantile à 99 % des pertes
    es = pertes[pertes >= var].mean()     # moyenne des pertes au-delà de la VaR
    return {"VaR": var, "ES": es}


# ---------------------------------------------------------------------------
# 2. VaR PARAMÉTRIQUE (méthode variance-covariance)
# ---------------------------------------------------------------------------
def var_parametrique(r_ptf, alpha=0.99, loi="normale", ddl=5):
    """
    VaR paramétrique : on suppose que les rendements suivent une loi connue,
    dont on estime la moyenne (mu) et l'écart-type (sigma).

    loi = "normale" : loi gaussienne
    loi = "student" : loi de Student à ddl degrés de liberté,
                      aux queues plus épaisses que la normale
    """
    mu = np.mean(r_ptf)
    sigma = np.std(r_ptf, ddof=1)         # ddof=1 : écart-type sans biais

    if loi == "normale":
        z = stats.norm.ppf(alpha)         # quantile de la loi normale (2,326 à 99 %)
        var = -mu + sigma * z
        es = -mu + sigma * stats.norm.pdf(z) / (1 - alpha)

    elif loi == "student":
        if ddl <= 2:
            raise ValueError("Il faut ddl > 2 pour que la variance existe.")
        # Une Student a une variance de ddl/(ddl-2) : on ajuste l'échelle
        # pour que la volatilité du modèle soit égale à sigma.
        echelle = sigma * np.sqrt((ddl - 2) / ddl)
        t = stats.t.ppf(alpha, ddl)       # quantile de la loi de Student
        var = -mu + echelle * t
        es = -mu + echelle * (stats.t.pdf(t, ddl) / (1 - alpha)) * (ddl + t**2) / (ddl - 1)

    else:
        raise ValueError("loi doit valoir 'normale' ou 'student'")

    return {"VaR": var, "ES": es}


# ---------------------------------------------------------------------------
# 3. VaR MONTE CARLO
# ---------------------------------------------------------------------------
def var_monte_carlo(rendements, poids, alpha=0.99, n_sim=10_000, graine=42):
    """
    VaR Monte Carlo : on simule un grand nombre de scénarios de rendements
    des actions, en respectant leurs volatilités ET leurs corrélations,
    puis on calcule la VaR sur les pertes simulées du portefeuille.

    rendements : DataFrame des rendements des actions (une colonne par action)
    poids      : poids du portefeuille
    n_sim      : nombre de scénarios simulés
    graine     : fixe le hasard pour obtenir toujours le même résultat
    """
    poids = normaliser_poids(poids)
    mu = rendements.mean().values         # vecteur des rendements moyens
    cov = rendements.cov().values         # matrice de variance-covariance

    # Décomposition de Cholesky : cov = L x L transposée.
    # L sert à transformer des variables indépendantes en variables corrélées.
    try:
        L = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        raise ValueError("Matrice de covariance non inversible : "
                         "vérifie qu'aucune action n'est en double.")

    rng = np.random.default_rng(graine)              # générateur aléatoire
    Z = rng.standard_normal((n_sim, len(poids)))     # tirages N(0,1) indépendants
    sim_actifs = mu + Z @ L.T                        # rendements simulés corrélés
    sim_ptf = sim_actifs @ poids                     # rendements simulés du portefeuille

    resultat = var_historique(sim_ptf, alpha)        # même calcul de quantile
    resultat["simulations"] = sim_ptf                # on garde les scénarios pour les graphiques
    return resultat


# ---------------------------------------------------------------------------
# 4. CHANGEMENT D'HORIZON
# ---------------------------------------------------------------------------
def changer_horizon(resultat, horizon):
    """
    Passe d'une VaR à 1 jour à une VaR à h jours avec la règle de la
    racine du temps : VaR(h) = VaR(1) x racine(h).
    Hypothèse : rendements indépendants et de même loi d'un jour à l'autre.
    """
    facteur = np.sqrt(horizon)
    return {"VaR": resultat["VaR"] * facteur, "ES": resultat["ES"] * facteur}


# ---------------------------------------------------------------------------
# 5. COMPARAISON DES MÉTHODES
# ---------------------------------------------------------------------------
def comparer_methodes(rendements, poids, alpha=0.99, horizon=1,
                      n_sim=10_000, ddl=5):
    """
    Calcule la VaR et l'ES avec toutes les méthodes et renvoie un tableau.
    """
    r_ptf = rendements_portefeuille(rendements, poids)

    resultats = {
        "Historique": var_historique(r_ptf, alpha),
        "Paramétrique normale": var_parametrique(r_ptf, alpha, "normale"),
        "Paramétrique Student": var_parametrique(r_ptf, alpha, "student", ddl),
        "Monte Carlo": var_monte_carlo(rendements, poids, alpha, n_sim),
    }

    lignes = {}
    for nom, res in resultats.items():
        lignes[nom] = changer_horizon(res, horizon)

    return pd.DataFrame(lignes).T     # .T : on met les méthodes en lignes


# ---------------------------------------------------------------------------
# Test du module : python var_models.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from data import telecharger_prix, calculer_rendements

    tickers = ["MC.PA", "AIR.PA", "TTE.PA"]
    poids = [0.4, 0.3, 0.3]
    montant = 1_000_000                   # valeur du portefeuille en euros

    prix = telecharger_prix(tickers, debut="2021-01-01")
    rendements = calculer_rendements(prix)

    tableau = comparer_methodes(rendements, poids, alpha=0.99, horizon=1)

    print("VaR et ES à 99 %, horizon 1 jour (en % du portefeuille) :")
    print((tableau * 100).round(2))
    print(f"\nEn euros, pour un portefeuille de {montant:,} € :")
    print((tableau * montant).round(0))
