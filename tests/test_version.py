"""
Test de l'empreinte du moteur (version.py), qui renouvelle le cache de Streamlit.
"""

import shutil

from version import FICHIERS_MOTEUR, DOSSIER, version_moteur


def test_empreinte_change_quand_le_moteur_change(tmp_path):
    # Copie des fichiers du moteur dans un dossier temporaire fourni par pytest
    for fichier in FICHIERS_MOTEUR:
        shutil.copy(DOSSIER / fichier, tmp_path / fichier)
    avant = version_moteur(tmp_path)
    assert version_moteur(tmp_path) == avant              # stable si rien ne change

    with open(tmp_path / "backtesting.py", "a", encoding="utf-8") as f:
        f.write("\n# modification\n")
    assert version_moteur(tmp_path) != avant
