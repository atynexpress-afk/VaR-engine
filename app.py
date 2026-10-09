"""
app.py
Application interactive de mesure du risque de marché.
Elle assemble les modules du projet :
  data.py         -> données et portefeuille
  var_models.py   -> VaR et Expected Shortfall
  backtesting.py  -> backtesting et stress tests
  definitions.py  -> définitions affichées par les icônes d'aide
  style.py        -> apparence (couleurs, CSS, modèle des graphiques)
  guide.py        -> guide de démarrage affiché à l'ouverture

Lancement dans le terminal :  streamlit run app.py
"""

import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from data import telecharger_prix, calculer_rendements, rendements_portefeuille, normaliser_poids
from var_models import var_historique, var_parametrique, var_monte_carlo, changer_horizon
from backtesting import (var_glissante, test_kupiec, test_christoffersen, feux_bale,
                         stress_historiques, stress_hypothetique)
from definitions import DEFINITIONS as D      # D["var"] renvoie la définition de la VaR
from style import (appliquer_style, afficher, pastilles, barre_exceptions,
                   COULEURS, COULEUR_PORTEFEUILLE, COULEUR_PERTES, COULEUR_EXCEPTION, ACCENT)
from guide import afficher_guide, rouvrir_guide


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

METHODES = ["Historique", "Paramétrique normale", "Paramétrique Student", "Monte Carlo"]


def euros(x):
    """Formate un nombre en euros avec des espaces : 1234567 -> '1 234 567 €'."""
    return f"{x:,.0f} €".replace(",", " ")


def pct(x, decimales=2):
    """Formate un nombre en pourcentage à la française : 0.0235 -> '2,35 %'."""
    return f"{x * 100:.{decimales}f} %".replace(".", ",")


def colonne(definition):
    """Ajoute une icône d'aide à l'en-tête d'une colonne de tableau."""
    return st.column_config.Column(help=definition)


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
# 1. FONCTIONS MISES EN CACHE
# Streamlit relance tout le script à chaque clic. Le cache évite de
# re-télécharger les données ou de refaire un calcul long si ses paramètres
# n'ont pas changé : le résultat est gardé en mémoire.
# =============================================================================
@st.cache_data(show_spinner="Téléchargement des prix…")
def charger_prix(tickers, debut, fin):
    return telecharger_prix(list(tickers), debut, fin)


@st.cache_data(show_spinner="Backtesting en cours…")
def lancer_backtest(r_ptf, alpha, fenetre, methode, ddl):
    return var_glissante(r_ptf, alpha, fenetre, methode, ddl)


@st.cache_data(show_spinner="Téléchargement des crises historiques…")
def lancer_stress(tickers, poids):
    return stress_historiques(list(tickers), list(poids))


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
    p = st.sidebar.number_input(f"Poids {t} (%)", min_value=0.0, max_value=100.0,
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
debut = st.sidebar.date_input("Date de début", value=datetime.date(2018, 1, 1), help=D["periode"])
fin = st.sidebar.date_input("Date de fin", value=datetime.date.today(), help=D["periode"])
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
ddl = st.sidebar.slider("Degrés de liberté (loi de Student)", min_value=3, max_value=30, value=5,
                        help=D["ddl"])
n_sim = st.sidebar.select_slider("Nombre de simulations Monte Carlo",
                                 options=[1_000, 5_000, 10_000, 50_000, 100_000], value=10_000,
                                 format_func=lambda x: f"{x:,}".replace(",", " "), help=D["n_sim"])
graine = st.sidebar.number_input("Graine aléatoire (Monte Carlo)", min_value=0,
                                 max_value=10_000, value=42, help=D["graine"])

# ---- 2.3 Backtesting ----
st.sidebar.header("Backtesting")
fenetre = st.sidebar.slider("Fenêtre d'estimation (jours)", min_value=100, max_value=750,
                            value=250, step=50, help=D["fenetre"])


# =============================================================================
# 3. DONNÉES ET CALCULS
# =============================================================================
try:
    prix = charger_prix(tuple(tickers), debut, fin)
except ValueError as erreur:
    st.error(str(erreur))
    st.stop()

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
st.markdown('<p class="sous-titre">VaR et Expected Shortfall par trois méthodes, '
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
# 5. ONGLET PORTEFEUILLE
# =============================================================================
with onglet_ptf:
    with st.container(key="carte_base100"):
        st.subheader("Évolution des prix (base 100)", help=D["base100"])
        base100 = prix / prix.iloc[0] * 100
        fig = go.Figure()
        for i, t in enumerate(tickers):
            fig.add_trace(go.Scatter(x=base100.index, y=base100[t], name=t, mode="lines",
                                     line=dict(width=1.5, color=COULEURS[i], shape="spline")))
        fig.add_trace(go.Scatter(x=base100.index, y=base100 @ poids, name="Portefeuille",
                                 mode="lines", line=dict(width=3, color=COULEUR_PORTEFEUILLE,
                                                         shape="spline")))
        fig.update_layout(hovermode="x unified", height=400)
        afficher(fig)

    col_g, col_d = st.columns(2)
    with col_g.container(key="carte_stats"):
        st.subheader("Statistiques annualisées", help=D["stats_annuelles"])
        stats_actifs = pd.DataFrame({
            "Poids": poids,
            "Rendement annuel": rendements.mean().values * 252,
            "Volatilité annuelle": rendements.std().values * np.sqrt(252),
        }, index=tickers)
        stats_actifs.loc["Portefeuille"] = [1.0, r_ptf.mean() * 252, r_ptf.std() * np.sqrt(252)]
        st.dataframe(stats_actifs.style.format(lambda x: pct(x, 1)), column_config={
            "Poids": colonne(D["poids"]),
            "Rendement annuel": colonne(D["rendement_annuel"]),
            "Volatilité annuelle": colonne(D["volatilite"]),
        })
    with col_d.container(key="carte_correlation"):
        st.subheader("Matrice de corrélation", help=D["correlation"])
        if len(tickers) > 1:
            fig = px.imshow(rendements.corr(), text_auto=".2f", zmin=-1, zmax=1,
                            color_continuous_scale=[[0, COULEURS[0]], [0.5, "#f1f2f6"],
                                                    [1, COULEURS[1]]])
            fig.update_layout(height=340, coloraxis_showscale=False)
            afficher(fig)
        else:
            st.info("Ajoute au moins deux actions pour voir les corrélations.")


# =============================================================================
# 6. ONGLET VaR & ES
# =============================================================================
with onglet_var:
    col_g, col_d = st.columns([1.1, 1])
    with col_g.container(key="carte_comparaison"):
        st.subheader(f"Comparaison des méthodes · horizon {horizon} j", help=D["methode"])
        affichage = pd.DataFrame({
            "VaR (%)": tableau["VaR"], "ES (%)": tableau["ES"],
            "VaR (€)": tableau["VaR"] * montant, "ES (€)": tableau["ES"] * montant,
        })
        st.dataframe(affichage.style.format({"VaR (%)": pct, "ES (%)": pct,
                                             "VaR (€)": euros, "ES (€)": euros}),
                     column_config={"VaR (%)": colonne(D["var"]), "ES (%)": colonne(D["es"]),
                                    "VaR (€)": colonne(D["var"]), "ES (€)": colonne(D["es"])})
    with col_d.container(key="carte_barres"):
        st.subheader("VaR et ES par méthode", help=D["es"])
        # Format « long » pour Plotly : une ligne par (méthode, mesure)
        long = (tableau * montant).reset_index().melt(id_vars="index", var_name="Mesure",
                                                     value_name="Perte (€)")
        # <br> force un retour à la ligne dans les libellés trop longs
        long["index"] = long["index"].str.replace("Paramétrique ", "Paramétrique<br>")
        fig = px.bar(long, x="index", y="Perte (€)", color="Mesure", barmode="group",
                     color_discrete_sequence=COULEURS[:2], labels={"index": "", "Perte (€)": ""})
        fig.update_layout(height=300, bargap=0.35, bargroupgap=0.1, legend_title_text="",
                          xaxis_tickangle=0, yaxis_ticksuffix=" €")
        afficher(fig)

    col_g, col_d = st.columns(2)
    with col_g.container(key="carte_distribution"):
        res = resultats_1j[methode_principale]
        if methode_principale == "Monte Carlo":
            serie, titre = resultats_1j["Monte Carlo"]["simulations"], "Rendements simulés"
        else:
            serie, titre = r_ptf.values, "Rendements observés"
        st.subheader("Distribution à 1 jour", help=D["distribution"])
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=serie, nbinsx=100, histnorm="probability density",
                                   name=titre, marker_color=ACCENT, opacity=0.45))
        x = np.linspace(serie.min(), serie.max(), 400)
        fig.add_trace(go.Scatter(x=x, y=stats.norm.pdf(x, serie.mean(), serie.std()),
                                 name="Loi normale de même μ et σ", mode="lines",
                                 line=dict(color=COULEURS[1], width=2.5, shape="spline")))
        fig.add_vline(x=-res["VaR"], line_dash="dash", line_color=COULEURS[7],
                      annotation_text=f"VaR {pct(res['VaR'])}", annotation_position="top left")
        fig.add_vline(x=-res["ES"], line_dash="dot", line_color=COULEURS[6],
                      annotation_text=f"ES {pct(res['ES'])}", annotation_position="bottom left")
        fig.update_layout(height=380, bargap=0.05, xaxis_tickformat=".1%")
        afficher(fig)

    with col_d.container(key="carte_qqplot"):
        st.subheader("QQ-plot face à la loi normale", help=D["qqplot"])
        z = np.sort((r_ptf.values - r_ptf.mean()) / r_ptf.std())     # rendements centrés réduits
        n = len(z)
        quantiles_theoriques = stats.norm.ppf((np.arange(1, n + 1) - 0.5) / n)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=quantiles_theoriques, y=z, mode="markers", name="Observations",
                                 marker=dict(size=6, color=ACCENT, opacity=0.6)))
        fig.add_trace(go.Scatter(x=[-4, 4], y=[-4, 4], mode="lines", name="Loi normale",
                                 line=dict(color=COULEURS[1], dash="dash", width=2)))
        fig.update_layout(height=380, xaxis_title="Quantiles théoriques",
                          yaxis_title="Quantiles observés")
        afficher(fig)

    k1, k2 = st.columns(2)
    with k1.container(key="carte_skew"):
        st.metric("Asymétrie (skewness)", f"{stats.skew(r_ptf):.2f}".replace(".", ","),
                  help=D["skewness"])
    with k2.container(key="carte_kurt"):
        st.metric("Excès de kurtosis", f"{stats.kurtosis(r_ptf):.2f}".replace(".", ","),
                  help=D["kurtosis"])


# =============================================================================
# 7. ONGLET BACKTESTING
# =============================================================================
with onglet_bt:
    if len(r_ptf) <= fenetre + 20:
        st.warning("Pas assez de données pour cette fenêtre : élargis la période ou réduis la fenêtre.")
    else:
        lignes = {}
        backtests = {}
        for code, nom in [("historique", "Historique"), ("normale", "Paramétrique normale"),
                          ("student", "Paramétrique Student")]:
            bt = lancer_backtest(r_ptf, alpha, fenetre, code, ddl)
            backtests[nom] = bt
            k = test_kupiec(bt["Exception"], alpha)
            c = test_christoffersen(bt["Exception"], alpha)
            f = feux_bale(bt["Exception"])
            rejete = c["Modèle rejeté (5 %)"] or k["Modèle rejeté (5 %)"]
            lignes[nom] = {
                "Exceptions observées": k["Exceptions observées"],
                "Exceptions attendues": round(k["Exceptions attendues"], 1),
                "p-value Kupiec": round(k["p-value"], 3),
                "p-value Christoffersen": round(c["p-value couverture conditionnelle"], 3),
                "Verdict (5 %)": "Rejeté" if rejete else "Accepté",
                "Zone Bâle (250 j)": f"{f['Zone']} ({f['Exceptions sur 250 jours']})",
            }

        with st.container(key="carte_tests"):
            st.subheader(f"Tests de validation · VaR {pct(alpha, 1)} à 1 jour, fenêtre de {fenetre} j",
                         help=D["backtesting"])
            st.dataframe(pd.DataFrame(lignes).T, column_config={
                "Exceptions observées": colonne(D["exception"]),
                "Exceptions attendues": colonne(D["exceptions_attendues"]),
                "p-value Kupiec": colonne(D["kupiec"]),
                "p-value Christoffersen": colonne(D["christoffersen"]),
                "Verdict (5 %)": colonne(D["verdict"]),
                "Zone Bâle (250 j)": colonne(D["bale"]),
            })

        col_g, col_d = st.columns([1, 2.3])
        with col_g.container(key="carte_bale"):
            choix = st.selectbox("Méthode à visualiser", list(backtests), help=D["methode"])
            bt = backtests[choix]
            f = feux_bale(bt["Exception"])
            st.metric(f"Exceptions sur 250 jours · zone {f['Zone'].lower()}",
                      f"{f['Exceptions sur 250 jours']}", help=D["bale"])
            barre_exceptions(f["Exceptions sur 250 jours"])
            if alpha != 0.99:
                st.caption("Les feux tricolores sont définis pour une VaR à 99 % : "
                           "à un autre niveau, la zone est indicative.")

        with col_d.container(key="carte_backtest"):
            st.subheader(f"Pertes réalisées et VaR · {choix}", help=D["exception"])
            exc = bt[bt["Exception"]]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=bt.index, y=bt["Perte"], name="Perte réalisée", mode="lines",
                                     line=dict(color=COULEUR_PERTES, width=1)))
            fig.add_trace(go.Scatter(x=bt.index, y=bt["VaR"], name=f"VaR {pct(alpha, 1)}",
                                     mode="lines", line=dict(color=ACCENT, width=2.5),
                                     fill="tozeroy", fillcolor="rgba(91, 108, 240, 0.08)"))
            fig.add_trace(go.Scatter(x=exc.index, y=exc["Perte"], name="Exception", mode="markers",
                                     marker=dict(color=COULEUR_EXCEPTION, size=9, symbol="x")))
            fig.update_layout(height=360, hovermode="x unified", yaxis_tickformat=".1%")
            afficher(fig)


# =============================================================================
# 8. ONGLET STRESS TESTS
# =============================================================================
with onglet_stress:
    stress = lancer_stress(tuple(tickers), tuple(float(p) for p in poids))
    stress_aff = stress.copy()
    stress_aff["Perte (€)"] = stress_aff["Perte totale"] * montant
    disponibles = stress.dropna()

    col_g, col_d = st.columns([1.25, 1])
    with col_g.container(key="carte_stress_tableau"):
        st.subheader("Scénarios historiques", help=D["stress_historique"])
        st.dataframe(stress_aff.style.format({"Perte totale": pct, "Pire journée": pct,
                                              "Perte (€)": euros},
                                             na_rep="Indisponible"),
                     column_config={"Perte totale": colonne(D["perte_totale"]),
                                    "Pire journée": colonne(D["pire_journee"]),
                                    "Perte (€)": colonne(D["perte_totale"])})
    with col_d.container(key="carte_stress_graphique"):
        st.subheader("Pertes de crise face à la VaR", help=D["var"])
        if len(disponibles) > 0:
            fig = px.bar(disponibles.reset_index(), x="Perte totale", y="index", orientation="h",
                         color_discrete_sequence=[ACCENT], labels={"index": "", "Perte totale": ""})
            fig.add_vline(x=principal["VaR"], line_dash="dash", line_color=COULEURS[7],
                          annotation_text=f"VaR ({horizon} j)")
            fig.update_layout(height=260, xaxis_tickformat=".0%", bargap=0.4)
            afficher(fig)
        else:
            st.info("Aucune donnée disponible sur ces périodes pour les titres choisis.")

    with st.container(key="carte_hypothetique"):
        st.subheader("Scénario hypothétique", help=D["stress_hypothetique"])
        colonnes = st.columns(min(len(tickers), 4))
        chocs = []
        for i, t in enumerate(tickers):
            choc = colonnes[i % len(colonnes)].slider(f"Choc {t} (%)", min_value=-60, max_value=30,
                                                      value=-20, step=5, help=D["choc"])
            chocs.append(choc / 100)
        perte_hyp = stress_hypothetique(poids, chocs)
        h1, h2 = st.columns(2)
        h1.metric("Perte du portefeuille", pct(perte_hyp), help=D["stress_hypothetique"])
        h2.metric("Perte en euros", euros(perte_hyp * montant), help=D["stress_hypothetique"])

st.write("")
st.caption("Projet pédagogique — données Yahoo Finance. Ne constitue pas un outil de gestion "
           "des risques en production.")
