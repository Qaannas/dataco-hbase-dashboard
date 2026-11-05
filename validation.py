"""Validation of a five-column Hive export, without assuming additive measures."""
from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Any

COLUMNS = ('product_id', 'product_name', 'category_id', 'revenue', 'view_number')


def number(value: Any, *, counter: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'Valeur numérique invalide : {value!r}') from None
    if not result.is_finite():
        raise ValueError(f'Valeur non finie : {value!r}')
    if counter and (result < 0 or result != result.to_integral_value()):
        raise ValueError(f'Compteur entier positif ou nul attendu : {value!r}')
    return result


def read_tsv(text: str) -> list[dict[str, str]]:
    """No header; one row per key. Reject duplicate keys instead of deduplicating."""
    rows = []
    seen = set()
    for line, values in enumerate(csv.reader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE), 1):
        if len(values) != 5:
            raise ValueError(f'Ligne {line} : cinq champs sont requis, sans en-tête.')
        if any(not v.strip() or v.strip() in ('\\N', 'NULL') for v in values):
            raise ValueError(f'Ligne {line} : champ vide ou NULL.')
        if any('\n' in v or '\r' in v for v in values):
            raise ValueError(f'Ligne {line} : retour à la ligne dans un champ.')
        if values[0] != values[0].strip():
            raise ValueError(f'Ligne {line} : espaces autour de la RowKey.')
        row = dict(zip(COLUMNS, values))
        if row['product_id'] in seen:
            raise ValueError(f'Ligne {line} : product_id répété ({row["product_id"]}).')
        seen.add(row['product_id'])
        number(row['revenue'])
        number(row['view_number'], counter=True)
        rows.append(row)
    if not rows:
        raise ValueError('Le fichier TSV est vide.')
    return rows


def compare_product(source: dict[str, str], actual: dict[str, Any] | None) -> list[dict[str, str]]:
    """Compare a source product with HBase. Revenue tolerance: 0.01 source unit."""
    if actual is None:
        return [{'product_id': source['product_id'], 'champ': 'RowKey',
                 'source': source['product_id'], 'hbase': 'absent', 'statut': 'ÉCART'}]
    results = []
    for field in COLUMNS:
        expected, value = source[field], actual.get(field)
        if field == 'view_number' and value is None:
            value = actual.get('view_count')
        if field in ('revenue', 'view_number'):
            try:
                delta = abs(number(expected, counter=field == 'view_number') -
                            number(value, counter=field == 'view_number'))
                matched = delta <= (Decimal('0.01') if field == 'revenue' else Decimal(0))
            except ValueError:
                matched = False
        else:
            matched = str(value) == expected
        results.append({'product_id': source['product_id'], 'champ': field,
                        'source': expected, 'hbase': str(value),
                        'statut': 'OK' if matched else 'ÉCART'})
    return results


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Contrôle structurel du TSV avant ImportTsv.')
    parser.add_argument('tsv', type=Path)
    args = parser.parse_args()
    try:
        records = read_tsv(args.tsv.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f'ERREUR : {exc}\n')
    print(f'OK : {len(records)} produits uniques, cinq champs, indicateurs numériques valides.')
    print('Ce contrôle ne prouve pas la justesse des agrégats : vérifier leur granularité dans Hive.')
