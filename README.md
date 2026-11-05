# DataCo — Tableau de bord HBase, Atelier 5

Application Streamlit en français centrée sur un tableau de bord avec recherche par identifiant produit, indicateurs et comparaison des produits consultés.

Les [réponses françaises à l'atelier](REPONSES_ATELIER5_FR.md) couvrent les sept questions, l'architecture, les commandes de démonstration et la politique de fraîcheur. Le [bilan réel](evidence/VALIDATION_REELLE.md) décrit la validation de 75 produits et la correction du double comptage des vues.

## Lancement sur Ubuntu

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

Ouvrir l’adresse indiquée par Streamlit (habituellement <http://localhost:8501> ; le port suivant est choisi si celui-ci est occupé). Le lanceur cherche l'adresse du conteneur `cloudera` sur le bridge Docker Linux. Si elle n'est pas disponible, il utilise `127.0.0.1`. Pour imposer une connexion :

```bash
HBASE_HOST=172.17.0.2 HBASE_PORT=9090 ./run.sh
```

L'adresse ci-dessus était celle du laboratoire au moment des contrôles ; elle peut changer. L'hôte et le port sont modifiables dans la barre latérale. La variable `HBASE_TABLE` permet de choisir une autre table avant le lancement.

L'application Python s'exécute sur Ubuntu, avec Python 3.10 ou ultérieur, pas dans l'ancien CentOS du conteneur.

