import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO
import xlsxwriter
from datetime import datetime
import re

st.set_page_config(page_title="Economato MVP", layout="wide")
st.title("Economato - Gestione Giacenze e Consumi")

# Upload files
col1, col2 = st.columns(2)
with col1:
    giacenze_file = st.file_uploader("Carica XML Giacenze", type=['xml'])
with col2:
    consumi_file = st.file_uploader("Carica XML Consumi", type=['xml'])

# Parse giacenze
giacenze_data = []
if giacenze_file:
    st.write("📄 File giacenze caricato:", giacenze_file.name)
    try:
        tree = ET.parse(giacenze_file)
        root = tree.getroot()

        # Debug: mostra namespace
        st.write("Debug - Root tag:", root.tag)

        # Registra namespace se presente
        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['ns'] = namespace
            st.write("Debug - Namespace trovato:", namespace)

        # Prova diversi percorsi per trovare Detail
        items = []

        # Metodo 1: con namespace
        if namespaces:
            items = root.findall('.//ns:Detail', namespaces)
            if not items:
                items = root.findall('.//ns:Detail_Collection/ns:Detail', namespaces)

        # Metodo 2: senza namespace specifico
        if not items:
            items = root.findall('.//{*}Detail')

        # Metodo 3: cerca ovunque
        if not items:
            for elem in root.iter():
                if 'Detail' in elem.tag and elem.attrib:
                    items.append(elem)

        st.write(f"Debug - Trovati {len(items)} elementi Detail")

        # Se ancora non trova nulla, mostra struttura
        if not items:
            st.write("Debug - Struttura XML (primi 5 livelli):")
            def show_structure(elem, level=0, max_level=5):
                if level < max_level:
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    st.write("  " * level + f"- {tag} (attributi: {len(elem.attrib)})")
                    for child in elem[:3]:  # mostra solo primi 3 figli
                        show_structure(child, level + 1, max_level)
            show_structure(root)

        for item in items:
            try:
                giacenze_data.append({
                    'codice': item.get('CodiceArticolo', ''),
                    'descrizione': item.get('Descrizione', ''),
                    'classe': item.get('Classe', ''),
                    'categoria': item.get('Categoria', ''),
                    'giacenza': float(item.get('textbox23', '0').replace(',', '.')),
                    'unita': item.get('UM', ''),
                    'fornitore': item.get('RagioneSociale', ''),
                    'prezzo_unitario': float(item.get('EuroUnitazio', '0').replace(',', '.'))
                })
            except ValueError:
                continue

        st.success(f"✅ Caricati {len(giacenze_data)} articoli dalle giacenze")
    except Exception as e:
        st.error(f"Errore nel parsing del file giacenze: {str(e)}")

# Parse consumi
consumi_data = []
if consumi_file:
    st.write("📄 File consumi caricato:", consumi_file.name)
    try:
        tree = ET.parse(consumi_file)
        root = tree.getroot()

        # Debug
        st.write("Debug - Root tag consumi:", root.tag)

        # Registra namespace
        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['ns'] = namespace
            st.write("Debug - Namespace consumi:", namespace)

        # Cerca Detail
        items = []
        if namespaces:
            items = root.findall('.//ns:Detail', namespaces)
            if not items:
                items = root.findall('.//ns:Detail_Collection/ns:Detail', namespaces)

        if not items:
            items = root.findall('.//{*}Detail')

        if not items:
            for elem in root.iter():
                if 'Detail' in elem.tag and elem.attrib:
                    items.append(elem)

        st.write(f"Debug - Trovati {len(items)} record consumi")

        # Mostra primo record come esempio
        if items and len(items) > 0:
            st.write("Debug - Esempio primo record consumi:")
            st.write(dict(items[0].attrib))

        for item in items:
            try:
                # Estrai data e calcola mese
                data_str = item.get('Data', '')
                if data_str:
                    mese = data_str[:7]  # YYYY-MM
                else:
                    mese = 'N/A'

                # Gestisci quantità - usa il campo Quantita invece di textbox8
                quantita_str = item.get('Quantita', '0')
                try:
                    quantita = float(quantita_str.replace(',', '.'))
                    # Debug per valori negativi
                    if quantita < 0:
                        st.warning(f"⚠️ Valore negativo trovato: {quantita} per {codice} nel reparto {item.get('textbox7', '')}")
                except:
                    quantita = 0

                # Estrai codice - potrebbe essere in campi diversi
                codice = item.get('Codice', '') or item.get('textbox5', '') or item.get('CodiceArticolo', '')
                descrizione = item.get('textbox9', '') or item.get('Descrizione', '')

                consumi_data.append({
                    'codice': codice.strip(),  # Rimuovi spazi
                    'descrizione': descrizione,
                    'quantita': quantita,
                    'mese': mese,
                    'reparto': item.get('textbox7', ''),
                    'data': data_str
                })
            except Exception as e:
                continue

        st.success(f"✅ Caricati {len(consumi_data)} record consumi")
    except Exception as e:
        st.error(f"Errore nel parsing del file consumi: {str(e)}")



# Show data with filter
if giacenze_data:
    st.subheader("📊 Dati Giacenze")
    df_giacenze = pd.DataFrame(giacenze_data)

    # Filter
    search = st.text_input("🔍 Filtra per descrizione o codice", "")
    if search:
        mask = (df_giacenze['descrizione'].str.contains(search, case=False, na=False) |
                df_giacenze['codice'].str.contains(search, case=False, na=False))
        df_filtered = df_giacenze[mask]
    else:
        df_filtered = df_giacenze

    st.dataframe(df_filtered, use_container_width=True, height=400)

# Show consumi summary if available
if consumi_data:
    st.subheader("📊 Riepilogo Consumi per Mese")
    df_consumi = pd.DataFrame(consumi_data)

    # Controlla valori negativi
    negativi = df_consumi[df_consumi['quantita'] < 0]
    if len(negativi) > 0:
        st.info(f"ℹ️ Trovati {len(negativi)} movimenti con quantità negative (probabili rettifiche inventario)")

    # Raggruppa per mese
    consumi_per_mese = df_consumi.groupby('mese')['codice'].count().sort_index()
    st.bar_chart(consumi_per_mese)



# Export button
if giacenze_data and consumi_data:
    st.subheader("📥 Export Report Unificato")

    # Informazione sulla giacenza
    st.info("ℹ️ La giacenza mostrata è quella del **magazzino centrale** (non include le giacenze nei reparti)")

    # Input per giorni di copertura e configurazione mesi
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        giorni_copertura = st.number_input(
            "Giorni di copertura desiderati",
            min_value=1,
            max_value=90,
            value=7,
            help="Per quanti giorni vuoi avere scorte disponibili"
        )
    with col2:
        giorni_aprile = st.number_input(
            "Giorni lavorativi Aprile 2025",
            min_value=1,
            max_value=30,
            value=15,
            help="Dal 16 aprile = 15 giorni"
        )
    with col3:
        giorni_standard = st.number_input(
            "Giorni lavorativi altri mesi",
            min_value=1,
            max_value=31,
            value=30,
            help="Giorni standard per gli altri mesi"
        )

    # Debug: mostra esempi di codici
    df_giacenze_temp = pd.DataFrame(giacenze_data)
    df_consumi_temp = pd.DataFrame(consumi_data)

    st.write("🔍 **Debug - Verifica matching codici:**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Primi 10 codici da Giacenze:")
        st.dataframe(df_giacenze_temp[['codice', 'descrizione']].head(10))
        st.write(f"Totale articoli in giacenze: {len(df_giacenze_temp)}")
        st.write(f"Esempio codice: '{df_giacenze_temp['codice'].iloc[0]}' (lunghezza: {len(df_giacenze_temp['codice'].iloc[0])})")
    with col2:
        st.write("Primi 10 codici da Consumi:")
        st.dataframe(df_consumi_temp[['codice', 'descrizione']].head(10))
        st.write(f"Totale record consumi: {len(df_consumi_temp)}")
        if len(df_consumi_temp) > 0:
            st.write(f"Esempio codice: '{df_consumi_temp['codice'].iloc[0]}' (lunghezza: {len(df_consumi_temp['codice'].iloc[0])})")
            # Mostra codici unici nei consumi
            codici_unici = df_consumi_temp['codice'].unique()
            st.write(f"Codici unici nei consumi: {len(codici_unici)}")
            st.write("Primi 5 codici unici:", list(codici_unici[:5]))

    # Verifica se ci sono codici in comune
    if len(df_giacenze_temp) > 0 and len(df_consumi_temp) > 0:
        codici_giacenze = set(df_giacenze_temp['codice'].str.strip())
        codici_consumi = set(df_consumi_temp['codice'].str.strip())
        codici_comuni = codici_giacenze.intersection(codici_consumi)
        st.write(f"**Codici in comune trovati: {len(codici_comuni)}**")
        if len(codici_comuni) > 0:
            st.write("Esempi di codici in comune:", list(codici_comuni)[:5])
        else:
            st.warning("⚠️ Nessun codice in comune trovato! I codici potrebbero essere formattati diversamente.")

    if st.button("🚀 Genera Report Excel con Consumi Mensili", type="primary"):
        # Prepara dataframes
        df_giacenze = pd.DataFrame(giacenze_data)
        df_consumi = pd.DataFrame(consumi_data)

        # Crea pivot table dei consumi per mese
        df_consumi_pivot = df_consumi.pivot_table(
            index=['codice'],  # Usa solo codice per il matching
            columns='mese',
            values='quantita',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        # Rinomina colonne mesi e definisci giorni per mese
        mesi_dict = {
            '2024-01': 'Gennaio 2024',
            '2024-02': 'Febbraio 2024',
            '2024-03': 'Marzo 2024',
            '2024-04': 'Aprile 2024',
            '2024-05': 'Maggio 2024',
            '2024-06': 'Giugno 2024',
            '2024-07': 'Luglio 2024',
            '2024-08': 'Agosto 2024',
            '2024-09': 'Settembre 2024',
            '2024-10': 'Ottobre 2024',
            '2024-11': 'Novembre 2024',
            '2024-12': 'Dicembre 2024',
            '2025-01': 'Gennaio 2025',
            '2025-02': 'Febbraio 2025',
            '2025-03': 'Marzo 2025',
            '2025-04': 'Aprile 2025',
            '2025-05': 'Maggio 2025',
            '2025-06': 'Giugno 2025',
            '2025-07': 'Luglio 2025'
        }

        # Giorni effettivi per mese
        giorni_per_mese = {
            '2025-04': giorni_aprile,  # Apertura 16 aprile
            '2025-05': giorni_standard,
            '2025-06': giorni_standard,
            '2025-03': giorni_standard
        }

        # Rinomina solo le colonne che esistono
        for old_name, new_name in mesi_dict.items():
            if old_name in df_consumi_pivot.columns:
                df_consumi_pivot = df_consumi_pivot.rename(columns={old_name: new_name})

        # Unisci con giacenze (usa solo codice per il merge)
        df_unified = pd.merge(
            df_giacenze[['codice', 'descrizione', 'classe', 'categoria', 'giacenza', 'unita', 'fornitore', 'prezzo_unitario']],
            df_consumi_pivot,
            on=['codice'],
            how='left'
        )

        # Debug: mostra il risultato del merge
        st.write(f"**Debug Merge:**")
        st.write(f"- Articoli in giacenze: {len(df_giacenze)}")
        st.write(f"- Articoli in consumi (dopo pivot): {len(df_consumi_pivot)}")
        st.write(f"- Articoli dopo merge: {len(df_unified)}")

        # Mostra esempi di consumi pivot
        if len(df_consumi_pivot) > 0:
            st.write("Esempio consumi dopo pivot:")
            st.dataframe(df_consumi_pivot.head())

        # Riempie NaN con 0 per i mesi
        mesi_cols = [col for col in df_unified.columns if '202' in str(col)]
        df_unified[mesi_cols] = df_unified[mesi_cols].fillna(0)

        # Calcola consumo totale
        df_unified['consumo_totale'] = df_unified[mesi_cols].sum(axis=1)

        # Calcola consumo giornaliero per ogni mese
        for mese_col in mesi_cols:
            mese_key = None
            for k, v in mesi_dict.items():
                if v == mese_col:
                    mese_key = k
                    break

            giorni = giorni_per_mese.get(mese_key, giorni_standard)
            df_unified[f'{mese_col}_giornaliero'] = df_unified[mese_col] / giorni

        # Calcola consumo giornaliero medio totale
        giornaliero_cols = [col for col in df_unified.columns if col.endswith('_giornaliero')]
        if giornaliero_cols:
            df_unified['consumo_giornaliero'] = df_unified[giornaliero_cols].mean(axis=1)
        else:
            df_unified['consumo_giornaliero'] = df_unified['consumo_medio_mensile'] / 30

        # Calcola consumo medio mensile
        n_mesi = len(mesi_cols)
        df_unified['consumo_medio_mensile'] = df_unified['consumo_totale'] / n_mesi if n_mesi > 0 else 0

        # Calcola giorni di copertura attuali
        df_unified['giorni_copertura_attuali'] = df_unified.apply(
            lambda row: 0 if row['giacenza'] == 0 or row['consumo_giornaliero'] == 0 else row['giacenza'] / row['consumo_giornaliero'],
            axis=1
        )

        # Suggerimento ordine basato sui giorni di copertura desiderati
        df_unified['da_ordinare'] = df_unified.apply(
            lambda row: max(0, (row['consumo_giornaliero'] * giorni_copertura) - row['giacenza']),
            axis=1
        )

        # Aggiungi colonne con unità di misura per chiarezza
        df_unified['giacenza_con_um'] = df_unified.apply(lambda row: f"{row['giacenza']:.1f} {row['unita']}", axis=1)
        df_unified['consumo_giornaliero_con_um'] = df_unified.apply(lambda row: f"{row['consumo_giornaliero']:.2f} {row['unita']}/giorno", axis=1)
        df_unified['da_ordinare_con_um'] = df_unified.apply(lambda row: f"{row['da_ordinare']:.1f} {row['unita']}", axis=1)

        # Riordina colonne - ordina i mesi cronologicamente
        cols_order = ['codice', 'descrizione', 'classe', 'categoria', 'unita', 'fornitore', 'giacenza', 'prezzo_unitario']

        # Ordina i mesi cronologicamente
        mesi_ordinati = []
        for anno in ['2024', '2025']:
            for mese_num in range(1, 13):
                mese_key = f"{anno}-{mese_num:02d}"
                mese_name = mesi_dict.get(mese_key)
                if mese_name and mese_name in df_unified.columns:
                    mesi_ordinati.append(mese_name)

        # Aggiungi prima tutti i mesi
        cols_order.extend(mesi_ordinati)

        # Poi aggiungi tutti i consumi giornalieri
        giornalieri_ordinati = [f'{mese}_giornaliero' for mese in mesi_ordinati if f'{mese}_giornaliero' in df_unified.columns]
        cols_order.extend(giornalieri_ordinati)

        cols_order.extend(['consumo_totale', 'consumo_medio_mensile', 'consumo_giornaliero', 'giorni_copertura_attuali', 'da_ordinare'])

        # Rimuovi colonne duplicate e non esistenti
        cols_order = [col for col in cols_order if col in df_unified.columns]

        # Aggiungi le colonne con unità di misura
        final_cols = cols_order[:cols_order.index('giacenza')+1]
        final_cols.extend(['giacenza_con_um'])
        # Aggiungi colonne tra giacenza e consumo_totale
        giacenza_idx = cols_order.index('giacenza')
        consumo_totale_idx = cols_order.index('consumo_totale')

        # Aggiungi prima tutti i mesi
        for col in cols_order[giacenza_idx+1:consumo_totale_idx]:
            if not col.endswith('_giornaliero'):
                final_cols.append(col)

        # Poi aggiungi tutti i giornalieri formattati
        for col in cols_order[giacenza_idx+1:consumo_totale_idx]:
            if col.endswith('_giornaliero'):
                # Formatta il consumo giornaliero con unità
                mese_name = col.replace('_giornaliero', '')
                df_unified[f'{col}_fmt'] = df_unified.apply(
                    lambda row: f"{row[col]:.2f} {row['unita']}/g" if pd.notna(row[col]) and row[col] > 0 else f"0 {row['unita']}/g",
                    axis=1
                )
                final_cols.append(f'{col}_fmt')

        final_cols.extend(['consumo_totale', 'consumo_giornaliero_con_um', 'giorni_copertura_attuali', 'da_ordinare_con_um'])

        # Rimuovi colonne che non esistono
        final_cols = [col for col in final_cols if col in df_unified.columns]
        df_unified_display = df_unified[final_cols].copy()

        # Crea Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Foglio principale unificato
            df_unified_display.to_excel(writer, sheet_name='Giacenze e Consumi', index=False)

            # Formatta il foglio
            workbook = writer.book
            worksheet = writer.sheets['Giacenze e Consumi']

            # Formato per numeri
            num_format = workbook.add_format({'num_format': '#,##0.00'})

            # Formato per giorni di copertura
            days_format = workbook.add_format({'num_format': '#,##0'})

            # Formato per intestazioni
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BD',
                'border': 1
            })

            # Applica formati
            for col_num, col_name in enumerate(df_unified_display.columns):
                worksheet.write(0, col_num, col_name, header_format)

                # Larghezza colonne
                if col_name in ['descrizione', 'fornitore']:
                    worksheet.set_column(col_num, col_num, 30)
                elif col_name == 'codice':
                    worksheet.set_column(col_num, col_num, 15)
                elif col_name in ['classe', 'categoria']:
                    worksheet.set_column(col_num, col_num, 15)
                elif '_con_um' in col_name:
                    worksheet.set_column(col_num, col_num, 18)
                elif col_name.endswith('_giornaliero_fmt'):
                    worksheet.set_column(col_num, col_num, 15)
                else:
                    worksheet.set_column(col_num, col_num, 12)

            # Foglio dettaglio consumi
            df_consumi_detail = df_consumi[['codice', 'descrizione', 'data', 'reparto', 'quantita', 'mese']]
            df_consumi_detail = df_consumi_detail.sort_values(['codice', 'data'])
            df_consumi_detail.to_excel(writer, sheet_name='Dettaglio Consumi', index=False)

            # Foglio riepilogo per reparto
            df_reparti = df_consumi.pivot_table(
                index='reparto',
                columns='mese',
                values='quantita',
                aggfunc='sum',
                fill_value=0
            )

            # Aggiungi totali per riga e colonna
            df_reparti['Totale'] = df_reparti.sum(axis=1)
            df_reparti.loc['TOTALE'] = df_reparti.sum()

            # Evidenzia valori negativi nel commento
            df_reparti_styled = df_reparti.copy()
            df_reparti_styled.to_excel(writer, sheet_name='Consumi per Reparto')

            # Crea anche un foglio con solo valori negativi se ce ne sono
            valori_negativi = df_consumi[df_consumi['quantita'] < 0]
            if len(valori_negativi) > 0:
                valori_negativi.to_excel(writer, sheet_name='Rettifiche Negative', index=False)
                st.warning(f"⚠️ Trovati {len(valori_negativi)} movimenti negativi (probabili rettifiche inventario)")



        output.seek(0)

        # Download button
        st.download_button(
            label="📥 Scarica Report Excel Completo",
            data=output.getvalue(),
            file_name=f"report_economato_unificato_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("✅ Report generato con successo!")

        # Mostra anteprima con statistiche
        st.subheader("Anteprima Report")

        # Mostra statistiche chiave
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            articoli_sotto_scorta = len(df_unified[df_unified['giorni_copertura_attuali'] < giorni_copertura])
            st.metric(f"Articoli sotto {giorni_copertura} giorni", articoli_sotto_scorta)
        with col2:
            articoli_da_ordinare = len(df_unified[df_unified['da_ordinare'] > 0])
            st.metric("Articoli da ordinare", articoli_da_ordinare)
        with col3:
            valore_da_ordinare = (df_unified['da_ordinare'] * df_unified['prezzo_unitario']).sum()
            st.metric("Valore totale ordini", f"€{valore_da_ordinare:,.2f}")
        with col4:
            consumo_giornaliero_totale = df_unified['consumo_giornaliero'].sum()
            st.metric("Consumo giornaliero totale", f"{consumo_giornaliero_totale:,.0f}")

        st.dataframe(df_unified_display.head(20))

# Info section
with st.expander("ℹ️ Informazioni"):
    st.write("""
    ### Come usare questa app:
    1. **Carica il file XML delle giacenze** (Eco_SituazioneAvanzataArticoli_Giacienze.xml)
    2. **Carica il file XML dei consumi** (ECO_SituazioneConsumi_DettagliPerArticolo_tutto.xml)
    3. **Genera il report Excel** che include:
       - Foglio principale con giacenze e consumi mensili affiancati
       - Dettaglio di tutti i movimenti di consumo
       - Riepilogo consumi per reparto

    ### Il report mostra:
    - Giacenze attuali per articolo
    - Consumi mensili (Aprile, Maggio, Giugno, etc.)
    - Consumo totale e medio mensile
    - Consumo giornaliero
    - Giorni di copertura attuali
    - Suggerimento quantità da ordinare (basato sui giorni di copertura desiderati)
    """)
