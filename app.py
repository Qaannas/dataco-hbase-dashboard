"""DataCo - tableau de bord et recherche de produits."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from hbase_client import TABLE_NAME, get_product, test_connection

st.set_page_config(page_title='DataCo • Tableau de bord', page_icon='📊', layout='wide')
st.title('DataCo — Tableau de bord produits')
st.caption('Recherchez un produit, consultez ses indicateurs et comparez les produits consultés.')

with st.sidebar:
    st.header('Paramètres')
    st.caption('Connexion à votre base locale.')
    host = st.text_input('Hôte Thrift', value=os.getenv('HBASE_HOST', '127.0.0.1')).strip()
    port = int(st.number_input('Port Thrift', min_value=1, max_value=65535,
                              value=int(os.getenv('HBASE_PORT', '9090')), step=1))
    st.caption(f'Table : {TABLE_NAME} · HBase Thrift 1')
    if st.button('Tester la connexion'):
        try:
            tables = test_connection(host, port)
            if TABLE_NAME in tables:
                st.success(f'Connexion réussie ; table {TABLE_NAME} disponible.')
            else:
                st.warning(f'Connexion réussie, mais table {TABLE_NAME} absente.')
        except Exception as exc:
            st.error(f'Connexion impossible : {exc}')

# Never mix rows read from different servers, or show a previous successful lookup as a new result.
connection_key = (host, port, TABLE_NAME)
if st.session_state.get('connection_key') != connection_key:
    st.session_state.connection_key = connection_key
    st.session_state.lookup_history = {}
    st.session_state.latest_product_id = None

st.subheader('Recherche de produit')
with st.form('lookup'):
    product_id = st.text_input('Identifiant du produit', value='1004')
    submitted = st.form_submit_button('Consulter le produit', type='primary')
if submitted:
    st.session_state.latest_product_id = None
    try:
        result = get_product(product_id, host, port)
        if result is None:
            st.warning(f'Aucun produit trouvé pour {product_id!r}.')
        else:
            st.session_state.lookup_history[result['product_id']] = result
            st.session_state.latest_product_id = result['product_id']
    except Exception as exc:
        st.error(f'Lecture impossible : {exc}')

latest = st.session_state.latest_product_id
if latest:
    row = st.session_state.lookup_history[latest]
    st.subheader(row.get('product_name') or f'Produit {latest}')
    st.write(f'**Produit :** {latest} · **Catégorie :** {row.get("category_id") or "Non disponible"}')
    c1, c2 = st.columns(2)
    c1.metric('Revenu (unité source)', f'{row["revenue"]:,.2f}' if row.get('revenue') is not None else 'Non disponible')
    c2.metric('Vues', f'{row["view_count"]:,}' if row.get('view_count') is not None else 'Non disponible')
    if row.get('orders_count') is not None or row.get('quantity_sold') is not None:
        c3, c4 = st.columns(2)
        c3.metric('Commandes', f'{row["orders_count"]:,}' if row.get('orders_count') is not None else '—')
        c4.metric('Quantité vendue', f'{row["quantity_sold"]:,}' if row.get('quantity_sold') is not None else '—')
    else:
        st.caption('Commandes et quantités non disponibles dans cette table : ces agrégats doivent être préparés en amont.')
    if row.get('last_view_date'):
        st.write(f'Dernière consultation du produit : {row["last_view_date"]}')
    missing = [key for key in ('product_name', 'category_id', 'revenue', 'view_count') if row.get(key) is None]
    if missing:
        st.warning('Fiche incomplète : ' + ', '.join(missing))
    refreshed = row.get('refreshed_at')
    if refreshed:
        try:
            timestamp = datetime.fromisoformat(refreshed.replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                raise ValueError('Fuseau horaire absent')
            age = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
            if age < 0:
                st.warning('Date de rafraîchissement future : vérifier l’horloge et les métadonnées.')
            elif age > 26:
                st.warning(f'Indicateurs âgés de {age:.1f} h : objectif de fraîcheur de 26 h dépassé.')
            else:
                st.info(f'Rafraîchissement déclaré : {refreshed} · âge : {age:.1f} h.')
        except ValueError:
            st.warning('Métadonnée refreshed_at invalide : utiliser ISO 8601 avec fuseau horaire.')
    else:
        st.info('Dernier rafraîchissement inconnu : aucune métadonnée metrics:refreshed_at dans cette fiche.')

st.divider()
st.subheader('Produits consultés pendant cette session')
st.caption('Comparaison locale des produits recherchés, sans classement global ni scan complet.')
if st.session_state.lookup_history:
    df = pd.DataFrame(st.session_state.lookup_history.values())
    st.dataframe(df.drop(columns=['view_number'], errors='ignore'), hide_index=True, width='stretch')
    if len(df) > 1:
        plot = df.set_index('product_id')
        for metric, title in [('revenue', 'Revenu par produit (unité source)'), ('view_count', 'Nombre de vues par produit')]:
            if plot[metric].notna().any():
                st.write(f'**{title}**')
                st.bar_chart(plot[[metric]], x_label='Product ID', y_label=title)
    if st.button('Effacer l’historique'):
        st.session_state.lookup_history = {}
        st.session_state.latest_product_id = None
        st.rerun()
else:
    st.info('Consultez un premier produit pour commencer.')
