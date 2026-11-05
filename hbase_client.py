"""Small HBase Thrift client for the DataCo Atelier 5 dashboard."""
from __future__ import annotations

import os
import math
from typing import Any

import happybase

TABLE_NAME = os.getenv('HBASE_TABLE', 'product_analytics')


def _read_cell(cells: dict[bytes, bytes], name: str) -> str | None:
    value = cells.get(name.encode('utf-8'))
    if value is None:
        return None
    return value.decode('utf-8', errors='replace')


def _numeric(value: str | None) -> float | None:
    if value is None or value.strip() == '':
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f'Indicateur non fini : {value!r}')
    return number


def _counter(value: str | None) -> int | None:
    from decimal import Decimal
    if value is None or not value.strip():
        return None
    number = Decimal(value)
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError(f'Compteur invalide : {value!r}')
    return int(number)


def _connection(host: str, port: int) -> happybase.Connection:
    host = host.strip()
    if not host:
        raise ValueError('Renseignez l’adresse du serveur HBase.')
    # Compatible with the default HBase Thrift 1 binary/buffered service.
    # Open only when a user requests a product; no full-table scan is needed.
    return happybase.Connection(
        host=host,
        port=port,
        timeout=5000,
        compat='0.98',
        transport='buffered',
        protocol='binary',
    )


def test_connection(host: str, port: int) -> list[str]:
    connection = _connection(host, port)
    try:
        return [name.decode('utf-8', errors='replace') for name in connection.tables()]
    finally:
        connection.close()


def get_product(product_id: str, host: str, port: int) -> dict[str, Any] | None:
    product_id = product_id.strip()
    if not product_id:
        raise ValueError('Enter a product ID.')
    connection = _connection(host, port)
    try:
        cells = connection.table(TABLE_NAME).row(product_id.encode('utf-8'))
    finally:
        connection.close()
    if not cells:
        return None

    return decode_product(product_id, cells)


def decode_product(product_id: str, cells: dict[bytes, bytes]) -> dict[str, Any]:
    views = _counter(_read_cell(cells, 'metrics:view_count'))
    legacy_views = _counter(_read_cell(cells, 'metrics:view_number'))
    if views is not None and legacy_views is not None and views != legacy_views:
        raise ValueError(f'Produit {product_id} : view_count et view_number sont différents.')
    views = views if views is not None else legacy_views

    row: dict[str, Any] = {
        'product_id': product_id,
        'product_name': _read_cell(cells, 'info:product_name'),
        'category_id': _read_cell(cells, 'info:category_id'),
        'revenue': _numeric(_read_cell(cells, 'metrics:revenue')),
        'view_count': views,
        'view_number': views,  # Compatibility with the original five-column import.
    }
    # Extension described in the TP: these are optional, not in the 5-column import.
    for qualifier in ('orders_count', 'quantity_sold'):
        value = _read_cell(cells, f'metrics:{qualifier}')
        if value is not None:
            row[qualifier] = _counter(value)
    last_view_date = _read_cell(cells, 'metrics:last_view_date')
    if last_view_date:
        row['last_view_date'] = last_view_date
    refreshed_at = _read_cell(cells, 'metrics:refreshed_at')
    if refreshed_at:
        row['refreshed_at'] = refreshed_at
    return row


def inspect_table(host: str, port: int) -> dict[str, Any]:
    """Explicit teaching scan, always limited to ten rows, plus real families."""
    connection = _connection(host, port)
    try:
        table = connection.table(TABLE_NAME)
        families = sorted(name.decode('utf-8') for name in table.families())
        rows = [dict(product_id=key.decode('utf-8'), **{
            column.decode('utf-8'): value.decode('utf-8', errors='replace')
            for column, value in cells.items()
        }) for key, cells in table.scan(limit=10, batch_size=10)]
        return {'families': families, 'rows': rows}
    finally:
        connection.close()


def count_products(host: str, port: int) -> int:
    """Full-table count for the explicit lab validation action only."""
    connection = _connection(host, port)
    try:
        # A key-only filter avoids transporting all product cell values.
        return sum(1 for _ in connection.table(TABLE_NAME).scan(
            filter='FirstKeyOnlyFilter() AND KeyOnlyFilter()', batch_size=1000))
    finally:
        connection.close()
