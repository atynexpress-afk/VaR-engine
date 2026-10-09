"""
Tests de la préparation des données (data.py). Le téléchargement Yahoo Finance
n'est pas testé ici : il dépend d'Internet.
"""

import numpy as np
import pandas as pd
import pytest

from data import calculer_rendements, normaliser_poids, rendements_portefeuille


def test_normaliser_poids():
    assert normaliser_poids([2, 1, 1]) == pytest.approx([0.5, 0.25, 0.25])


@pytest.mark.parametrize("poids", [[-1, 2], [0, 0]])
def test_poids_invalides(poids):
    with pytest.raises(ValueError):
        normaliser_poids(poids)


def test_rendements_simples_et_log():
    prix = pd.DataFrame({"A": [100.0, 110.0, 99.0]})
    assert calculer_rendements(prix)["A"].tolist() == pytest.approx([0.10, -0.10])
    assert calculer_rendements(prix, "log")["A"].tolist() == pytest.approx(
        [np.log(1.1), np.log(0.9)])


def test_rendement_du_portefeuille():
    rendements = pd.DataFrame({"A": [0.10, -0.02], "B": [0.00, 0.04]})
    r_ptf = rendements_portefeuille(rendements, [3, 1])          # 75 % / 25 %
    assert r_ptf.tolist() == pytest.approx([0.075, -0.005])


def test_un_poids_par_action():
    rendements = pd.DataFrame({"A": [0.01], "B": [0.02]})
    with pytest.raises(ValueError):
        rendements_portefeuille(rendements, [1.0])
