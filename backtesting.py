"""
backtesting.py
Vérifie si une VaR aurait été fiable dans le passé (backtesting)
et mesure les pertes du portefeuille dans des crises historiques (stress tests).

Principe du backtesting :
chaque jour, on calcule la VaR avec les données des jours PRÉCÉDENTS uniquement,
puis on regarde la perte réelle du lendemain. Si la perte dépasse la VaR,
on parle d'« exception ». Avec une VaR à 99 %, on attend environ 1 exception
tous les 100 jours : beaucoup plus signifie que le modèle sous-estime le risque.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import xlogy

from data import normaliser_poids, telecharger_prix_euros
from var_models import volatilite_ewma, LAMBDA_RISKMETRICS


# ---------------------------------------------------------------------------
# 1. VaR GLISSANTE ET EXCEPTIONS
# ---------------------------------------------------------------------------
def var_glissante(r_ptf, alpha=0.99, fenetre=250, methode="historique", ddl=5,
                  lam=LAMBDA_RISKMETRICS):
    """
    Calcule, pour chaque jour t, la VaR estimée sur les `fenetre` jours
    précédents (de t-fenetre à t-1), puis la compare à la perte du jour t.

    methode : "historique", "normale", "student", "ewma" ou "fhs"
    Pour "ewma" et "fhs", la volatilité EWMA est calculée une seule fois sur
    toute la série : sigma[t] n'utilise que les rendements jusqu'à t-1,
    il n'y a donc pas de regard vers le futur.
    Renvoie un DataFrame avec une ligne par jour :
      Perte, VaR, ES (prévus la veille), Exception (True si la perte a dépassé la VaR)
    """
    r_ptf = pd.Series(r_ptf)
    if len(r_ptf) <= fenetre:
        raise ValueError("Pas assez de données : il faut plus de jours que la taille de la fenêtre.")

    # rolling(fenetre) calcule une statistique sur les `fenetre` derniers jours,
    # pour tous les jours d'un coup (bien plus rapide qu'une boucle Python).
    # shift(1) décale d'un jour : la VaR du jour t n'utilise que les jours jusqu'à t-1.
    def glissant(serie):
        return serie.rolling(fenetre)

    def es_empirique(pertes):
        """ES historique d'une fenêtre : moyenne des pertes au-delà de leur quantile."""
        return pertes[pertes >= np.quantile(pertes, alpha)].mean()

    if methode == "historique":
        var = glissant(-r_ptf).quantile(alpha).shift(1)
        es = glissant(-r_ptf).apply(es_empirique, raw=True).shift(1)
    elif methode in ("normale", "student"):
        mu = glissant(r_ptf).mean().shift(1)
        sigma = glissant(r_ptf).std().shift(1)          # écart-type sans biais (ddof=1)
        if methode == "normale":
            z = stats.norm.ppf(alpha)
            var = -mu + sigma * z
            es = -mu + sigma * stats.norm.pdf(z) / (1 - alpha)
        else:
            if ddl <= 2:
                raise ValueError("Il faut ddl > 2 pour que la variance existe.")
            echelle = sigma * np.sqrt((ddl - 2) / ddl)
            t = stats.t.ppf(alpha, ddl)
            var = -mu + echelle * t
            es = -mu + echelle * stats.t.pdf(t, ddl) / (1 - alpha) * (ddl + t ** 2) / (ddl - 1)
    elif methode in ("ewma", "fhs"):
        sigma = pd.Series(volatilite_ewma(r_ptf, lam)[:-1], index=r_ptf.index)
        if methode == "ewma":
            z = stats.norm.ppf(alpha)
            var = sigma * z
            es = sigma * stats.norm.pdf(z) / (1 - alpha)
        else:
            chocs = r_ptf / sigma                         # rendements standardisés
            var = sigma * glissant(-chocs).quantile(alpha).shift(1)
            es = sigma * glissant(-chocs).apply(es_empirique, raw=True).shift(1)
    else:
        raise ValueError("methode doit valoir 'historique', 'normale', 'student', "
                         "'ewma' ou 'fhs'")

    resultat = pd.DataFrame({"Perte": -r_ptf, "VaR": var, "ES": es}).iloc[fenetre:]
    resultat["Exception"] = resultat["Perte"] > resultat["VaR"]
    return resultat


# ---------------------------------------------------------------------------
# 2. TEST DE KUPIEC (couverture non conditionnelle)
# ---------------------------------------------------------------------------
def test_kupiec(exceptions, alpha=0.99):
    """
    Question : le NOMBRE d'exceptions est-il compatible avec le niveau de confiance ?

    H0 : la probabilité d'exception est bien p = 1 - alpha.
    Statistique du rapport de vraisemblance, qui suit un Khi-deux à 1 degré
    de liberté sous H0 :
        LR = -2 ln[ (1-p)^(n-x) p^x ] + 2 ln[ (1-x/n)^(n-x) (x/n)^x ]
    """
    exceptions = np.asarray(exceptions, dtype=bool)
    n = len(exceptions)                 # nombre de jours testés
    x = int(exceptions.sum())           # nombre d'exceptions observées
    p = 1 - alpha                       # probabilité théorique d'exception
    p_obs = x / n                       # fréquence observée

    # xlogy(a, b) calcule a x ln(b) en gérant le cas 0 x ln(0) = 0
    log_l0 = xlogy(n - x, 1 - p) + xlogy(x, p)
    log_l1 = xlogy(n - x, 1 - p_obs) + xlogy(x, p_obs)
    lr = -2 * (log_l0 - log_l1)
    p_value = 1 - stats.chi2.cdf(lr, df=1)

    return {
        "Jours testés": n,
        "Exceptions observées": x,
        "Exceptions attendues": n * p,
        "Statistique LR": lr,
        "p-value": p_value,
        "Modèle rejeté (5 %)": p_value < 0.05,
    }


# ---------------------------------------------------------------------------
# 3. TEST DE CHRISTOFFERSEN (indépendance et couverture conditionnelle)
# ---------------------------------------------------------------------------
def test_christoffersen(exceptions, alpha=0.99):
    """
    Question : les exceptions arrivent-elles par GROUPES ?
    Un bon modèle a des exceptions dispersées dans le temps. Si une exception
    est souvent suivie d'une autre, le modèle réagit trop lentement aux crises.

    On compte les transitions entre deux jours consécutifs :
      n00 : pas d'exception -> pas d'exception
      n01 : pas d'exception -> exception
      n10 : exception -> pas d'exception
      n11 : exception -> exception
    """
    e = np.asarray(exceptions, dtype=int)
    hier, aujourdhui = e[:-1], e[1:]
    n00 = int(np.sum((hier == 0) & (aujourdhui == 0)))
    n01 = int(np.sum((hier == 0) & (aujourdhui == 1)))
    n10 = int(np.sum((hier == 1) & (aujourdhui == 0)))
    n11 = int(np.sum((hier == 1) & (aujourdhui == 1)))

    # Probabilité d'exception sachant l'état de la veille
    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    # Probabilité d'exception sans tenir compte de la veille
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    log_l_indep = xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi)
    log_l_markov = (xlogy(n00, 1 - pi01) + xlogy(n01, pi01)
                    + xlogy(n10, 1 - pi11) + xlogy(n11, pi11))
    lr_ind = -2 * (log_l_indep - log_l_markov)
    p_value_ind = 1 - stats.chi2.cdf(lr_ind, df=1)

    # Couverture conditionnelle = Kupiec + indépendance (Khi-deux à 2 ddl)
    lr_uc = test_kupiec(exceptions, alpha)["Statistique LR"]
    lr_cc = lr_uc + lr_ind
    p_value_cc = 1 - stats.chi2.cdf(lr_cc, df=2)

    return {
        "Exceptions consécutives (n11)": n11,
        "P(exception | exception la veille)": pi11,
        "P(exception | pas d'exception la veille)": pi01,
        "Statistique LR indépendance": lr_ind,
        "p-value indépendance": p_value_ind,
        "Statistique LR couverture conditionnelle": lr_cc,
        "p-value couverture conditionnelle": p_value_cc,
        "Modèle rejeté (5 %)": p_value_cc < 0.05,
    }


# ---------------------------------------------------------------------------
# 4. BACKTEST DE L'EXPECTED SHORTFALL (Acerbi et Szekely, 2014)
# ---------------------------------------------------------------------------
SEUILS_ACERBI_SZEKELY = {"Orange": -0.70, "Rouge": -1.80}   # risque 5 % et 0,01 %


def test_acerbi_szekely(bt, alpha=0.99):
    """
    Question : quand la VaR est dépassée, la perte est-elle en moyenne égale à l'ES prévue ?
    Le test de Kupiec compte les dépassements ; celui-ci mesure aussi leur AMPLEUR.

    Statistique Z2 (« test 2 » d'Acerbi et Szekely) :
        Z2 = 1 - somme( Perte_t / ES_t  sur les jours d'exception ) / (T x (1 - alpha))
    Si le modèle est juste, Z2 vaut 0 en moyenne. Z2 négatif : les pertes extrêmes
    sont plus fortes ou plus fréquentes que prévu, l'ES sous-estime le risque.
    Seuils publiés par les auteurs, très stables d'une loi à l'autre :
      Z2 > -0,70 : zone verte ; -1,80 < Z2 <= -0,70 : orange ; Z2 <= -1,80 : rouge.

    bt : résultat de var_glissante (colonnes Perte, ES, Exception)
    """
    T = len(bt)
    exceptions = bt[bt["Exception"]]
    z2 = 1 - (exceptions["Perte"] / exceptions["ES"]).sum() / (T * (1 - alpha))
    if z2 > SEUILS_ACERBI_SZEKELY["Orange"]:
        zone = "Verte"
    elif z2 > SEUILS_ACERBI_SZEKELY["Rouge"]:
        zone = "Orange"
    else:
        zone = "Rouge"
    return {"Z2": z2, "Zone": zone, "Modèle rejeté (5 %)": zone != "Verte"}


# ---------------------------------------------------------------------------
# 5. FEUX TRICOLORES DE BÂLE
# ---------------------------------------------------------------------------
def feux_bale(exceptions):
    """
    Règle du régulateur pour une VaR à 99 % sur les 250 derniers jours :
      0 à 4 exceptions  -> zone verte  (modèle accepté)
      5 à 9 exceptions  -> zone orange (capital majoré)
      10 ou plus        -> zone rouge  (modèle remis en cause)
    """
    derniers = np.asarray(exceptions, dtype=bool)[-250:]
    x = int(derniers.sum())
    if x <= 4:
        zone = "Verte"
    elif x <= 9:
        zone = "Orange"
    else:
        zone = "Rouge"
    return {"Exceptions sur 250 jours": x, "Zone": zone}


# ---------------------------------------------------------------------------
# 6. STRESS TESTS
# ---------------------------------------------------------------------------
# Crises historiques : (date de début, date de fin)
SCENARIOS_HISTORIQUES = {
    "Faillite de Lehman (2008)": ("2008-09-01", "2008-11-21"),
    "Crise de la dette européenne (2011)": ("2011-07-01", "2011-09-23"),
    "Krach Covid (2020)": ("2020-02-19", "2020-03-18"),
    "Invasion de l'Ukraine (2022)": ("2022-02-10", "2022-03-08"),
}


def stress_sur_prix(prix, poids):
    """
    Perte du portefeuille sur une période, à partir des prix de chaque action.
    On suppose qu'on achète au premier jour et qu'on ne touche plus à rien :
      valeur finale = somme des poids_i x (prix final_i / prix initial_i)
    Renvoie la perte totale et la pire journée (en % du portefeuille).
    """
    poids = normaliser_poids(poids)
    evolution = prix / prix.iloc[0]                 # chaque action démarre à 1
    valeur_ptf = evolution @ poids                  # valeur du portefeuille chaque jour
    perte_totale = 1 - valeur_ptf.iloc[-1]
    pire_jour = -(valeur_ptf / valeur_ptf.shift(1) - 1).min()
    return {"Perte totale": perte_totale, "Pire journée": pire_jour}


def stress_historiques(tickers, poids, scenarios=SCENARIOS_HISTORIQUES):
    """
    Applique au portefeuille actuel chaque crise historique.
    Si une action n'existait pas encore à l'époque, le scénario est ignoré.
    Un seul essai de téléchargement : une absence de données est ici normale
    (action pas encore cotée), inutile d'attendre pour réessayer.
    """
    lignes = {}
    for nom, (debut, fin) in scenarios.items():
        try:
            prix, _ = telecharger_prix_euros(tickers, debut=debut, fin=fin, tentatives=1)
            lignes[nom] = stress_sur_prix(prix, poids)
        except ValueError:
            lignes[nom] = {"Perte totale": np.nan, "Pire journée": np.nan}
    return pd.DataFrame(lignes).T


def stress_hypothetique(poids, chocs):
    """
    Scénario imaginé par l'utilisateur : un choc en % sur chaque action.
    Exemple : chocs = [-0.20, -0.10, -0.30]  ->  perte = somme des poids x chocs
    """
    poids = normaliser_poids(poids)
    chocs = np.asarray(chocs, dtype=float)
    if len(chocs) != len(poids):
        raise ValueError("Il faut exactement un choc par action.")
    return -float(chocs @ poids)


# ---------------------------------------------------------------------------
# Test du module : python backtesting.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from data import calculer_rendements, rendements_portefeuille

    tickers = ["MC.PA", "AIR.PA", "TTE.PA"]
    poids = [0.4, 0.3, 0.3]

    prix, _ = telecharger_prix_euros(tickers, debut="2018-01-01")
    r_ptf = rendements_portefeuille(calculer_rendements(prix), poids)

    for methode in ["historique", "normale", "student", "ewma", "fhs"]:
        bt = var_glissante(r_ptf, alpha=0.99, fenetre=250, methode=methode)
        k = test_kupiec(bt["Exception"], 0.99)
        c = test_christoffersen(bt["Exception"], 0.99)
        f = feux_bale(bt["Exception"])
        print(f"\n=== VaR {methode} ===")
        print(f"Exceptions : {k['Exceptions observées']} observées "
              f"pour {k['Exceptions attendues']:.1f} attendues")
        print(f"Kupiec        : p-value = {k['p-value']:.3f} "
              f"-> {'REJETÉ' if k['Modèle rejeté (5 %)'] else 'accepté'}")
        print(f"Christoffersen: p-value = {c['p-value couverture conditionnelle']:.3f} "
              f"-> {'REJETÉ' if c['Modèle rejeté (5 %)'] else 'accepté'}")
        print(f"Bâle          : {f['Exceptions sur 250 jours']} exceptions -> zone {f['Zone']}")

    print("\n=== Stress tests historiques ===")
    print((stress_historiques(tickers, poids) * 100).round(2))
    print(f"\nChoc hypothétique (-20 %, -30 %, -10 %) : "
          f"perte de {stress_hypothetique(poids, [-0.2, -0.3, -0.1]):.2%}")
