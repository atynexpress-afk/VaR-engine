"""
onglets.py
Contenu des quatre onglets de l'application : une fonction par onglet.
app.py prépare les données et les résultats, puis appelle ces fonctions
à l'intérieur de chaque onglet. Chaque fonction reçoit explicitement
ce dont elle a besoin : on voit d'un coup d'œil de quoi dépend chaque onglet.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from backtesting import (var_glissante, test_kupiec, test_christoffersen, test_acerbi_szekely,
                         feux_bale,
                         stress_historiques, stress_hypothetique)
from definitions import DEFINITIONS as D
from formats import euros, pct, nombre, nombre_signe, p_value, colonne
from style import (afficher, barre_exceptions, encadre, COULEURS, COULEUR_PORTEFEUILLE, COULEUR_PERTES,
                   COULEUR_EXCEPTION, ACCENT)


# =============================================================================
# CALCULS LONGS MIS EN CACHE
# Streamlit relance tout le script à chaque clic : le cache garde en mémoire
# le résultat tant que les paramètres ne changent pas.
# =============================================================================
@st.cache_data(show_spinner="Backtesting en cours…")
def lancer_backtest(r_ptf, alpha, fenetre, methode, ddl, lam):
    return var_glissante(r_ptf, alpha, fenetre, methode, ddl, lam)


@st.cache_data(show_spinner="Téléchargement des crises historiques…")
def lancer_stress(tickers, poids):
    return stress_historiques(list(tickers), list(poids))


# =============================================================================
# 1. ONGLET PORTEFEUILLE
# =============================================================================
def onglet_portefeuille(prix, rendements, r_ptf, poids):
    """Évolution des prix, statistiques annualisées et corrélations.
    Les colonnes de prix portent les noms lisibles des titres.
    """
    with st.container(key="carte_base100"):
        st.subheader("Évolution des prix (base 100)", help=D["base100"])
        base100 = prix / prix.iloc[0] * 100
        fig = go.Figure()
        for i, t in enumerate(prix.columns):
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
        }, index=prix.columns)
        stats_actifs.loc["Portefeuille"] = [1.0, r_ptf.mean() * 252, r_ptf.std() * np.sqrt(252)]
        st.dataframe(stats_actifs.style.format(lambda x: pct(x, 1)), column_config={
            "Poids": colonne(D["poids"]),
            "Rendement annuel": colonne(D["rendement_annuel"]),
            "Volatilité annuelle": colonne(D["volatilite"]),
        })
    with col_d.container(key="carte_correlation"):
        st.subheader("Matrice de corrélation", help=D["correlation"])
        if prix.shape[1] > 1:
            fig = px.imshow(rendements.corr(), text_auto=".2f", zmin=-1, zmax=1,
                            color_continuous_scale=[[0, COULEURS[0]], [0.5, "#f1f2f6"],
                                                    [1, COULEURS[1]]])
            fig.update_layout(height=340, coloraxis_showscale=False)
            afficher(fig)
        else:
            st.info("Ajoute au moins deux actions pour voir les corrélations.")



# =============================================================================
# 2. ONGLET VaR & ES
# =============================================================================
def onglet_var_es(resultats_1j, tableau, r_ptf, methode_principale, horizon, montant):
    """Comparaison des méthodes, distribution des rendements et QQ-plot.

    resultats_1j : résultats à 1 jour par méthode (dictionnaire)
    tableau      : VaR et ES à l'horizon choisi (une ligne par méthode)
    """
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
        # Noms courts pour que les six libellés tiennent sous les barres
        long["index"] = long["index"].map({
            "Historique": "Historique", "Paramétrique normale": "Normale",
            "Paramétrique Student": "Student", "Monte Carlo": "Monte Carlo",
            "EWMA (RiskMetrics)": "EWMA", "Historique filtrée (FHS)": "FHS"})
        fig = px.bar(long, x="index", y="Perte (€)", color="Mesure", barmode="group",
                     color_discrete_sequence=COULEURS[:2], labels={"index": "", "Perte (€)": ""})
        fig.update_layout(height=300, bargap=0.35, bargroupgap=0.1, legend_title_text="",
                          xaxis_tickangle=0, yaxis_ticksuffix=" €",
                          yaxis_tickformat=",.0f")
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
# 3. ONGLET BACKTESTING
# =============================================================================
def raison_du_rejet(kupiec, christoffersen):
    """
    Traduit le résultat des tests en une phrase compréhensible par un débutant.
    Renvoie None si le modèle passe les deux tests.
    """
    if kupiec["Modèle rejeté (5 %)"]:
        if kupiec["Exceptions observées"] > kupiec["Exceptions attendues"]:
            return "sous-estime le risque (la perte dépasse la VaR trop souvent)"
        return "surestime le risque (la VaR est trop prudente)"
    if christoffersen["Modèle rejeté (5 %)"]:
        return ("nombre de dépassements correct, mais ils arrivent en rafale pendant "
                "les crises (le modèle réagit trop lentement)")
    return None


def conclusion_backtesting(raisons):
    """Encadré de synthèse au-dessus du tableau des tests."""
    valides = [nom for nom, raison in raisons.items() if raison is None]
    rejetes = [f"<b>{nom}</b> : {raison}" for nom, raison in raisons.items() if raison is not None]
    if len(valides) == 0:
        titre, ton = "Aucun modèle ne passe les tests de validation", "alerte"
    elif len(valides) == 1:
        titre, ton = f"Seul le modèle {valides[0]} passe les tests de validation", "succes"
    else:
        titre, ton = f"Modèles validés : {', '.join(valides)}", "succes"
    encadre(titre, rejetes, ton)


def onglet_backtesting(r_ptf, alpha, fenetre, ddl, lam):
    """
    Tests de validation de chaque méthode et graphique des exceptions.
    Renvoie le tableau des tests (pour l'export), ou None si les données manquent.
    """
    if len(r_ptf) <= fenetre + 20:
        st.warning("Pas assez de données pour cette fenêtre : élargis la période ou réduis la fenêtre.")
        return None
    else:
        lignes = {}
        lignes_es = {}
        backtests = {}
        raisons = {}
        for code, nom in [("historique", "Historique"), ("normale", "Paramétrique normale"),
                          ("student", "Paramétrique Student"), ("ewma", "EWMA (RiskMetrics)"),
                          ("fhs", "Historique filtrée (FHS)")]:
            bt = lancer_backtest(r_ptf, alpha, fenetre, code, ddl, lam)
            backtests[nom] = bt
            k = test_kupiec(bt["Exception"], alpha)
            c = test_christoffersen(bt["Exception"], alpha)
            f = feux_bale(bt["Exception"])
            raisons[nom] = raison_du_rejet(k, c)
            rejete = raisons[nom] is not None
            lignes[nom] = {
                "Exceptions observées": k["Exceptions observées"],
                "Exceptions attendues": k["Exceptions attendues"],
                "p-value Kupiec": k["p-value"],
                "p-value Christoffersen": c["p-value couverture conditionnelle"],
                "Verdict (5 %)": "Rejeté" if rejete else "Accepté",
                "Zone Bâle (250 j)": f"{f['Zone']} ({f['Exceptions sur 250 jours']})",
            }
            a = test_acerbi_szekely(bt, alpha)
            lignes_es[nom] = {"Z2 (Acerbi-Szekely)": a["Z2"], "Zone ES": a["Zone"]}

        with st.container(key="carte_tests"):
            st.subheader(f"Tests de validation · VaR {pct(alpha, 1)} à 1 jour, fenêtre de {fenetre} j",
                         help=D["backtesting"])
            conclusion_backtesting(raisons)
            # Les valeurs restent des nombres (alignés à droite) ; seul leur affichage est formaté
            tests = pd.DataFrame(lignes).T.style.format({"Exceptions attendues": nombre,
                                                          "p-value Kupiec": p_value,
                                                          "p-value Christoffersen": p_value})
            st.dataframe(tests, column_config={
                "Exceptions observées": colonne(D["exception"]),
                "Exceptions attendues": colonne(D["exceptions_attendues"]),
                "p-value Kupiec": colonne(D["kupiec"]),
                "p-value Christoffersen": colonne(D["christoffersen"]),
                "Verdict (5 %)": colonne(D["verdict"]),
                "Zone Bâle (250 j)": colonne(D["bale"]),
            })

        with st.container(key="carte_tests_es"):
            st.subheader(f"Backtest de l'Expected Shortfall · ES {pct(alpha, 1)} à 1 jour",
                         help=D["acerbi_szekely"])
            col_tableau, col_texte = st.columns([1, 1.2], vertical_alignment="center")
            col_tableau.dataframe(
                pd.DataFrame(lignes_es).T.style.format({"Z2 (Acerbi-Szekely)": nombre_signe}),
                column_config={"Z2 (Acerbi-Szekely)": colonne(D["acerbi_szekely"]),
                               "Zone ES": colonne(D["acerbi_szekely"])})
            sous_estimees = [nom for nom, l in lignes_es.items() if l["Zone ES"] != "Verte"]
            col_texte.markdown(
                "Le test de Kupiec compte les dépassements de la VaR ; celui-ci vérifie aussi "
                "leur **ampleur** : les jours de dépassement, la perte est-elle en moyenne égale "
                "à l'ES prévue ? **Z2 proche de 0** : ES fiable. **Z2 sous −0,70** : les pertes "
                "extrêmes sont plus fortes que prévu.")
            if sous_estimees:
                col_texte.markdown(f"ES sous-estimée par : **{', '.join(sous_estimees)}**. "
                                   "Les jours de crise, leurs pertes dépassent nettement "
                                   "l'ES qu'ils avaient prévue.")

        col_g, col_d = st.columns([1, 2.3])
        with col_g.container(key="carte_bale"):
            choix = st.selectbox("Méthode à visualiser", list(backtests), help=D["methode"])
            bt = backtests[choix]
            f = feux_bale(bt["Exception"])
            st.metric("Exceptions sur 250 jours", f"{f['Exceptions sur 250 jours']}",
                      delta=f"Zone {f['Zone'].lower()}", delta_color="off", delta_arrow="off",
                      help=D["bale"])
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
            fig.add_trace(go.Scatter(x=bt.index, y=bt["ES"], name=f"ES {pct(alpha, 1)}",
                                     mode="lines", line=dict(color=COULEURS[6], width=1.5,
                                                             dash="dot")))
            fig.add_trace(go.Scatter(x=exc.index, y=exc["Perte"], name="Exception", mode="markers",
                                     marker=dict(color=COULEUR_EXCEPTION, size=9, symbol="x")))
            fig.update_layout(height=360, hovermode="x unified", yaxis_tickformat=".1%")
            afficher(fig)
        return pd.concat([pd.DataFrame(lignes).T, pd.DataFrame(lignes_es).T], axis=1)


# =============================================================================
# 4. ONGLET STRESS TESTS
# =============================================================================
def onglet_stress_tests(tickers, noms_titres, poids, montant, res_1j):
    """Crises historiques et scénario hypothétique.

    res_1j : VaR et ES à 1 jour de la méthode mise en avant
    Renvoie le tableau des crises historiques (pour l'export).
    """
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
        # On compare des pertes sur la MÊME durée : la pire journée de chaque crise
        # face à la VaR et à l'ES à 1 jour (la perte totale porte sur plusieurs semaines).
        st.subheader("Pire journée de crise face à la VaR 1 j", help=D["pire_journee"])
        if len(disponibles) > 0:
            fig = px.bar(disponibles.reset_index(), x="Pire journée", y="index", orientation="h",
                         color_discrete_sequence=[ACCENT], labels={"index": "", "Pire journée": ""})
            # Lignes verticales, avec leur étiquette au-dessus du graphique pour ne pas
            # chevaucher les barres : la VaR à gauche de sa ligne, l'ES à droite.
            for mesure, couleur, trait, cote in [("VaR", COULEURS[7], "dash", "right"),
                                                 ("ES", COULEURS[6], "dot", "left")]:
                fig.add_vline(x=res_1j[mesure], line_dash=trait, line_color=couleur)
                fig.add_annotation(x=res_1j[mesure], y=1, yref="paper", yanchor="bottom",
                                   xanchor=cote, showarrow=False,
                                   text=f"{mesure} {pct(res_1j[mesure], 1)}",
                                   font=dict(color=couleur))
            fig.update_layout(height=300, xaxis_tickformat=".0%", bargap=0.4,
                              margin=dict(t=40))
            afficher(fig)
        else:
            st.info("Aucune donnée disponible sur ces périodes pour les titres choisis.")

    with st.container(key="carte_hypothetique"):
        st.subheader("Scénario hypothétique", help=D["stress_hypothetique"])
        colonnes = st.columns(min(len(tickers), 4))
        chocs = []
        for i, nom in enumerate(noms_titres):
            choc = colonnes[i % len(colonnes)].slider(f"Choc {nom} (%)", min_value=-60,
                                                      max_value=30, value=-20, step=5,
                                                      help=D["choc"])
            chocs.append(choc / 100)
        perte_hyp = stress_hypothetique(poids, chocs)
        h1, h2 = st.columns(2)
        h1.metric("Perte du portefeuille", pct(perte_hyp), help=D["stress_hypothetique"])
        h2.metric("Perte en euros", euros(perte_hyp * montant), help=D["stress_hypothetique"])
    return stress_aff
