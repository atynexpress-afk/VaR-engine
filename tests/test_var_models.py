"""
Tests des calculs de VaR et d'Expected Shortfall (var_models.py).
On utilise des données simulées : les tests ne dépendent pas d'Internet
et donnent toujours le même résultat.

Lancement dans le terminal :  python -m pytest
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from var_models import (var_historique, var_parametrique, var_monte_carlo, var_ewma,
                        var_historique_filtree, volatilite_ewma, changer_horizon)


@pytest.fixture
def rendements_gaussiens():
    """10 000 rendements journaliers gaussiens : moyenne 0,05 %, volatilité 1 %."""
    rng = np.random.default_rng(0)
    return pd.Series(rng.normal(0.0005, 0.01, 10_000))


# ---------------------------------------------------------------------------
# VaR historique
# ---------------------------------------------------------------------------
def test_historique_quantile_connu():
    # Pertes de 1 à 100 : le quantile à 99 % vaut 99,01 (interpolation linéaire)
    r = -np.arange(1, 101)
    res = var_historique(r, 0.99)
    assert res["VaR"] == pytest.approx(99.01)
    assert res["ES"] == pytest.approx(100)          # seule la perte de 100 dépasse la VaR


def test_es_superieure_a_var(rendements_gaussiens):
    for alpha in (0.95, 0.99):
        res = var_historique(rendements_gaussiens, alpha)
        assert res["ES"] > res["VaR"] > 0


# ---------------------------------------------------------------------------
# VaR paramétrique
# ---------------------------------------------------------------------------
def test_normale_formule_fermee(rendements_gaussiens):
    mu, sigma = rendements_gaussiens.mean(), rendements_gaussiens.std()
    res = var_parametrique(rendements_gaussiens, 0.99, "normale")
    assert res["VaR"] == pytest.approx(-mu + sigma * 2.326348, rel=1e-6)
    assert res["ES"] == pytest.approx(-mu + sigma * 2.665214, rel=1e-6)


def test_student_proche_de_la_normale_quand_ddl_grand(rendements_gaussiens):
    normale = var_parametrique(rendements_gaussiens, 0.99, "normale")
    student = var_parametrique(rendements_gaussiens, 0.99, "student", ddl=1000)
    assert student["VaR"] == pytest.approx(normale["VaR"], rel=0.01)
    assert student["ES"] == pytest.approx(normale["ES"], rel=0.01)


def test_student_refuse_ddl_trop_petit(rendements_gaussiens):
    with pytest.raises(ValueError):
        var_parametrique(rendements_gaussiens, 0.99, "student", ddl=2)


def test_les_methodes_retrouvent_la_var_theorique(rendements_gaussiens):
    # Sur des données gaussiennes, toutes les méthodes doivent s'accorder (à 5 % près)
    theorique = -0.0005 + 0.01 * stats.norm.ppf(0.99)
    assert var_historique(rendements_gaussiens, 0.99)["VaR"] == pytest.approx(theorique, rel=0.05)
    assert var_parametrique(rendements_gaussiens, 0.99)["VaR"] == pytest.approx(theorique, rel=0.05)


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------
def test_monte_carlo_reproductible_et_coherent():
    rng = np.random.default_rng(1)
    rendements = pd.DataFrame(rng.multivariate_normal(
        [0, 0], [[1e-4, 5e-5], [5e-5, 1e-4]], size=5_000), columns=["A", "B"])
    poids = [0.5, 0.5]

    res1 = var_monte_carlo(rendements, poids, 0.99, n_sim=50_000, graine=42)
    res2 = var_monte_carlo(rendements, poids, 0.99, n_sim=50_000, graine=42)
    assert res1["VaR"] == res2["VaR"]                 # même graine -> même résultat

    r_ptf = rendements @ np.array(poids)
    normale = var_parametrique(r_ptf, 0.99, "normale")
    assert res1["VaR"] == pytest.approx(normale["VaR"], rel=0.03)


# ---------------------------------------------------------------------------
# EWMA et historique filtrée
# ---------------------------------------------------------------------------
def test_ewma_recurrence_calculee_a_la_main():
    r = np.array([0.01, -0.02, 0.03])
    sigma = volatilite_ewma(r, lam=0.9, n_init=3)
    v0 = np.var(r, ddof=1)
    v1 = 0.9 * v0 + 0.1 * 0.01 ** 2
    v2 = 0.9 * v1 + 0.1 * 0.02 ** 2
    v3 = 0.9 * v2 + 0.1 * 0.03 ** 2
    assert sigma ** 2 == pytest.approx([v0, v1, v2, v3])


def test_ewma_reagit_a_un_choc():
    calme = np.full(300, 0.005)
    apres_choc = np.append(calme, -0.10)             # krach de 10 % le dernier jour
    assert var_ewma(apres_choc)["VaR"] > 3 * var_ewma(calme)["VaR"]


def test_ewma_sur_rendements_constants():
    # Si le rendement vaut toujours 1 %, la volatilité EWMA converge vers 1 %
    sigma = volatilite_ewma(np.full(1_000, 0.01))
    assert sigma[-1] == pytest.approx(0.01)


def test_fhs_proche_de_la_normale_sur_donnees_gaussiennes(rendements_gaussiens):
    fhs = var_historique_filtree(rendements_gaussiens, 0.99)
    ewma = var_ewma(rendements_gaussiens, 0.99)
    assert fhs["VaR"] == pytest.approx(ewma["VaR"], rel=0.10)
    assert fhs["ES"] > fhs["VaR"]


# ---------------------------------------------------------------------------
# Horizon
# ---------------------------------------------------------------------------
def test_racine_du_temps():
    res = changer_horizon({"VaR": 0.02, "ES": 0.03}, 9)
    assert res["VaR"] == pytest.approx(0.06)
    assert res["ES"] == pytest.approx(0.09)
