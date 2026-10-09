"""
Tests du backtesting et des stress tests (backtesting.py), sur données simulées.
"""

import numpy as np
import pandas as pd
import pytest

from backtesting import (var_glissante, test_kupiec, test_christoffersen, feux_bale,
                         stress_sur_prix, stress_hypothetique)
from var_models import var_historique, var_parametrique

# pytest exécute toute fonction dont le nom commence par « test_ » : on lui
# signale que ces deux-là sont des fonctions du projet, pas des tests.
test_kupiec.__test__ = False
test_christoffersen.__test__ = False


# ---------------------------------------------------------------------------
# Test de Kupiec
# ---------------------------------------------------------------------------
def test_kupiec_valeur_de_reference():
    # Cas classique des manuels (Jorion) : 10 exceptions sur 250 jours à 99 %
    exceptions = np.zeros(250, dtype=bool)
    exceptions[:10] = True
    res = test_kupiec(exceptions, 0.99)
    assert res["Statistique LR"] == pytest.approx(12.96, abs=0.01)
    assert res["Modèle rejeté (5 %)"]


def test_kupiec_accepte_le_nombre_attendu():
    exceptions = np.zeros(1_000, dtype=bool)
    exceptions[::100] = True                          # exactement 10 exceptions sur 1 000
    res = test_kupiec(exceptions, 0.99)
    assert res["Statistique LR"] == pytest.approx(0, abs=1e-9)
    assert not res["Modèle rejeté (5 %)"]


def test_kupiec_sans_aucune_exception():
    res = test_kupiec(np.zeros(250, dtype=bool), 0.99)
    assert np.isfinite(res["Statistique LR"])        # pas d'erreur de log(0)


# ---------------------------------------------------------------------------
# Test de Christoffersen
# ---------------------------------------------------------------------------
def test_christoffersen_detecte_les_grappes():
    exceptions = np.zeros(1_000, dtype=bool)
    exceptions[500:510] = True                        # 10 exceptions d'affilée
    res = test_christoffersen(exceptions, 0.99)
    assert res["p-value indépendance"] < 0.05


def test_christoffersen_accepte_des_exceptions_dispersees():
    exceptions = np.zeros(1_000, dtype=bool)
    exceptions[::100] = True                          # 10 exceptions bien espacées
    res = test_christoffersen(exceptions, 0.99)
    assert res["Exceptions consécutives (n11)"] == 0
    assert not res["Modèle rejeté (5 %)"]


# ---------------------------------------------------------------------------
# Feux tricolores de Bâle : bornes des zones
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n_exceptions, zone", [(0, "Verte"), (4, "Verte"), (5, "Orange"),
                                                (9, "Orange"), (10, "Rouge")])
def test_zones_de_bale(n_exceptions, zone):
    exceptions = np.zeros(250, dtype=bool)
    exceptions[:n_exceptions] = True
    assert feux_bale(exceptions)["Zone"] == zone


def test_bale_ne_compte_que_les_250_derniers_jours():
    exceptions = np.zeros(500, dtype=bool)
    exceptions[:20] = True                            # exceptions anciennes, ignorées
    assert feux_bale(exceptions)["Exceptions sur 250 jours"] == 0


# ---------------------------------------------------------------------------
# VaR glissante
# ---------------------------------------------------------------------------
@pytest.fixture
def rendements():
    rng = np.random.default_rng(3)
    return pd.Series(rng.normal(0, 0.01, 400))


@pytest.mark.parametrize("methode", ["historique", "normale", "student", "ewma", "fhs"])
def test_var_glissante_ne_regarde_pas_le_futur(rendements, methode):
    # Modifier la perte du dernier jour ne doit pas changer la VaR de ce même jour
    modifie = rendements.copy()
    modifie.iloc[-1] = -0.50
    bt1 = var_glissante(rendements, 0.99, 250, methode)
    bt2 = var_glissante(modifie, 0.99, 250, methode)
    assert bt1["VaR"].iloc[-1] == pytest.approx(bt2["VaR"].iloc[-1])
    assert bt2["Exception"].iloc[-1]                  # -50 % est bien une exception


@pytest.mark.parametrize("methode, calcul_direct", [
    ("historique", lambda passe: var_historique(passe, 0.99)["VaR"]),
    ("normale", lambda passe: var_parametrique(passe, 0.99, "normale")["VaR"]),
    ("student", lambda passe: var_parametrique(passe, 0.99, "student", 5)["VaR"]),
])
def test_var_glissante_egale_le_calcul_direct(rendements, methode, calcul_direct):
    # La version rapide (rolling) doit redonner, pour un jour pris au hasard,
    # la VaR calculée directement sur les 250 jours qui le précèdent.
    bt = var_glissante(rendements, 0.99, 250, methode)
    t = 320
    attendu = calcul_direct(rendements.iloc[t - 250:t])
    assert bt.loc[rendements.index[t], "VaR"] == pytest.approx(attendu, rel=1e-10)


def test_var_glissante_refuse_une_fenetre_trop_longue(rendements):
    with pytest.raises(ValueError):
        var_glissante(rendements, 0.99, fenetre=1_000)


# ---------------------------------------------------------------------------
# Stress tests
# ---------------------------------------------------------------------------
def test_stress_sur_prix():
    # Action A : -20 % ; action B : stable ; portefeuille 50/50 -> perte de 10 %.
    # Valeur du portefeuille : 1 -> 0,95 -> 0,90 ; pire journée : 0,90 / 0,95 - 1 = -5,26 %
    prix = pd.DataFrame({"A": [100, 90, 80], "B": [50, 50, 50]})
    res = stress_sur_prix(prix, [0.5, 0.5])
    assert res["Perte totale"] == pytest.approx(0.10)
    assert res["Pire journée"] == pytest.approx(1 - 0.90 / 0.95)


def test_stress_hypothetique():
    assert stress_hypothetique([0.5, 0.5], [-0.20, -0.10]) == pytest.approx(0.15)
    with pytest.raises(ValueError):
        stress_hypothetique([0.5, 0.5], [-0.20])
