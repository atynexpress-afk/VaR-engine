"""
app.py
Application interactive de mesure du risque de marché.
Elle assemble les modules du projet :
  data.py         -> données et portefeuille
  var_models.py   -> VaR et Expected Shortfall
  backtesting.py  -> backtesting et stress tests
  definitions.py  -> définitions affichées par les icônes d'aide
  style.py        -> apparence (couleurs, CSS, modèle des graphiques)
  formats.py      -> mise en forme des nombres à la française
  guide.py        -> guide de démarrage affiché à l'ouverture
  onglets.py      -> contenu des quatre onglets

Lancement dans le terminal :  streamlit run app.py
"""

import datetime

import numpy as np
import pandas as pd
import streamlit as st

from data import telecharger_prix, calculer_rendements, rendements_portefeuille, normaliser_poids
from var_models import (var_historique, var_parametrique, var_monte_carlo, var_ewma,
                        var_historique_filtree, changer_horizon, LAMBDA_RISKMETRICS)
from definitions import DEFINITIONS as D      # D["var"] renvoie la définition de la VaR
from formats import euros, pct
from style import appliquer_style, pastilles
from guide import afficher_guide, rouvrir_guide
from onglets import onglet_portefeuille, onglet_var_es, onglet_backtesting, onglet_stress_tests


# =============================================================================
# 0. CONFIGURATION GÉNÉRALE
# =============================================================================
st.set_page_config(page_title="VaR Engine", layout="wide")
appliquer_style()
afficher_guide()          # guide de démarrage, tant qu'il n'a pas été vu ou passé

MAX_ACTIONS = 8

# Principales actions du CAC 40 : nom affiché -> code Yahoo Finance
ACTIONS = {
    "LVMH": "MC.PA", "Airbus": "AIR.PA", "TotalEnergies": "TTE.PA",
    "BNP Paribas": "BNP.PA", "Sanofi": "SAN.PA", "L'Oréal": "OR.PA",
    "Schneider Electric": "SU.PA", "Air Liquide": "AI.PA", "AXA": "CS.PA",
    "Société Générale": "GLE.PA", "Crédit Agricole": "ACA.PA", "Hermès": "RMS.PA",
    "Kering": "KER.PA", "Safran": "SAF.PA", "Vinci": "DG.PA", "Danone": "BN.PA",
    "Orange": "ORA.PA", "Capgemini": "CAP.PA", "Renault": "RNO.PA",
    "EssilorLuxottica": "EL.PA",
}

NOMS = {code: nom for nom, code in ACTIONS.items()}   # code Yahoo -> nom affiché

METHODES = ["Historique", "Paramétrique normale", "Paramétrique Student", "Monte Carlo",
            "EWMA (RiskMetrics)", "Historique filtrée (FHS)"]


def nom_titre(ticker):
    """Nom lisible d'un titre : 'MC.PA' -> 'LVMH' ; un ticker inconnu reste tel quel."""
    return NOMS.get(ticker, ticker)


def reequilibrer_poids(ticker_modifie, tickers):
    """
    Appelée automatiquement quand l'utilisateur modifie le poids d'une action.
    Les autres poids sont ajustés pour que le total reste égal à 100 %,
    en conservant leurs proportions entre eux.

    Exemple avec 3 actions à 50 / 30 / 20 : si la 1re passe à 70, il reste 30 %
    à répartir entre les deux autres dans le rapport 30:20, soit 18 / 12.
    """
    etat = st.session_state                          # mémoire de l'application
    nouveau = min(max(etat[f"poids_{ticker_modifie}"], 0.0), 100.0)
    autres = [t for t in tickers if t != ticker_modifie]
    if len(autres) == 0:                             # une seule action : 100 %
        etat[f"poids_{ticker_modifie}"] = 100.0
        return

    reste = 100.0 - nouveau
    total_autres = sum(etat[f"poids_{t}"] for t in autres)
    for t in autres:
        if total_autres > 0:
            part = etat[f"poids_{t}"] / total_autres   # proportion conservée
        else:
            part = 1 / len(autres)                     # sinon, partage égal
        etat[f"poids_{t}"] = round(reste * part, 1)

    # Les arrondis peuvent laisser un écart de 0,1 : on le corrige sur le plus gros poids
    ecart = round(100.0 - nouveau - sum(etat[f"poids_{t}"] for t in autres), 1)
    plus_gros = max(autres, key=lambda t: etat[f"poids_{t}"])
    etat[f"poids_{plus_gros}"] = round(etat[f"poids_{plus_gros}"] + ecart, 1)


# =============================================================================
# 1. TÉLÉCHARGEMENT MIS EN CACHE
# Streamlit relance tout le script à chaque clic. Le cache évite de
# re-télécharger les données si les paramètres n'ont pas changé : le résultat
# est gardé en mémoire. (Les calculs longs des onglets sont dans onglets.py.)
# =============================================================================
@st.cache_data(show_spinner="Téléchargement des prix…")
def charger_prix(tickers, debut, fin):
    return telecharger_prix(list(tickers), debut, fin)



# =============================================================================
# 2. BARRE LATÉRALE : TOUS LES PARAMÈTRES
# Le paramètre help=... ajoute l'icône d'aide qui affiche la définition.
# =============================================================================
st.sidebar.title("VaR Engine")
st.sidebar.button("Revoir le guide", key="revoir_guide", on_click=rouvrir_guide,
                  help="Rouvre le guide de démarrage pour les débutants.")

# ---- 2.1 Portefeuille ----
st.sidebar.header("Portefeuille")
noms = st.sidebar.multiselect("Actions du CAC 40", options=list(ACTIONS),
                              default=["LVMH", "Airbus", "TotalEnergies"], help=D["actions"])
autres = st.sidebar.text_input("Autres tickers Yahoo Finance (séparés par des virgules)",
                               placeholder="ex. AAPL, MSFT, ^FCHI", help=D["tickers"])

tickers = [ACTIONS[nom] for nom in noms]
for t in autres.split(","):
    t = t.strip().upper()                 # enlève les espaces, met en majuscules
    if t != "" and t not in tickers:
        tickers.append(t)

if len(tickers) == 0:
    st.info("Choisis au moins une action dans la barre latérale.")
    st.stop()
if len(tickers) > MAX_ACTIONS:
    st.warning(f"Maximum {MAX_ACTIONS} actions : seules les {MAX_ACTIONS} premières sont gardées.")
    tickers = tickers[:MAX_ACTIONS]

# Si la liste des actions a changé, on repart de poids égaux.
# st.session_state est la « mémoire » de Streamlit : elle survit aux relances du script.
if st.session_state.get("tickers_precedents") != tickers:
    st.session_state["tickers_precedents"] = tickers
    poids_egal = round(100 / len(tickers), 1)
    for t in tickers:
        st.session_state[f"poids_{t}"] = poids_egal
    # correction de l'arrondi (ex. 3 x 33,3 = 99,9 -> la 1re action passe à 33,4)
    st.session_state[f"poids_{tickers[0]}"] = round(100 - poids_egal * (len(tickers) - 1), 1)

st.sidebar.caption("Poids de chaque action : les autres s'ajustent pour que le total reste à 100 %")
poids_bruts = []
for t in tickers:
    # key relie le champ à st.session_state ; on_change appelle la fonction de
    # rééquilibrage dès que l'utilisateur modifie la valeur.
    p = st.sidebar.number_input(f"Poids {nom_titre(t)} (%)", min_value=0.0, max_value=100.0,
                                step=5.0, format="%.1f", key=f"poids_{t}",
                                on_change=reequilibrer_poids, args=(t, tickers),
                                help=D["poids"])
    poids_bruts.append(p)

if sum(poids_bruts) == 0:
    st.error("La somme des poids ne peut pas être nulle.")
    st.stop()
poids = normaliser_poids(poids_bruts)

montant = st.sidebar.number_input("Valeur du portefeuille (€)", min_value=1_000,
                                  value=1_000_000, step=100_000, help=D["montant"])
debut = st.sidebar.date_input("Date de début", value=datetime.date(2018, 1, 1),
                              format="DD/MM/YYYY", help=D["periode"])
fin = st.sidebar.date_input("Date de fin", value=datetime.date.today(),
                            format="DD/MM/YYYY", help=D["periode"])
if debut >= fin:
    st.error("La date de début doit être antérieure à la date de fin.")
    st.stop()

# ---- 2.2 Paramètres de risque ----
st.sidebar.header("Mesure du risque")
alpha = st.sidebar.select_slider("Niveau de confiance",
                                 options=[0.90, 0.95, 0.975, 0.99, 0.995], value=0.99,
                                 format_func=lambda x: pct(x, 1), help=D["niveau_confiance"])
horizon = st.sidebar.slider("Horizon (jours)", min_value=1, max_value=20, value=1,
                            help=D["horizon"])
methode_principale = st.sidebar.selectbox("Méthode mise en avant", METHODES, help=D["methode"])

# ---- 2.3 Paramètres avancés ----
# Réglages pour spécialistes, repliés par défaut pour ne pas intimider les débutants.
# Dans un expander, on écrit st.slider (et non st.sidebar.slider) : le
# « with » place automatiquement les champs à l'intérieur du bloc.
with st.sidebar.expander("Paramètres avancés"):
    ddl = st.slider("Degrés de liberté (loi de Student)", min_value=3, max_value=30, value=5,
                    help=D["ddl"])
    n_sim = st.select_slider("Nombre de simulations Monte Carlo",
                             options=[1_000, 5_000, 10_000, 50_000, 100_000], value=10_000,
                             format_func=lambda x: f"{x:,}".replace(",", " "), help=D["n_sim"])
    graine = st.number_input("Graine aléatoire (Monte Carlo)", min_value=0, max_value=10_000,
                             value=42, help=D["graine"])
    lam = st.slider("Facteur de lissage λ (EWMA et FHS)", min_value=0.85, max_value=0.99,
                    value=LAMBDA_RISKMETRICS, step=0.01, help=D["lambda"])
    fenetre = st.slider("Fenêtre du backtesting (jours)", min_value=100, max_value=750,
                        value=250, step=50, help=D["fenetre"])


# =============================================================================
# 3. DONNÉES ET CALCULS
# =============================================================================
try:
    prix = charger_prix(tuple(tickers), debut, fin)
except ValueError as erreur:
    st.error(str(erreur))
    st.stop()

# Les colonnes portent désormais les noms lisibles (LVMH plutôt que MC.PA) :
# tableaux et graphiques les reprennent automatiquement.
noms_titres = [nom_titre(t) for t in tickers]
prix.columns = noms_titres

if len(prix) < 60:
    st.error("Moins de 60 jours de données : élargis la période.")
    st.stop()

rendements = calculer_rendements(prix)
r_ptf = rendements_portefeuille(rendements, poids)

try:
    resultats_1j = {
        "Historique": var_historique(r_ptf, alpha),
        "Paramétrique normale": var_parametrique(r_ptf, alpha, "normale"),
        "Paramétrique Student": var_parametrique(r_ptf, alpha, "student", ddl),
        "Monte Carlo": var_monte_carlo(rendements, poids, alpha, n_sim, graine),
        "EWMA (RiskMetrics)": var_ewma(r_ptf, alpha, lam),
        "Historique filtrée (FHS)": var_historique_filtree(r_ptf, alpha, lam),
    }
except ValueError as erreur:
    st.error(str(erreur))
    st.stop()

# Passage à l'horizon choisi
resultats = {}
for nom, res in resultats_1j.items():
    resultats[nom] = changer_horizon(res, horizon)
tableau = pd.DataFrame(resultats).T          # lignes = méthodes, colonnes = VaR, ES
principal = resultats[methode_principale]


# =============================================================================
# 4. EN-TÊTE : TITRE, PASTILLES DE PARAMÈTRES ET CARTES DE SYNTHÈSE
# =============================================================================
st.title("Mesure du risque de marché")
st.markdown('<p class="sous-titre">VaR et Expected Shortfall par six méthodes, '
            'backtesting réglementaire et stress tests.</p>', unsafe_allow_html=True)
pastilles([
    ("Méthode", methode_principale),
    ("Confiance", pct(alpha, 1)),
    ("Horizon", f"{horizon} j"),
    ("Titres", len(tickers)),
    ("Période", f"{debut:%d/%m/%Y} → {fin:%d/%m/%Y}"),
    ("Portefeuille", euros(montant)),
])

c1, c2, c3, c4 = st.columns(4)
# delta = petite pastille sous la valeur ; delta_color="off" et delta_arrow="off"
# l'affichent en neutre, sans flèche ni couleur de hausse ou de baisse.
with c1.container(key="carte_kpi_var"):
    st.metric(f"VaR {pct(alpha, 1)} · {horizon} j", euros(principal["VaR"] * montant),
              delta=f"{pct(principal['VaR'])} du portefeuille", delta_color="off",
              delta_arrow="off", help=D["var"])
with c2.container(key="carte_kpi_es"):
    st.metric(f"Expected Shortfall · {horizon} j", euros(principal["ES"] * montant),
              delta=f"{pct(principal['ES'])} du portefeuille", delta_color="off",
              delta_arrow="off", help=D["es"])
with c3.container(key="carte_kpi_vol"):
    st.metric("Volatilité annualisée", pct(r_ptf.std() * np.sqrt(252), 1),
              delta=f"{pct(r_ptf.std())} par jour", delta_color="off", delta_arrow="off",
              help=D["volatilite"])
with c4.container(key="carte_kpi_jours"):
    st.metric("Jours d'historique", f"{len(r_ptf):,}".replace(",", " "),
              delta=f"depuis le {r_ptf.index[0]:%d/%m/%Y}", delta_color="off", delta_arrow="off",
              help=D["jours"])

st.write("")
onglet_ptf, onglet_var, onglet_bt, onglet_stress = st.tabs(
    ["Portefeuille", "VaR & ES", "Backtesting", "Stress tests"])


# =============================================================================
# 5. ONGLETS (leur contenu est dans onglets.py)
# =============================================================================
with onglet_ptf:
    onglet_portefeuille(prix, rendements, r_ptf, poids)
with onglet_var:
    onglet_var_es(resultats_1j, tableau, r_ptf, methode_principale, horizon, montant)
with onglet_bt:
    onglet_backtesting(r_ptf, alpha, fenetre, ddl, lam)
with onglet_stress:
    onglet_stress_tests(tickers, noms_titres, poids, montant, resultats_1j[methode_principale])

st.write("")
st.caption("Projet pédagogique — données Yahoo Finance. Ne constitue pas un outil de gestion "
           "des risques en production.")
