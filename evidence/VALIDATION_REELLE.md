# Validation réelle — 5 novembre 2026

## Périmètre observé

Contrôles effectués sur le conteneur local `cloudera`, base Hive `tp4`, table HBase `product_analytics`. Le service Thrift 1 était joignable à `172.17.0.2:9090`. Cette adresse Docker peut changer ; elle n'est pas codée en dur dans le client.

Le schéma réel de `sales_fact_full` comporte `product_id` (int), `product_name` (string), `product_category_id` (int), `revenue` (double), `viewnumber` (bigint) et `order_date` (string).

La source contient **11 387 lignes et 75 produits distincts**. Pour chacun des 75 produits, le contrôle a confirmé un nom, une catégorie et une valeur de vues distincts, avec revenue et vues renseignés. L'export de référence possède cinq champs par ligne, 75 clés uniques et des valeurs numériques valides.

## Anomalie constatée et corrigée

L'import antérieur avait additionné `ViewNumber` alors que ce compteur était répété entre les lignes d'un même produit.

- Produit `1004` : 364 lignes Hive, compteur source constant de **1 028 vues**, mais HBase contenait **374 192** (= 364 × 1 028).
- Produit `116` : 203 lignes Hive, compteur source constant de **896 vues**, mais HBase contenait **181 888** (= 203 × 896).

Le contrôle complet avant intervention a trouvé **75 écarts de vues sur 75 produits**. Les clés, noms, catégories et revenus concordaient déjà.

La correction a conservé le compteur constant de la source avec `MAX(ViewNumber)`, uniquement après le contrôle de constance. Les 75 compteurs HBase ont été mis à jour. **Aucune autre cellule n'a été modifiée**, ce qui a été vérifié après écriture.

Cette intervention ciblée n'a pas recréé la table ni réexécuté ImportTsv. Elle ne modifie pas les anciens fichiers d'export HDFS : ne pas réimporter un ancien fichier contenant les vues surévaluées. Utiliser la requête corrigée et vérifier le nouvel export avant tout prochain chargement.

## Preuves conservées

- [Référence Hive à une ligne par produit](reference_hive.tsv).
- [Comparaison avant correction](comparaison_avant.csv) : 375 comparaisons de champs, 75 écarts.
- [Comparaison après correction](comparaison_hive_hbase.csv) : **375 comparaisons, zéro écart**.
- [Sauvegarde avant correction](hbase_before_views_fix.json), créée le 5 novembre 2026 à 20:36:08, heure de Paris. Les noms de cellules et leurs valeurs brutes sont encodés en Base64. Elle conserve les valeurs courantes avant écriture, pas l'ensemble des versions historiques HBase.

La comparaison couvre les **75 produits**, pas uniquement un échantillon : les ensembles de clés sont identiques. Les 375 contrôles portent sur l'identifiant, le nom, la catégorie, le revenu et les vues. Tolérance du revenu : 0,01 unité source ; autres champs : égalité exacte.

## Résultat après correction

Le produit `1004` retourne :

- Nom : Field & Stream Sportsman 16 Gun Fire Safe.
- Catégorie : 45.
- Revenu brut de la source : `6637668.282318115` ; affichage arrondi à deux décimales.
- Vues : **1 028**.

Les familles HBase lues sont `info` et `metrics`. Le scan d'exploration a retourné dix lignes. Le comptage complet a retourné **75 lignes**.

L'interface Streamlit a été testée avec les vraies données pour `1004` et `116` : affichage des indicateurs, historique de deux produits et construction des graphiques sans exception. Les **11 tests automatisés réussis** couvrent notamment les alias, les valeurs invalides, les clés dupliquées, les erreurs de lecture et la remise à zéro lors d'un changement de serveur.

Le dashboard a également été ouvert dans un navigateur et la fiche réelle `1004` consultée. Une [capture de contrôle](dashboard.png) est conservée. Le serveur de cette session écoute sur <http://127.0.0.1:8502> (le port 8501 était occupé).

## Limites précises

- La concordance est prouvée avec la synthèse Hive inspectée, pas avec une reconstruction indépendante de tous les journaux Web et de toutes les commandes brutes.
- `orders_count`, `quantity_sold`, `last_view_date` et `refreshed_at` ne sont pas présents dans les lignes actuelles. Le dashboard sait les lire, mais aucun chiffre ni date de fraîcheur n'a été inventé.
- La fréquence quotidienne est une proposition documentée. Aucun ordonnanceur n'a été installé.
- L'extension historique par produit et par jour est expliquée ; sa table n'a pas été créée.
- Ces résultats décrivent l'état constaté lors de cette intervention. Les fichiers de preuve ne se mettent pas à jour automatiquement.

## Rejouer la vérification

Depuis le répertoire du projet, en adaptant l'adresse du serveur :

```bash
.venv/bin/python validation.py evidence/reference_hive.tsv
.venv/bin/python verify_hbase.py evidence/reference_hive.tsv --host 172.17.0.2
.venv/bin/python -m unittest discover -s tests -v
```

La vérification complète parcourt la table et compare les 75 fiches. Elle est destinée au petit jeu du TP, pas à une lecture automatique à chaque ouverture du dashboard. Le fichier de référence est un instantané : pour un nouveau lot, régénérer et contrôler une nouvelle référence Hive.

L'option `--repair-views` n'est pas nécessaire pour vérifier. Elle modifie HBase, refuse les divergences sur d'autres champs et exige une nouvelle sauvegarde dont le fichier n'existe pas déjà. Ne pas la relancer avec un ancien export après une mise à jour métier.
