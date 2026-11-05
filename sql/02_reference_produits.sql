-- À exécuter après 01_controles_source.sql et vérification des sources.
-- Dans le jeu observé, le revenu est ventilé et les vues totales sont répétées.
-- MAX conserve ici le compteur constant ; ce n'est pas une règle universelle.
USE tp4;
SELECT CAST(product_id AS STRING),
       regexp_replace(product_name, '[\\t\\r\\n]', ' '),
       CAST(product_category_id AS STRING),
       CAST(SUM(revenue) AS STRING),
       CAST(MAX(ViewNumber) AS STRING)
FROM sales_fact_full
GROUP BY product_id, product_name, product_category_id
ORDER BY product_id;
