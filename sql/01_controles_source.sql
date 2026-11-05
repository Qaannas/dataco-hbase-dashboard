-- Environnement observé : base tp4. Adapter USE si nécessaire.
USE tp4;
DESCRIBE sales_fact_full;
DESCRIBE tokenized_access_logs;

-- Granularité réelle et nombre de produits attendus.
SELECT COUNT(*) AS lignes_source, COUNT(DISTINCT product_id) AS produits
FROM sales_fact_full;

-- Doit renvoyer zéro ligne avant d'utiliser MAX(ViewNumber) pour ce jeu précis.
-- Ce contrôle prouve la constance, pas à lui seul la sémantique des vues.
SELECT product_id, COUNT(*) AS n,
       COUNT(DISTINCT ViewNumber) AS v,
       COUNT(DISTINCT product_name) AS p,
       COUNT(DISTINCT product_category_id) AS c,
       COUNT(ViewNumber) AS nv, COUNT(product_name) AS np,
       COUNT(product_category_id) AS nc, COUNT(revenue) AS nr
FROM sales_fact_full
GROUP BY product_id
HAVING product_id IS NULL OR v != 1 OR p != 1 OR c != 1
    OR nv != n OR np != n OR nc != n OR nr != n;

-- Comparer le total répété avec la somme incorrecte ; vérifier aussi les logs.
SELECT product_id, COUNT(*) AS lignes,
       SUM(revenue) AS revenue,
       MIN(ViewNumber) AS vues_min, MAX(ViewNumber) AS vues_max,
       SUM(ViewNumber) AS somme_vues_a_ne_pas_utiliser
FROM sales_fact_full
WHERE product_id IN (1004, 116)
GROUP BY product_id;
