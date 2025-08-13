#!/usr/bin/env python3
"""
Economato - Unified inventory and consumption management app
"""

import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
import xlsxwriter
from datetime import datetime
import os

# Configuration
GOOGLE_DRIVE_BASE = "/Users/stefanodellapietra/Library/CloudStorage/GoogleDrive-stefano@panoramagroup.it/My Drive"
GIACENZE_PATH = os.path.join(GOOGLE_DRIVE_BASE, "Organized/data/economato/giacienze/Eco_SituazioneAvanzataArticoli_giacienze11082025.xml")
CONSUMI_PATH = os.path.join(GOOGLE_DRIVE_BASE, "Organized/data/economato/consumi/xml/ECO_SituazioneConsumi_DettagliPerArticolo_dal1aprile.xml")

st.set_page_config(page_title="Economato", layout="wide")
st.title("Economato - Gestione Giacenze e Consumi")

# File loading section
st.header("📁 Caricamento File")
col1, col2 = st.columns(2)

with col1:
    use_default_giacenze = st.checkbox("Usa file giacenze predefinito", value=True)
    if use_default_giacenze and os.path.exists(GIACENZE_PATH):
        giacenze_file = GIACENZE_PATH
        st.success(f"✅ File giacenze: {os.path.basename(giacenze_file)}")
    else:
        giacenze_file = st.file_uploader("Carica XML Giacenze", type=['xml'])

with col2:
    use_default_consumi = st.checkbox("Usa file consumi predefinito", value=True)
    if use_default_consumi and os.path.exists(CONSUMI_PATH):
        consumi_file = CONSUMI_PATH
        st.success(f"✅ File consumi: {os.path.basename(consumi_file)}")
    else:
        consumi_file = st.file_uploader("Carica XML Consumi", type=['xml'])

# Parse giacenze
giacenze_data = []
if giacenze_file:
    try:
        tree = ET.parse(giacenze_file)
        root = tree.getroot()

        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['ns'] = namespace

        items = root.findall('.//ns:Detail', namespaces) if namespaces else root.findall('.//Detail')

        for item in items:
            giacenze_data.append({
                'codice': item.get('CodiceArticolo', ''),
                'descrizione': item.get('Descrizione', ''),
                'giacenza': float(item.get('Esistenza_1', 0))
            })

        st.success(f"✅ Caricati {len(giacenze_data)} articoli da giacenze")
    except Exception as e:
        st.error(f"Errore nel parsing del file giacenze: {str(e)}")

# Parse consumi
consumi_data = []
if consumi_file:
    try:
        tree = ET.parse(consumi_file)
        root = tree.getroot()

        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['ns'] = namespace

        items = root.findall('.//ns:Detail', namespaces) if namespaces else root.findall('.//Detail')

        for item in items:
            codice = item.get('Codice', '')
            quantita_str = item.get('Quantita', '0')

            # Extract month from Data field
            mese = None
            if item.get('Data'):
                try:
                    mese = item.get('Data')[:7]  # Gets 'YYYY-MM'
                except:
                    pass

            if codice and mese:
                try:
                    quantita = float(quantita_str.replace(',', '.'))
                except:
                    quantita = 0.0

                consumi_data.append({
                    'codice': codice.strip(),
                    'descrizione': item.get('Descrizione', ''),
                    'mese': mese,
                    'quantita': quantita
                })

        st.success(f"✅ Caricati {len(consumi_data)} record consumi")
    except Exception as e:
        st.error(f"Errore nel parsing del file consumi: {str(e)}")

# Show data summaries
if giacenze_data:
    st.header("📊 Riepilogo Giacenze")
    df_giacenze = pd.DataFrame(giacenze_data)
    search = st.text_input("🔍 Cerca per codice o descrizione", "")
    if search:
        mask = (df_giacenze['codice'].str.contains(search, case=False, na=False) |
                df_giacenze['descrizione'].str.contains(search, case=False, na=False))
        df_filtered = df_giacenze[mask]
    else:
        df_filtered = df_giacenze
    st.dataframe(df_filtered, use_container_width=True, height=400)

if consumi_data:
    st.header("📊 Riepilogo Consumi")
    df_consumi = pd.DataFrame(consumi_data)
    consumi_per_mese = df_consumi.groupby('mese')['quantita'].sum().sort_index()
    st.bar_chart(consumi_per_mese)

# Generate report
if giacenze_data and consumi_data:
    st.header("📥 Genera Report Excel")

    col1, col2 = st.columns(2)
    with col1:
        giorni_copertura = st.number_input("Giorni di copertura desiderati", min_value=1, max_value=365, value=30)
    with col2:
        mesi_consumo = st.number_input("Mesi per calcolo consumo medio", min_value=1, max_value=12, value=3)

    if st.button("🚀 Genera Report Excel", type="primary"):
        df_giacenze = pd.DataFrame(giacenze_data)
        df_consumi = pd.DataFrame(consumi_data)

        # Create pivot table
        df_consumi_pivot = df_consumi.pivot_table(
            index='codice',
            columns='mese',
            values='quantita',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        # Merge with giacenze
        df_merged = pd.merge(
            df_giacenze,
            df_consumi_pivot,
            on='codice',
            how='left'
        )

        # Fill NaN values with 0 for month columns
        month_cols = [col for col in df_merged.columns if col.startswith('202')]
        df_merged[month_cols] = df_merged[month_cols].fillna(0)

        # Calculate averages
        if month_cols:
            recent_months = sorted(month_cols)[-mesi_consumo:] if len(month_cols) >= mesi_consumo else month_cols
            df_merged['consumo_medio_mensile'] = df_merged[recent_months].mean(axis=1)
        else:
            df_merged['consumo_medio_mensile'] = 0

        df_merged['consumo_medio_giornaliero'] = df_merged['consumo_medio_mensile'] / 30

        # Calculate coverage days
        df_merged['giorni_copertura_attuali'] = df_merged.apply(
            lambda x: x['giacenza'] / x['consumo_medio_giornaliero'] if x['consumo_medio_giornaliero'] > 0 else float('inf'),
            axis=1
        )

        # Calculate reorder quantities
        df_merged['fabbisogno_per_copertura'] = df_merged['consumo_medio_giornaliero'] * giorni_copertura
        df_merged['quantita_da_ordinare'] = df_merged['fabbisogno_per_copertura'] - df_merged['giacenza']
        df_merged['quantita_da_ordinare'] = df_merged['quantita_da_ordinare'].apply(lambda x: max(0, x))

        # Create Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Main sheet
            df_merged.to_excel(writer, sheet_name='Analisi Completa', index=False)

            # Urgent reorders
            df_urgent = df_merged[
                (df_merged['giorni_copertura_attuali'] < 15) &
                (df_merged['consumo_medio_mensile'] > 0)
            ].sort_values('giorni_copertura_attuali')

            if len(df_urgent) > 0:
                df_urgent.to_excel(writer, sheet_name='Riordino Urgente', index=False)

            # Statistics
            stats_data = {
                'Metrica': [
                    'Totale articoli',
                    'Articoli con consumi',
                    'Articoli con copertura < 15 giorni',
                    'Articoli con copertura < 30 giorni'
                ],
                'Valore': [
                    len(df_merged),
                    len(df_merged[df_merged['consumo_medio_mensile'] > 0]),
                    len(df_merged[(df_merged['giorni_copertura_attuali'] < 15) & (df_merged['giorni_copertura_attuali'] != float('inf'))]),
                    len(df_merged[(df_merged['giorni_copertura_attuali'] < 30) & (df_merged['giorni_copertura_attuali'] != float('inf'))])
                ]
            }
            pd.DataFrame(stats_data).to_excel(writer, sheet_name='Statistiche', index=False)

        # Download button
        st.download_button(
            label="📥 Scarica Report Excel",
            data=output.getvalue(),
            file_name=f"economato_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Show preview
        if len(df_urgent) > 0:
            st.subheader("⚠️ Articoli che richiedono riordino urgente")
            st.dataframe(df_urgent[['codice', 'descrizione', 'giacenza', 'giorni_copertura_attuali', 'quantita_da_ordinare']].head(20))

# Instructions
with st.sidebar:
    st.header("📋 Istruzioni")
    st.markdown("""
    1. I file predefiniti sono già selezionati
    2. Clicca su "Genera Report Excel" per creare il report
    3. Il report include:
       - Analisi completa con consumi mensili
       - Articoli da riordinare urgentemente
       - Statistiche generali
    """)

    st.header("ℹ️ Info")
    st.markdown("""
    - **Giacenze**: Magazzino centrale
    - **Consumi**: Aprile-Luglio 2025
    - **Calcoli**: Basati sul consumo medio degli ultimi mesi
    """)

if __name__ == "__main__":
    # The app runs automatically when executed with streamlit
    pass
