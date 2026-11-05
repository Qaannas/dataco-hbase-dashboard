"""Read-only full comparison; optional narrowly scoped repair of repeated views."""
from __future__ import annotations

import argparse
import base64
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from hbase_client import TABLE_NAME, _connection, decode_product
from validation import compare_product, read_tsv


def snapshot(table):
    return {key.decode('utf-8'): cells for key, cells in table.scan(batch_size=1000)}


def report(source, rows):
    result = []
    for record in source:
        key = record['product_id']
        actual = decode_product(key, rows[key]) if key in rows else None
        result.extend(compare_product(record, actual))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--output', type=Path, default=Path('evidence/comparaison_hive_hbase.csv'))
    parser.add_argument('--repair-views', action='store_true', help='Corriger uniquement les vues ; sauvegarde obligatoire avant écriture.')
    parser.add_argument('--backup', type=Path, default=Path('evidence/hbase_before_views_fix.json'))
    args = parser.parse_args()
    source = read_tsv(args.reference.read_text(encoding='utf-8'))
    connection = _connection(args.host, args.port)
    try:
        table = connection.table(TABLE_NAME)
        before = snapshot(table)
        comparison = report(source, before)
        source_keys = {r['product_id'] for r in source}
        same_keys = source_keys == set(before)
        mismatches = [r for r in comparison if r['statut'] != 'OK']
        print(f'Source : {len(source)} produits ; HBase : {len(before)} ; mêmes clés : {same_keys}.')
        print(f'Écarts avant intervention : {len(mismatches)}.')
        if args.repair_views:
            if not same_keys or any(r['champ'] != 'view_number' for r in mismatches):
                raise ValueError('Réparation refusée : clés ou autres champs incohérents.')
            backup = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'host': args.host, 'port': args.port, 'table': TABLE_NAME,
                'rows': {key: {base64.b64encode(col).decode(): base64.b64encode(value).decode()
                               for col, value in cells.items()} for key, cells in before.items()},
            }
            # Exclusive creation: never overwrite an earlier backup.
            with args.backup.open('x', encoding='utf-8') as handle:
                json.dump(backup, handle, ensure_ascii=False, indent=2)
            corrections = {r['product_id'] for r in mismatches}
            for record in source:
                key = record['product_id']
                if key not in corrections:
                    continue
                current = table.row(key.encode())
                if current != before[key]:
                    raise ValueError(f'Produit {key} modifié depuis la sauvegarde ; arrêt.')
                value = record['view_number'].encode()
                cells = {name: value for name in (b'metrics:view_number', b'metrics:view_count') if name in current}
                if not cells:
                    cells = {b'metrics:view_number': value}
                table.put(key.encode(), cells)
            print(f'Compteurs corrigés : {len(corrections)} ; sauvegarde : {args.backup}.')
        after = snapshot(table) if args.repair_views else before
        comparison = report(source, after)
        with args.output.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['product_id', 'champ', 'source', 'hbase', 'statut'])
            writer.writeheader()
            writer.writerows(comparison)
        mismatches = sum(r['statut'] != 'OK' for r in comparison)
        print(f'Comparaisons : {len(comparison)} ; écarts : {mismatches} ; rapport : {args.output}.')
        if set(after) != source_keys or mismatches:
            return 1
        if args.repair_views:
            for key in before:
                protected_before = {c: v for c, v in before[key].items() if c not in (b'metrics:view_number', b'metrics:view_count')}
                protected_after = {c: v for c, v in after[key].items() if c not in (b'metrics:view_number', b'metrics:view_count')}
                if protected_before != protected_after:
                    raise ValueError(f'Un champ non ciblé a changé pour {key}.')
            print('Les autres cellules sont inchangées.')
        return 0
    finally:
        connection.close()


if __name__ == '__main__':
    raise SystemExit(main())
