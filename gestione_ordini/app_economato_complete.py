#!/usr/bin/env python
"""
HotelOPS Economato - Sistema Completo di Gestione Inventario e Consumi
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import numpy as np
import json
import re
import io
import logging
import xml.etree.ElementTree as ET

# Import report modules - commented out as not needed for core functionality
# from hotelops.reports import ExcelReportGenerator, ReportManager
# from hotelops.core.models import Article, Consumption

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# CONFIGURAZIONE PAGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="HotelOPS Economato - Gestione Completa",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# PERCORSI FILE
# -----------------------------------------------------------------------------
# Percorso base dati su Google Drive
DATA_PATH = Path("/Users/stefanodellapietra/Library/CloudStorage/GoogleDrive-stefano@panoramagroup.it/My Drive/Organized/data/economato")
GIACENZE_PATH = DATA_PATH / "giacienze"
CONSUMI_PATH = DATA_PATH / "consumi"

# File giacenze
GIACENZE_PRINCIPALE = GIACENZE_PATH / "giacenze_with_suppliers_fixed.csv"
GIACENZE_DETTAGLIO = GIACENZE_PATH / "giacenze_dettaglio_reparti_latest.csv"

# File XML (nuovo)
GIACENZE_XML = Path(__file__).parent.parent / "temp_Eco Situation July 15.xml"

# -----------------------------------------------------------------------------
# FUNZIONI DI CARICAMENTO DATI
# -----------------------------------------------------------------------------
@st.cache_data
def load_giacenze_from_xml():
    """Carica la tabella delle giacenze dal file XML."""
    if not GIACENZE_XML.exists():
        st.error(f"File XML non trovato: {GIACENZE_XML}")
        return pd.DataFrame()
    
    try:
        # Parse del file XML
        tree = ET.parse(GIACENZE_XML)
        root = tree.getroot()
        
        # Namespace
        namespace = '{Eco_SituazioneAvanzataArticoli}'
        
        # Trova tutti i Detail elements
        details = root.findall(f'.//{namespace}Detail')
        
        # Converti in lista di dizionari
        data = []
        for detail in details:
            attrs = detail.attrib
            
            # Estrai i dati principali
            record = {
                'article_id': attrs.get('CodiceArticolo', ''),
                'description': attrs.get('Descrizione', ''),
                'classe': attrs.get('Classe', ''),
                'categoria': attrs.get('Categoria', ''),
                'subcategoria': attrs.get('SubCategoria', ''),
                'supplier_name': attrs.get('RagioneSociale', ''),
                'unit_of_measure': attrs.get('UM', ''),
                'unit_price': float(attrs.get('EuroUnitazio', 0)) if attrs.get('EuroUnitazio') else 0,
                'avg_price': float(attrs.get('PrezzoMedio', 0)) if attrs.get('PrezzoMedio') else 0,
                'min_stock': float(attrs.get('ScortaSicurezza', 0)) if attrs.get('ScortaSicurezza') else 0,
                'warehouse_qty': float(attrs.get('Esistenza_1', 0)) if attrs.get('Esistenza_1') else 0,
                'department_qty': float(attrs.get('textbox19', 0)) if attrs.get('textbox19') else 0,
                'giacenza': float(attrs.get('textbox23', 0)) if attrs.get('textbox23') else 0,
                'total_value': float(attrs.get('textbox25', 0)) if attrs.get('textbox25') else 0,
                'in_ordine': float(attrs.get('InOrdine', 0)) if attrs.get('InOrdine') else 0,
                'consumi_ricette': float(attrs.get('ConsumiRicette', 0)) if attrs.get('ConsumiRicette') else 0,
                'consumi_certi': float(attrs.get('ConsumiCerti', 0)) if attrs.get('ConsumiCerti') else 0
            }
            
            data.append(record)
        
        # Crea DataFrame
        df = pd.DataFrame(data)
        
        # Aggiungi timestamp
        df['data_aggiornamento'] = datetime.now()
        df['update_timestamp'] = datetime.now()
        
        # Compatibilità con il resto dell'app
        df['fornitore'] = df['supplier_name']
        df['qty_totale'] = df['giacenza']
        df['qty_magazzino'] = df['warehouse_qty']
        df['qty_reparti'] = df['department_qty']
        df['valore_totale'] = df['total_value']
        df['valore_magazzino'] = df['warehouse_qty'] * df['avg_price']
        
        st.success(f"✅ Caricati {len(df)} articoli dal file XML")
        return df
        
    except Exception as e:
        st.error(f"Errore nel caricamento XML: {e}")
        return pd.DataFrame()


        # Gestisci la colonna data_aggiornamento se esiste
        if 'data_aggiornamento' in df.columns:
            df['data_aggiornamento'] = pd.to_datetime(df['data_aggiornamento'])
        elif 'update_timestamp' in df.columns:
            df['data_aggiornamento'] = pd.to_datetime(df['update_timestamp'])
        else:
            # Usa la data corrente se non c'è timestamp
            df['data_aggiornamento'] = datetime.now()

        # Se il dataframe ha già la colonna supplier_name, rinominala in fornitore
        if 'supplier_name' in df.columns:
            df['fornitore'] = df['supplier_name']
        # Altrimenti prova a caricare il file con fornitori corretti
        elif 'fornitore' not in df.columns:
            giacenze_with_suppliers = DATA_PATH / "giacenze/giacenze_with_suppliers_fixed.csv"
            if giacenze_with_suppliers.exists():
                try:
                    df_suppliers = pd.read_csv(giacenze_with_suppliers)
                    if 'supplier_name' in df_suppliers.columns:
                        # Crea mapping codice -> fornitore
                        supplier_map = df_suppliers.set_index('article_id')['supplier_name'].to_dict()
                        df['fornitore'] = df['article_id'].map(supplier_map).fillna('N/D')
                    else:
                        df['fornitore'] = 'N/D'
                except:
                    df['fornitore'] = 'N/D'
            else:
                # Fallback: carica dal file originale se disponibile
                original_file = Path("/Users/stefanodellapietra/Desktop/Projects/Companies/INTUR/INTUR_development/HotelOPS/modules/economato/Eco_SituazioneAvanzataArticoli_14_07_25.csv")
                if original_file.exists():
                    try:
                        df_orig = pd.read_csv(original_file, encoding='utf-8-sig')
                        if 'RagioneSociale' in df_orig.columns:
                            # Crea mapping codice -> fornitore
                            supplier_map = df_orig.set_index('CodiceArticolo')['RagioneSociale'].to_dict()
                            df['fornitore'] = df['article_id'].map(supplier_map).fillna('N/D')
                    except:
                        df['fornitore'] = 'N/D'
                else:
                    df['fornitore'] = 'N/D'

        # Crea colonne mancanti per compatibilità
        if 'qty_totale' not in df.columns:
            df['qty_totale'] = df.get('giacenza', 0)

        if 'qty_magazzino' not in df.columns:
            df['qty_magazzino'] = df.get('warehouse_qty', 0)

        if 'qty_reparti' not in df.columns:
            df['qty_reparti'] = df.get('department_qty', 0)

        # Calcola valore_totale se non esiste
        if 'valore_totale' not in df.columns:
            if 'total_value' in df.columns:
                df['valore_totale'] = df['total_value']
            else:
                # Calcola come giacenza * prezzo medio
                df['valore_totale'] = df['giacenza'] * df.get('avg_price', 0)

        # Calcola valore_magazzino se non esiste
        if 'valore_magazzino' not in df.columns:
            df['valore_magazzino'] = df['qty_magazzino'] * df.get('avg_price', 0)

        return df
    return pd.DataFrame()

@st.cache_data
def load_giacenze_principale():
    """Carica la tabella principale delle giacenze."""
    if GIACENZE_PRINCIPALE.exists():
        df = pd.read_csv(GIACENZE_PRINCIPALE)

        # Gestisci la colonna data_aggiornamento se esiste
        if 'data_aggiornamento' in df.columns:
            df['data_aggiornamento'] = pd.to_datetime(df['data_aggiornamento'])
        elif 'update_timestamp' in df.columns:
            df['data_aggiornamento'] = pd.to_datetime(df['update_timestamp'])
        else:
            # Usa la data corrente se non c'è timestamp
            df['data_aggiornamento'] = datetime.now()

        # Se il dataframe ha già la colonna supplier_name, rinominala in fornitore
        if 'supplier_name' in df.columns:
            df['fornitore'] = df['supplier_name']
        # Altrimenti prova a caricare il file con fornitori corretti
        elif 'fornitore' not in df.columns:
            giacenze_with_suppliers = DATA_PATH / "giacenze/giacenze_with_suppliers_fixed.csv"
            if giacenze_with_suppliers.exists():
                try:
                    df_suppliers = pd.read_csv(giacenze_with_suppliers)
                    if 'supplier_name' in df_suppliers.columns:
                        # Crea mapping codice -> fornitore
                        supplier_map = df_suppliers.set_index('article_id')['supplier_name'].to_dict()
                        df['fornitore'] = df['article_id'].map(supplier_map).fillna('N/D')
                    else:
                        df['fornitore'] = 'N/D'
                except:
                    df['fornitore'] = 'N/D'
            else:
                # Fallback: carica dal file originale se disponibile
                original_file = Path("/Users/stefanodellapietra/Desktop/Projects/Companies/INTUR/INTUR_development/HotelOPS/modules/economato/Eco_SituazioneAvanzataArticoli_14_07_25.csv")
                if original_file.exists():
                    try:
                        df_orig = pd.read_csv(original_file, encoding='utf-8-sig')
                        if 'RagioneSociale' in df_orig.columns:
                            # Crea mapping codice -> fornitore
                            supplier_map = df_orig.set_index('CodiceArticolo')['RagioneSociale'].to_dict()
                            df['fornitore'] = df['article_id'].map(supplier_map).fillna('N/D')
                    except:
                        df['fornitore'] = 'N/D'
                else:
                    df['fornitore'] = 'N/D'

        # Crea colonne mancanti per compatibilità
        if 'qty_totale' not in df.columns:
            df['qty_totale'] = df.get('giacenza', 0)

        if 'qty_magazzino' not in df.columns:
            df['qty_magazzino'] = df.get('warehouse_qty', 0)

        if 'qty_reparti' not in df.columns:
            df['qty_reparti'] = df.get('department_qty', 0)

        # Calcola valore_totale se non esiste
        if 'valore_totale' not in df.columns:
            if 'total_value' in df.columns:
                df['valore_totale'] = df['total_value']
            else:
                # Calcola come giacenza * prezzo medio
                df['valore_totale'] = df['giacenza'] * df.get('avg_price', 0)

        # Calcola valore_magazzino se non esiste
        if 'valore_magazzino' not in df.columns:
            df['valore_magazzino'] = df['qty_magazzino'] * df.get('avg_price', 0)

        return df
    return pd.DataFrame()

@st.cache_data
def load_giacenze_dettaglio():
    """Carica il dettaglio giacenze per reparto."""
    if GIACENZE_DETTAGLIO.exists():
        return pd.read_csv(GIACENZE_DETTAGLIO)
    return pd.DataFrame()

def parse_consumption_file(file_path, reparto_name=None, anno=None, mese=None):
    """Parse a consumption file with complex header structure."""
    try:
        # Read file without header to analyze structure
        df_raw = pd.read_excel(file_path, header=None)

        if df_raw.empty or len(df_raw) < 5:
            return None

        # Find header row
        header_row = None
        for i in range(min(10, len(df_raw))):
            row_values = df_raw.iloc[i].fillna('').astype(str)
            row_text = ' '.join(row_values).lower()

            if any(pattern in row_text for pattern in ['cod.', 'codice', 'descrizione', 'quantità', 'quantita']):
                header_row = i
                break

        if header_row is None:
            return None

        # Re-read with correct header
        df = pd.read_excel(file_path, header=header_row)
        df = df.dropna(how='all')

        # Remove rows after data (totals, notes)
        valid_rows = []
        for idx, row in df.iterrows():
            row_text = ' '.join(row.fillna('').astype(str)).lower()
            if any(pattern in row_text for pattern in ['totale', 'total', '---', '***']):
                break
            valid_rows.append(idx)

        if valid_rows:
            df = df.loc[valid_rows]

        # Normalize column names
        df.columns = df.columns.str.strip()

        # Map standard columns
        column_mapping = {
            'Cod.Art.': 'article_id',
            'Cod. Art.': 'article_id',
            'Codice': 'article_id',
            'Cod': 'article_id',
            'Descrizione': 'description',
            'Descr.': 'description',
            'Quantità': 'quantita',
            'Quantita': 'quantita',
            'Q.tà': 'quantita',
            'Qtà': 'quantita',
            'Euro': 'valore',
            'Valore': 'valore',
            'Prezzo': 'prezzo'
        }

        # Apply mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})

        # Ensure article_id exists
        if 'article_id' not in df.columns:
            for col in df.columns:
                if 'cod' in col.lower() or col.strip().startswith(('ATT.', 'BEV.', 'FOOD.', 'N.FOOD.')):
                    df = df.rename(columns={col: 'article_id'})
                    break

        if 'article_id' not in df.columns:
            return None

        # Clean article_id
        df['article_id'] = df['article_id'].astype(str).str.strip()
        df = df[df['article_id'].notna() & (df['article_id'] != '') & (df['article_id'] != 'nan')]

        # Convert numeric columns
        numeric_cols = ['quantita', 'prezzo', 'valore']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Add metadata
        if reparto_name:
            df['reparto'] = reparto_name
        if anno:
            df['anno'] = anno
        if mese:
            df['mese'] = mese

        # Remove zero quantities
        if 'quantita' in df.columns:
            df = df[df['quantita'] > 0]

        return df if not df.empty else None

    except Exception:
        return None

def normalizza_consumi_cumulativi(df, mese_corrente, reparto, valori_cumulativi):
    """
    Normalizza i consumi cumulativi convertendoli in valori mensili.

    Args:
        df: DataFrame con i consumi del mese
        mese_corrente: Numero del mese corrente
        reparto: Nome del reparto
        valori_cumulativi: Dizionario per tracciare i valori precedenti

    Returns:
        DataFrame con valori normalizzati (non cumulativi)
    """
    df_normalizzato = df.copy()

    # Per ogni articolo nel dataframe
    for idx, row in df.iterrows():
        articolo_id = row['article_id']

        # Chiave per tracciare l'articolo
        key = f"{reparto}_{articolo_id}"

        # Se abbiamo già visto questo articolo in un mese precedente
        if key in valori_cumulativi[reparto]:
            mese_prec = valori_cumulativi[reparto][key]['mese']

            # Solo se il mese corrente è successivo
            if mese_corrente > mese_prec:
                # Calcola la differenza (valore mensile reale)
                quantita_mensile = row['quantita'] - valori_cumulativi[reparto][key]['quantita']
                valore_mensile = row['valore'] - valori_cumulativi[reparto][key]['valore']

                # Se la differenza è positiva, probabilmente è cumulativo
                if quantita_mensile >= 0 and valore_mensile >= 0:
                    df_normalizzato.at[idx, 'quantita'] = quantita_mensile
                    df_normalizzato.at[idx, 'valore'] = valore_mensile

        # Aggiorna il dizionario con i valori correnti
        valori_cumulativi[reparto][key] = {
            'mese': mese_corrente,
            'quantita': row['quantita'],
            'valore': row['valore']
        }

    # Rimuovi righe con quantità zero dopo normalizzazione
    df_normalizzato = df_normalizzato[df_normalizzato['quantita'] > 0]

    return df_normalizzato

@st.cache_data
def load_consumi_data():
    """Load and process consumption data from all folders."""
    all_consumi = []
    debug_info = {"2024": {"records": 0, "total_value": 0}, "2025": {"records": 0, "total_value": 0}}

    # Mappa mesi
    mesi_nomi = {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
    }

    # Load giacenze for prices
    df_giacenze = load_giacenze_principale()
    price_map = {}
    if not df_giacenze.empty:
        price_map = df_giacenze.set_index('article_id')['avg_price'].to_dict()

    # Process 2024 - Use normalized dashboard file
    dashboard_2024 = CONSUMI_PATH / "Consumi_Economato_2024/unified /Dashboard Consumi Economato 2024.xlsx"
    if dashboard_2024.exists():
        try:
            df_2024 = pd.read_excel(dashboard_2024, sheet_name='MasterDati')

            # Rinomina colonne per compatibilità
            column_mapping = {
                'codice': 'article_id',
                'descrizione': 'description',
                'quantita': 'quantita',
                'costo': 'valore',
                'reparto': 'reparto',
                'month_int': 'mese',
                'year': 'anno'
            }
            df_2024 = df_2024.rename(columns=column_mapping)

            # Filtra solo 2024 e rimuovi righe con codice vuoto
            df_2024 = df_2024[df_2024['anno'] == 2024]
            df_2024 = df_2024[df_2024['article_id'].notna()]
            df_2024 = df_2024[df_2024['article_id'] != '']

            # Converte valori numerici
            df_2024['quantita'] = pd.to_numeric(df_2024['quantita'], errors='coerce').fillna(0)
            df_2024['valore'] = pd.to_numeric(df_2024['valore'], errors='coerce').fillna(0)

            # Se il valore è zero o mancante, calcola dai prezzi delle giacenze
            mask_no_value = (df_2024['valore'] == 0) | df_2024['valore'].isna()
            df_2024.loc[mask_no_value, 'valore'] = df_2024.loc[mask_no_value].apply(
                lambda row: row['quantita'] * price_map.get(row['article_id'], 0),
                axis=1
            )

            # Filtra quantità > 0
            df_2024 = df_2024[df_2024['quantita'] > 0]

            # Aggiungi nome mese
            df_2024['mese_nome'] = df_2024['mese'].map(mesi_nomi)

            # Seleziona colonne necessarie
            columns_to_keep = ['article_id', 'description', 'quantita', 'valore', 'reparto', 'anno', 'mese', 'mese_nome']
            df_2024 = df_2024[[col for col in columns_to_keep if col in df_2024.columns]]

            if not df_2024.empty:
                all_consumi.append(df_2024)
                debug_info["2024"]["records"] = len(df_2024)
                debug_info["2024"]["total_value"] = df_2024['valore'].sum()
                logger.info(f"Caricati {len(df_2024)} record dal dashboard 2024, valore totale: €{df_2024['valore'].sum():,.2f}")
        except Exception as e:
            logger.error(f"Errore nel caricamento dashboard 2024: {e}")

    # Dizionario per tracciare i valori cumulativi per reparto
    valori_cumulativi_2025 = {}

    # Process 2025
    consumi_2025_path = CONSUMI_PATH / "Consumi_Economato_2025"
    if consumi_2025_path.exists():
        for reparto_folder in consumi_2025_path.iterdir():
            if reparto_folder.is_dir():
                reparto_name = reparto_folder.name
                if reparto_name not in valori_cumulativi_2025:
                    valori_cumulativi_2025[reparto_name] = {}

                # Processa i file in ordine cronologico
                files = sorted(list(reparto_folder.glob("*.xlsx")))

                for file in files:
                    match = re.match(r'^(\d{2})_', file.stem)
                    if match:
                        mese_num = int(match.group(1))

                        # For 2025, files already contain reparto info
                        try:
                            # Read the file directly - it has reparto column
                            df = pd.read_excel(file)

                            if df.empty or len(df) < 1:
                                continue

                            # Check if it has the expected columns
                            if 'Codice' in df.columns and 'Reparto' in df.columns:
                                # Rename columns to standard names
                                column_mapping = {
                                    'Codice': 'article_id',
                                    'Descrizione': 'description',
                                    'Quantita': 'quantita',
                                    'Euro': 'valore',
                                    'Reparto': 'reparto'
                                }

                                df = df.rename(columns=column_mapping)

                                # Clean data
                                df['article_id'] = df['article_id'].astype(str).str.strip()
                                df = df[df['article_id'].notna() & (df['article_id'] != '') & (df['article_id'] != 'nan')]

                                # Convert numeric columns
                                numeric_cols = ['quantita', 'valore']
                                for col in numeric_cols:
                                    if col in df.columns:
                                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                                # Add metadata
                                df['anno'] = 2025
                                df['mese'] = mese_num

                                # Remove zero quantities
                                df = df[df['quantita'] > 0]

                                # Select only needed columns
                                columns_to_keep = ['article_id', 'description', 'quantita', 'valore', 'reparto', 'anno', 'mese']
                                df = df[[col for col in columns_to_keep if col in df.columns]]

                                if not df.empty:
                                    # Calcola il valore se mancante
                                    if 'valore' not in df.columns or df['valore'].sum() == 0:
                                        df['valore'] = df.apply(
                                            lambda row: row['quantita'] * price_map.get(row['article_id'], 0),
                                            axis=1
                                        )

                                    # Normalizza valori cumulativi
                                    df = normalizza_consumi_cumulativi(df, mese_num, reparto_name, valori_cumulativi_2025)

                                    debug_info["2025"]["records"] += len(df)
                                    debug_info["2025"]["total_value"] += df['valore'].sum()
                                    all_consumi.append(df)
                            else:
                                # Fall back to old parsing method if structure is different
                                df = parse_consumption_file(file, None, 2025, mese_num)
                                if df is not None:
                                    all_consumi.append(df)

                        except Exception as e:
                            # If reading fails, try the old method
                            try:
                                df = parse_consumption_file(file, None, 2025, mese_num)
                                if df is not None:
                                    all_consumi.append(df)
                            except:
                                continue

    # Combine all data
    # Combine all dataframes
    if all_consumi:
        df_consumi = pd.concat(all_consumi, ignore_index=True)

        # Add month names
        df_consumi['mese_nome'] = df_consumi['mese'].map(mesi_nomi)

        # Log riepilogo
        logger.info(f"=== RIEPILOGO CARICAMENTO DATI ===")
        logger.info(f"2024: {debug_info['2024']['records']} record, €{debug_info['2024']['total_value']:,.2f}")
        logger.info(f"2025: {debug_info['2025']['records']} record, €{debug_info['2025']['total_value']:,.2f}")
        logger.info(f"Totale: {len(df_consumi)} record")

        return df_consumi

    return pd.DataFrame()

# -----------------------------------------------------------------------------
# FUNZIONI DI UTILITÀ
# -----------------------------------------------------------------------------
def format_currency(value):
    """Formatta un valore come valuta."""
    return f"€{value:,.2f}"

def format_number(value):
    """Formatta un numero con separatori."""
    return f"{value:,.0f}"

def get_mesi_disponibili(df_consumi, anno):
    """Ottiene i mesi disponibili per un anno specifico."""
    if df_consumi.empty:
        return []

    mesi = df_consumi[df_consumi['anno'] == anno]['mese'].unique()
    return sorted(mesi)

def calcola_suggerimento_ordine(consumo_medio, giacenza_attuale, lead_time_giorni=7, stock_sicurezza_giorni=3):
    """Calcola il suggerimento di ordine basato sui consumi."""
    consumo_giornaliero = consumo_medio / 30  # Assumendo 30 giorni al mese
    consumo_durante_lead_time = consumo_giornaliero * lead_time_giorni
    stock_sicurezza = consumo_giornaliero * stock_sicurezza_giorni

    punto_riordino = consumo_durante_lead_time + stock_sicurezza

    if giacenza_attuale < punto_riordino:
        quantita_ordine = (consumo_medio * 1.5) - giacenza_attuale  # Ordina per 1.5 mesi
        return max(0, quantita_ordine)
    return 0

# -----------------------------------------------------------------------------
# COMPONENTI UI
# -----------------------------------------------------------------------------
def show_article_detail(article_id, df_giacenze_main, df_giacenze_detail, df_consumi):
    """Mostra il dettaglio completo di un articolo."""

    # Dati articolo dalle giacenze
    article_data = df_giacenze_main[df_giacenze_main['article_id'] == article_id].iloc[0]

    # Header con info articolo
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"📦 {article_data['description']}")
        st.caption(f"Codice: {article_id} | Classe: {article_data['classe']} | Categoria: {article_data['categoria']}")
    with col2:
        st.metric("Prezzo Medio", format_currency(article_data['avg_price']))
    with col3:
        st.metric("Unità di Misura", article_data['unit_of_measure'])

    # Metriche giacenze
    st.markdown("### 📊 Situazione Giacenze")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Giacenza Totale",
            format_number(article_data['qty_totale']),
            delta=f"Valore: {format_currency(article_data['valore_totale'])}"
        )

    with col2:
        st.metric(
            "In Magazzino",
            format_number(article_data['qty_magazzino']),
            delta=f"{(article_data['qty_magazzino']/article_data['qty_totale']*100):.1f}%" if article_data['qty_totale'] > 0 else "0%"
        )

    with col3:
        st.metric(
            "Nei Reparti",
            format_number(article_data['qty_reparti']),
            delta=f"{(article_data['qty_reparti']/article_data['qty_totale']*100):.1f}%" if article_data['qty_totale'] > 0 else "0%"
        )

    with col4:
        # Calcola consumo medio mensile
        consumi_articolo = df_consumi[df_consumi['article_id'] == article_id]
        if not consumi_articolo.empty:
            consumo_medio = consumi_articolo.groupby(['anno', 'mese'])['quantita'].sum().mean()
            st.metric("Consumo Medio Mensile", format_number(consumo_medio))
        else:
            consumo_medio = 0
            st.metric("Consumo Medio Mensile", "N/D")

    # Dettaglio distribuzione nei reparti
    if article_data['qty_reparti'] > 0:
        st.markdown("### 🏢 Distribuzione nei Reparti")

        detail_reparti = df_giacenze_detail[df_giacenze_detail['article_id'] == article_id]

        if not detail_reparti.empty:
            fig_reparti = px.pie(
                detail_reparti,
                values='quantita',
                names='reparto',
                title=f"Distribuzione {article_data['description']} nei Reparti"
            )
            st.plotly_chart(fig_reparti, use_container_width=True)

            # Tabella dettaglio
            st.dataframe(
                detail_reparti[['reparto', 'quantita', 'valore']].style.format({
                    'quantita': '{:.0f}',
                    'valore': '€{:.2f}'
                }),
                use_container_width=True,
                hide_index=True
            )

    # Analisi consumi
    if not consumi_articolo.empty:
        st.markdown("### 📈 Analisi Consumi")

        # Prepara dati per grafico
        consumi_mensili = consumi_articolo.groupby(['anno', 'mese', 'mese_nome']).agg({
            'quantita': 'sum',
            'valore': 'sum'
        }).reset_index()

        # Crea label per asse x
        consumi_mensili['periodo'] = consumi_mensili['mese_nome'] + ' ' + consumi_mensili['anno'].astype(str)
        consumi_mensili = consumi_mensili.sort_values(['anno', 'mese'])

        # Grafico consumi
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Quantità Consumate', 'Valore Consumi'),
            vertical_spacing=0.15,
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # Quantità
        fig.add_trace(
            go.Bar(
                x=consumi_mensili['periodo'],
                y=consumi_mensili['quantita'],
                name='Quantità',
                marker_color='lightblue',
                text=consumi_mensili['quantita'].apply(lambda x: f'{x:.0f}'),
                textposition='auto'
            ),
            row=1, col=1
        )

        # Valore
        fig.add_trace(
            go.Bar(
                x=consumi_mensili['periodo'],
                y=consumi_mensili['valore'],
                name='Valore',
                marker_color='lightgreen',
                text=consumi_mensili['valore'].apply(lambda x: f'€{x:.0f}'),
                textposition='auto'
            ),
            row=2, col=1
        )

        fig.update_xaxes(tickangle=45)
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Suggerimento ordine
        st.markdown("### 🎯 Suggerimento Ordine")

        if consumo_medio > 0:
            qty_suggerita = calcola_suggerimento_ordine(
                consumo_medio,
                article_data['qty_totale']
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Quantità Suggerita:** {qty_suggerita:.0f} {article_data['unit_of_measure']}")
            with col2:
                st.info(f"**Valore Ordine:** {format_currency(qty_suggerita * article_data['avg_price'])}")
            with col3:
                mesi_copertura = article_data['qty_totale'] / consumo_medio if consumo_medio > 0 else 0
                st.info(f"**Copertura Attuale:** {mesi_copertura:.1f} mesi")

# -----------------------------------------------------------------------------
# PAGINE PRINCIPALI
# -----------------------------------------------------------------------------
def page_dashboard(df_giacenze_main, df_giacenze_detail, df_consumi):
    """Pagina Dashboard principale."""
    st.header("📊 Dashboard Economato")

    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        valore_totale = df_giacenze_main['valore_totale'].sum() if 'valore_totale' in df_giacenze_main.columns else 0
        st.metric("Valore Totale Giacenze", format_currency(valore_totale))

    with col2:
        n_articoli = len(df_giacenze_main)
        n_con_giacenza = (df_giacenze_main['qty_totale'] > 0).sum()
        st.metric("Articoli Totali", f"{n_articoli}", delta=f"{n_con_giacenza} con giacenza")

    with col3:
        valore_magazzino = df_giacenze_main['valore_magazzino'].sum() if 'valore_magazzino' in df_giacenze_main.columns else 0
        perc_magazzino = (valore_magazzino / valore_totale * 100) if valore_totale > 0 else 0
        st.metric("Valore in Magazzino", format_currency(valore_magazzino), delta=f"{perc_magazzino:.1f}%")

    with col4:
        if not df_consumi.empty:
            ultimo_mese = df_consumi.groupby(['anno', 'mese'])['valore'].sum().iloc[-1]
            st.metric("Consumi Ultimo Mese", format_currency(ultimo_mese))
        else:
            st.metric("Consumi Ultimo Mese", "N/D")

    st.markdown("---")

    # Grafici principali
    col1, col2 = st.columns(2)

    with col1:
        # Top articoli per valore
        top_articoli = df_giacenze_main.nlargest(10, 'valore_totale')
        fig = px.bar(
            top_articoli,
            x='valore_totale',
            y='description',
            orientation='h',
            title='Top 10 Articoli per Valore in Giacenza',
            labels={'valore_totale': 'Valore (€)', 'description': 'Articolo'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Distribuzione valore per reparto
        if not df_giacenze_detail.empty:
            valore_reparti = df_giacenze_detail.groupby('reparto')['valore'].sum().reset_index()
            valore_reparti = valore_reparti.sort_values('valore', ascending=False).head(10)

            fig = px.pie(
                valore_reparti,
                values='valore',
                names='reparto',
                title='Distribuzione Valore per Reparto (Top 10)',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)

    # Trend consumi
    if not df_consumi.empty:
        st.markdown("### 📈 Trend Consumi")

        # Aggrega consumi per mese
        trend_consumi = df_consumi.groupby(['anno', 'mese', 'mese_nome']).agg({
            'quantita': 'sum',
            'valore': 'sum'
        }).reset_index()

        trend_consumi['periodo'] = trend_consumi['mese_nome'] + ' ' + trend_consumi['anno'].astype(str)
        trend_consumi = trend_consumi.sort_values(['anno', 'mese'])

        fig = px.line(
            trend_consumi,
            x='periodo',
            y='valore',
            title='Andamento Valore Consumi Mensili',
            markers=True
        )
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

def page_inventory_analysis(df_giacenze_main, df_giacenze_detail, df_consumi):
    """Pagina analisi inventario con ricerca articoli."""
    st.header("🔍 Analisi Inventario")

    # Barra di ricerca e filtri
    col1, col2 = st.columns([3, 1])

    with col1:
        search_term = st.text_input(
            "🔍 Cerca articolo",
            placeholder="Inserisci codice o descrizione..."
        )

    with col2:
        # Filtro fornitore principale
        fornitori_disponibili = sorted(df_giacenze_main['fornitore'].unique()) if 'fornitore' in df_giacenze_main.columns else []
        filter_fornitore = st.selectbox(
            "Fornitore",
            ["Tutti"] + fornitori_disponibili
        )

    # Seconda riga di filtri
    col3, col4 = st.columns([1, 1])

    with col3:
        filter_classe = st.selectbox(
            "Classe",
            ["Tutte"] + sorted(df_giacenze_main['classe'].unique())
        )

    with col4:
        if filter_classe != "Tutte":
            categorie_disponibili = sorted(df_giacenze_main[df_giacenze_main['classe'] == filter_classe]['categoria'].unique())
        else:
            categorie_disponibili = sorted(df_giacenze_main['categoria'].unique())

        filter_categoria = st.selectbox(
            "Categoria",
            ["Tutte"] + categorie_disponibili
        )

    # Applica filtri
    df_filtered = df_giacenze_main.copy()

    if search_term:
        mask = (
            df_filtered['article_id'].str.contains(search_term, case=False, na=False) |
            df_filtered['description'].str.contains(search_term, case=False, na=False)
        )
        df_filtered = df_filtered[mask]

    if filter_fornitore != "Tutti" and 'fornitore' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['fornitore'] == filter_fornitore]

    if filter_classe != "Tutte":
        df_filtered = df_filtered[df_filtered['classe'] == filter_classe]

    if filter_categoria != "Tutte":
        df_filtered = df_filtered[df_filtered['categoria'] == filter_categoria]

    # Mostra risultati
    st.info(f"Trovati {len(df_filtered)} articoli")

    # Selezione articolo per dettaglio
    if not df_filtered.empty:
        # Crea lista di articoli con codice e descrizione
        articoli_lista = df_filtered.apply(
            lambda x: f"{x['article_id']} - {x['description']}", axis=1
        ).tolist()

        selected_article_str = st.selectbox(
            "Seleziona un articolo per vedere il dettaglio:",
            [""] + articoli_lista
        )

        if selected_article_str:
            # Estrai il codice articolo
            selected_article_id = selected_article_str.split(" - ")[0]

            st.markdown("---")
            show_article_detail(selected_article_id, df_giacenze_main, df_giacenze_detail, df_consumi)

    # Tabella riepilogativa
    st.markdown("### 📋 Tabella Articoli")

    # Prepara dati per visualizzazione
    display_cols = [
        'article_id', 'description', 'fornitore', 'classe', 'categoria',
        'unit_of_measure', 'avg_price', 'giacenza', 'valore_totale'
    ]

    # Aggiungi fornitore se non presente nelle colonne
    if 'fornitore' not in df_filtered.columns:
        display_cols.remove('fornitore')

    # Verifica che tutte le colonne esistano
    display_cols = [col for col in display_cols if col in df_filtered.columns]

    df_display = df_filtered[display_cols].copy()

    # Aggiungi colonna consumo medio se disponibile
    if not df_consumi.empty:
        consumo_medio = df_consumi.groupby('article_id')['quantita'].mean().reset_index()
        consumo_medio.columns = ['article_id', 'consumo_medio']
        df_display = df_display.merge(consumo_medio, on='article_id', how='left')
        df_display['consumo_medio'] = df_display['consumo_medio'].fillna(0)

        # Calcola mesi di copertura
        df_display['mesi_copertura'] = df_display.apply(
            lambda x: x['giacenza'] / x['consumo_medio'] if x['consumo_medio'] > 0 else np.inf,
            axis=1
        )

    # Formatta per display
    format_dict = {}
    if 'avg_price' in df_display.columns:
        format_dict['avg_price'] = '€{:.2f}'
    if 'valore_totale' in df_display.columns:
        format_dict['valore_totale'] = '€{:,.2f}'
    if 'qty_magazzino' in df_display.columns:
        format_dict['qty_magazzino'] = '{:.0f}'
    if 'qty_reparti' in df_display.columns:
        format_dict['qty_reparti'] = '{:.0f}'
    if 'qty_totale' in df_display.columns:
        format_dict['qty_totale'] = '{:.0f}'
    if 'giacenza' in df_display.columns:
        format_dict['giacenza'] = '{:.0f}'
    if 'consumo_medio' in df_display.columns:
        format_dict['consumo_medio'] = '{:.1f}'
    if 'mesi_copertura' in df_display.columns:
        format_dict['mesi_copertura'] = '{:.1f}'

    st.dataframe(
        df_display.style.format(format_dict),
        use_container_width=True,
        hide_index=True
    )

    # Download CSV
    csv = df_display.to_csv(index=False)
    st.download_button(
        "📥 Scarica CSV",
        csv,
        f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )

def page_consumption_analysis(df_consumi):
    """Analizza i consumi con grafici e statistiche."""
    st.title("📈 Analisi Consumi")

    if df_consumi.empty:
        st.warning("Nessun dato di consumo disponibile")
        return

    # Tabs per diverse visualizzazioni
    tab_overview, tab_temporal, tab_reparti = st.tabs(["📊 Overview", "📅 Analisi Temporale", "🏢 Per Reparto"])

    with tab_overview:
        # Filtri
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            anni_disponibili = sorted(df_consumi['anno'].unique())
            selected_anno = st.selectbox("Anno", anni_disponibili)

        with col2:
            mesi_disponibili = get_mesi_disponibili(df_consumi, selected_anno)
            mesi_nomi = {
                1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
                5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
                9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
            }
            mesi_options = ["Tutti"] + [mesi_nomi.get(m, str(m)) for m in mesi_disponibili]
            selected_mese = st.selectbox("Mese", mesi_options)

        with col3:
            reparti_disponibili = sorted([str(r) for r in df_consumi['reparto'].unique() if pd.notna(r)])
            selected_reparto = st.selectbox("Reparto", ["Tutti"] + reparti_disponibili)

        # Applica filtri
        df_filtered = df_consumi[df_consumi['anno'] == selected_anno].copy()

        if selected_mese != "Tutti":
            # Trova il numero del mese dal nome
            mese_num = None
            for num, nome in mesi_nomi.items():
                if nome == selected_mese:
                    mese_num = num
                    break
            if mese_num:
                df_filtered = df_filtered[df_filtered['mese'] == mese_num]

        if selected_reparto != "Tutti":
            df_filtered = df_filtered[df_filtered['reparto'] == selected_reparto]

        # Metriche
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            valore_totale = df_filtered['valore'].sum()
            st.metric("Valore Totale Consumi", format_currency(valore_totale))

        with col2:
            quantita_totale = df_filtered['quantita'].sum()
            st.metric("Quantità Totale", format_number(quantita_totale))

        with col3:
            articoli_unici = df_filtered['article_id'].nunique()
            st.metric("Articoli Consumati", format_number(articoli_unici))

        with col4:
            if selected_reparto == "Tutti":
                reparti_attivi = df_filtered['reparto'].nunique()
                st.metric("Reparti Attivi", format_number(reparti_attivi))
            else:
                transazioni = len(df_filtered)
                st.metric("Transazioni", format_number(transazioni))

        # Grafici
        st.markdown("---")

        # Top articoli consumati
        st.subheader("🏆 Top Articoli Consumati")

        top_articoli = df_filtered.groupby(['article_id', 'description']).agg({
            'quantita': 'sum',
            'valore': 'sum'
        }).reset_index()

        col1, col2 = st.columns(2)

        with col1:
            # Top per valore
            top_valore = top_articoli.nlargest(10, 'valore')
            fig = px.bar(
                top_valore,
                x='valore',
                y='description',
                orientation='h',
                title='Top 10 per Valore',
                labels={'valore': 'Valore (€)', 'description': 'Articolo'}
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top per quantità
            top_quantita = top_articoli.nlargest(10, 'quantita')
            fig = px.bar(
                top_quantita,
                x='quantita',
                y='description',
                orientation='h',
                title='Top 10 per Quantità',
                labels={'quantita': 'Quantità', 'description': 'Articolo'},
                color_discrete_sequence=['lightcoral']
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        # Analisi per reparto
        if selected_reparto == "Tutti":
            st.markdown("---")
            st.subheader("📊 Consumi per Reparto")

            consumi_reparto = df_filtered.groupby('reparto').agg({
                'valore': 'sum',
                'quantita': 'sum',
                'article_id': 'nunique'
            }).reset_index()

            consumi_reparto.columns = ['Reparto', 'Valore', 'Quantità', 'Articoli Unici']
            consumi_reparto = consumi_reparto.sort_values('Valore', ascending=False)

            # Grafico - verifica che ci siano dati
            if not consumi_reparto.empty:
                fig = px.treemap(
                    consumi_reparto,
                    path=['Reparto'],
                    values='Valore',
                    title='Distribuzione Consumi per Reparto',
                    hover_data=['Quantità', 'Articoli Unici']
                )

            else:
                st.info("Nessun dato disponibile per il periodo selezionato")

            if not consumi_reparto.empty:
                st.plotly_chart(fig, use_container_width=True)

            # Tabella
            st.dataframe(
                consumi_reparto.style.format({
                    'Valore': '€{:,.2f}',
                    'Quantità': '{:,.0f}',
                    'Articoli Unici': '{:,.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )

    with tab_temporal:
        st.subheader("📅 Analisi Temporale Completa")

        # Opzioni visualizzazione
        col1, col2, col3 = st.columns(3)
        with col1:
            view_type = st.selectbox(
                "Tipo Vista",
                ["Grafico Linea", "Grafico Barre", "Tabella Pivot", "Heatmap"]
            )
        with col2:
            metric_type = st.selectbox(
                "Metrica",
                ["Valore (€)", "Quantità", "N° Articoli Unici"]
            )
        with col3:
            show_all_months = st.checkbox("Mostra tutti i mesi (inclusi zero)", value=False)

        # Prepara dati temporali completi
        # Crea range completo di mesi
        all_months = []
        anni = sorted(df_consumi['anno'].unique())
        for anno in anni:
            for mese in range(1, 13):
                all_months.append({'anno': anno, 'mese': mese})

        df_all_months = pd.DataFrame(all_months)

        # Aggrega dati per mese
        consumi_mensili = df_consumi.groupby(['anno', 'mese']).agg({
            'valore': 'sum',
            'quantita': 'sum',
            'article_id': 'nunique'
        }).reset_index()

        # Merge con tutti i mesi
        if show_all_months:
            consumi_mensili = df_all_months.merge(
                consumi_mensili,
                on=['anno', 'mese'],
                how='left'
            ).fillna(0)

        # Aggiungi nome mese
        mesi_nomi = {
            1: 'Gen', 2: 'Feb', 3: 'Mar', 4: 'Apr',
            5: 'Mag', 6: 'Giu', 7: 'Lug', 8: 'Ago',
            9: 'Set', 10: 'Ott', 11: 'Nov', 12: 'Dic'
        }
        consumi_mensili['mese_nome'] = consumi_mensili['mese'].map(mesi_nomi)
        consumi_mensili['periodo'] = consumi_mensili['anno'].astype(str) + '-' + consumi_mensili['mese'].astype(str).str.zfill(2)
        consumi_mensili['periodo_label'] = consumi_mensili['mese_nome'] + ' ' + consumi_mensili['anno'].astype(str)

        # Seleziona metrica
        if metric_type == "Valore (€)":
            metric_col = 'valore'
            format_str = '€{:,.0f}'
        elif metric_type == "Quantità":
            metric_col = 'quantita'
            format_str = '{:,.0f}'
        else:
            metric_col = 'article_id'
            format_str = '{:,.0f}'

        consumi_mensili = consumi_mensili.sort_values(['anno', 'mese'])

        if view_type == "Grafico Linea":
            fig = px.line(
                consumi_mensili,
                x='periodo_label',
                y=metric_col,
                title=f'Trend {metric_type} nel Tempo',
                markers=True,
                text=metric_col
            )
            fig.update_traces(texttemplate=format_str, textposition="top center")
            fig.update_xaxes(tickangle=45)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif view_type == "Grafico Barre":
            fig = px.bar(
                consumi_mensili,
                x='periodo_label',
                y=metric_col,
                title=f'{metric_type} per Mese',
                text=metric_col
            )
            fig.update_traces(texttemplate=format_str, textposition="outside")
            fig.update_xaxes(tickangle=45)
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif view_type == "Tabella Pivot":
            # Pivot per anno/mese
            pivot_data = consumi_mensili.pivot(
                index='mese_nome',
                columns='anno',
                values=metric_col
            ).fillna(0)

            # Riordina i mesi
            mesi_ordinati = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                           'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
            pivot_data = pivot_data.reindex(mesi_ordinati)

            # Aggiungi totali
            pivot_data['TOTALE'] = pivot_data.sum(axis=1)
            totali_anno = pivot_data.sum()
            totali_anno.name = 'TOTALE'
            pivot_data = pd.concat([pivot_data, pd.DataFrame([totali_anno])])

            # Formatta valori
            if metric_type == "Valore (€)":
                st.dataframe(
                    pivot_data.style.format('€{:,.0f}').background_gradient(cmap='YlOrRd'),
                    use_container_width=True
                )
            else:
                st.dataframe(
                    pivot_data.style.format('{:,.0f}').background_gradient(cmap='YlOrRd'),
                    use_container_width=True
                )

            # Statistiche
            col1, col2, col3 = st.columns(3)
            with col1:
                media_mensile = consumi_mensili[metric_col].mean()
                st.metric("Media Mensile", format_str.format(media_mensile))
            with col2:
                max_mese = consumi_mensili.loc[consumi_mensili[metric_col].idxmax()]
                st.metric("Mese Picco", f"{max_mese['periodo_label']}",
                         f"{format_str.format(max_mese[metric_col])}")
            with col3:
                trend = (consumi_mensili[metric_col].iloc[-1] - consumi_mensili[metric_col].iloc[-2]) / consumi_mensili[metric_col].iloc[-2] * 100 if len(consumi_mensili) > 1 else 0
                st.metric("Trend Ultimo Mese", f"{trend:+.1f}%")

        else:  # Heatmap
            # Prepara dati per heatmap
            heatmap_data = consumi_mensili.pivot(
                index='mese_nome',
                columns='anno',
                values=metric_col
            ).fillna(0)

            # Riordina i mesi
            mesi_ordinati = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                           'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
            heatmap_data = heatmap_data.reindex(mesi_ordinati)

            fig = px.imshow(
                heatmap_data.values,
                labels=dict(x="Anno", y="Mese", color=metric_type),
                x=heatmap_data.columns,
                y=heatmap_data.index,
                title=f'Heatmap {metric_type}',
                color_continuous_scale='YlOrRd',
                text_auto=True
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

        # Export dati temporali
        st.markdown("### 💾 Export Dati Temporali")
        csv = consumi_mensili.to_csv(index=False)
        st.download_button(
            label="📥 Scarica dati temporali CSV",
            data=csv,
            file_name=f"consumi_temporali_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )

    with tab_reparti:
        st.subheader("🏢 Analisi per Reparto")

        # Filtro periodo per analisi reparti
        col1, col2 = st.columns(2)
        with col1:
            anno_reparto = st.selectbox("Anno", sorted(df_consumi['anno'].unique()), key='anno_reparto')
        with col2:
            mese_reparto = st.selectbox(
                "Mese",
                ["Tutti"] + [mesi_nomi.get(m, str(m)) for m in sorted(df_consumi[df_consumi['anno'] == anno_reparto]['mese'].unique())],
                key='mese_reparto'
            )

        # Filtra dati
        df_reparti = df_consumi[df_consumi['anno'] == anno_reparto].copy()
        if mese_reparto != "Tutti":
            mese_num = None
            for num, nome in mesi_nomi.items():
                if nome == mese_reparto:
                    mese_num = num
                    break
            if mese_num:
                df_reparti = df_reparti[df_reparti['mese'] == mese_num]

        # Analisi per reparto
        consumi_reparto = df_reparti.groupby('reparto').agg({
            'valore': 'sum',
            'quantita': 'sum',
            'article_id': 'nunique'
        }).reset_index()

        consumi_reparto.columns = ['Reparto', 'Valore', 'Quantità', 'Articoli Unici']
        consumi_reparto = consumi_reparto.sort_values('Valore', ascending=False)

        # Visualizzazioni
        col1, col2 = st.columns(2)

        with col1:
            # Grafico a torta
            fig = px.pie(
                consumi_reparto,
                values='Valore',
                names='Reparto',
                title='Distribuzione Valore per Reparto'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top reparti
            fig = px.bar(
                consumi_reparto.head(10),
                x='Valore',
                y='Reparto',
                orientation='h',
                title='Top 10 Reparti per Valore',
                text='Valore'
            )
            fig.update_traces(texttemplate='€%{text:,.0f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        # Tabella dettagliata
        st.markdown("### 📋 Dettaglio Consumi per Reparto")
        st.dataframe(
            consumi_reparto.style.format({
                'Valore': '€{:,.2f}',
                'Quantità': '{:,.0f}',
                'Articoli Unici': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )

def page_data_analysis(df_consumi):
    """Pagina di analisi dati per debug."""
    st.header("🔍 Analisi Dati (Debug)")

    if df_consumi.empty:
        st.warning("Nessun dato di consumo disponibile")
        return

    # Tab per diverse analisi
    tab1, tab2, tab3 = st.tabs(["Riepilogo Mensile", "Analisi Anomalie", "Dati Raw"])

    with tab1:
        st.subheader("Riepilogo Consumi Mensili")

        # Aggregazione per anno e mese
        riepilogo = df_consumi.groupby(['anno', 'mese', 'mese_nome']).agg({
            'quantita': 'sum',
            'valore': 'sum',
            'article_id': 'count'
        }).reset_index()
        riepilogo.columns = ['Anno', 'Mese', 'Nome Mese', 'Quantità Tot', 'Valore Tot', 'N. Righe']
        riepilogo = riepilogo.sort_values(['Anno', 'Mese'])

        # Calcola differenze mese su mese
        riepilogo['Diff Valore'] = riepilogo.groupby('Anno')['Valore Tot'].diff()
        riepilogo['% Diff'] = (riepilogo['Diff Valore'] / riepilogo['Valore Tot'].shift(1) * 100).round(1)

        st.dataframe(
            riepilogo.style.format({
                'Quantità Tot': '{:,.0f}',
                'Valore Tot': '€{:,.2f}',
                'N. Righe': '{:,}',
                'Diff Valore': '€{:,.2f}',
                '% Diff': '{:.1f}%'
            }),
            use_container_width=True
        )

        # Grafico confronto anni
        fig = px.bar(
            riepilogo,
            x='Nome Mese',
            y='Valore Tot',
            color='Anno',
            title='Confronto Valori Mensili per Anno',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Analisi Anomalie")

        # Cerca articoli con valori anomali
        col1, col2 = st.columns(2)

        with col1:
            # Top 10 articoli per valore nel 2025
            df_2025 = df_consumi[df_consumi['anno'] == 2025]
            if not df_2025.empty:
                top_2025 = df_2025.groupby(['article_id', 'description'])['valore'].sum().reset_index()
                top_2025 = top_2025.nlargest(10, 'valore')

                st.markdown("**Top 10 Articoli 2025 per Valore**")
                st.dataframe(
                    top_2025.style.format({'valore': '€{:,.2f}'}),
                    use_container_width=True
                )

        with col2:
            # Articoli con maggior incremento 2024 vs 2025
            if 2024 in df_consumi['anno'].unique() and 2025 in df_consumi['anno'].unique():
                confronto = df_consumi.groupby(['anno', 'article_id'])['valore'].sum().reset_index()
                confronto_pivot = confronto.pivot(index='article_id', columns='anno', values='valore').fillna(0)
                confronto_pivot['diff'] = confronto_pivot[2025] - confronto_pivot.get(2024, 0)
                confronto_pivot['perc'] = (confronto_pivot['diff'] / confronto_pivot.get(2024, 1) * 100).replace([np.inf, -np.inf], 999)

                top_incrementi = confronto_pivot.nlargest(10, 'diff')
                st.markdown("**Top 10 Incrementi 2025 vs 2024**")
                st.dataframe(
                    top_incrementi.style.format({
                        2024: '€{:,.2f}',
                        2025: '€{:,.2f}',
                        'diff': '€{:,.2f}',
                        'perc': '{:.0f}%'
                    }),
                    use_container_width=True
                )

    with tab3:
        st.subheader("Dati Raw")

        # Filtri
        col1, col2, col3 = st.columns(3)
        with col1:
            anno_sel = st.selectbox("Anno", sorted(df_consumi['anno'].unique()))
        with col2:
            mese_sel = st.selectbox("Mese", sorted(df_consumi[df_consumi['anno'] == anno_sel]['mese'].unique()))
        with col3:
            reparto_sel = st.selectbox("Reparto", ["Tutti"] + sorted([str(r) for r in df_consumi['reparto'].unique() if pd.notna(r)]))

        # Filtra dati
        df_filtered = df_consumi[
            (df_consumi['anno'] == anno_sel) &
            (df_consumi['mese'] == mese_sel)
        ]
        if reparto_sel != "Tutti":
            df_filtered = df_filtered[df_filtered['reparto'] == reparto_sel]

        # Statistiche
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Righe", len(df_filtered))
        with col2:
            st.metric("Articoli Unici", df_filtered['article_id'].nunique())
        with col3:
            st.metric("Valore Totale", f"€{df_filtered['valore'].sum():,.2f}")
        with col4:
            st.metric("Valore Medio", f"€{df_filtered['valore'].mean():,.2f}")

        # Mostra dati
        st.dataframe(
            df_filtered[['article_id', 'description', 'reparto', 'quantita', 'valore']].style.format({
                'quantita': '{:.2f}',
                'valore': '€{:.2f}'
            }),
            use_container_width=True,
            height=400
        )

# -----------------------------------------------------------------------------
# PAGINA REPORT EXCEL
# -----------------------------------------------------------------------------
def page_excel_reports(df_giacenze_main, df_giacenze_detail, df_consumi):
    """Genera report Excel con filtri e analisi dettagliate."""
    st.title("📄 Report Excel Inventario e Consumi")

    st.markdown("""
    Genera report Excel professionali con:
    - **Dati completi** di giacenze e consumi
    - **Filtri automatici** per reparto, classe, fornitore
    - **Analisi consumi mensili** per ogni articolo
    - **Grafici e dashboard** integrati
    """)

    # Sezione Generazione Report
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("🔧 Configurazione Report")

        # Tipo di report
        report_type = st.selectbox(
            "Tipo di Report",
            [
                "Report Completo",
                "Solo Articoli Sotto Scorta",
                "Top 50 Articoli per Valore",
                "Articoli Movimento Veloce",
                "Report Personalizzato"
            ]
        )

        # Filtri personalizzati
        if report_type == "Report Personalizzato":
            st.markdown("**Applica Filtri:**")

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                # Filtro reparto
                reparti = ["Tutti"] + sorted(df_consumi['REPARTO'].unique().tolist()) if not df_consumi.empty else ["Tutti"]
                selected_reparto = st.selectbox("Reparto", reparti)

            with filter_col2:
                # Filtro fornitore
                fornitori = ["Tutti"] + sorted(df_giacenze_main['FORNITORE'].dropna().unique().tolist())
                selected_fornitore = st.selectbox("Fornitore", fornitori)

            with filter_col3:
                # Filtro periodo consumi
                if not df_consumi.empty:
                    min_date = pd.to_datetime(df_consumi['DATA']).min()
                    max_date = pd.to_datetime(df_consumi['DATA']).max()
                    date_range = st.date_input(
                        "Periodo Consumi",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date
                    )

        # Opzioni aggiuntive
        st.markdown("**Opzioni Report:**")
        opt_col1, opt_col2 = st.columns(2)

        with opt_col1:
            include_charts = st.checkbox("Includi Grafici", value=True)
            include_pivot = st.checkbox("Includi Pivot Mensile", value=True)

        with opt_col2:
            include_summary = st.checkbox("Includi Dashboard Riepilogo", value=True)
            highlight_critical = st.checkbox("Evidenzia Articoli Critici", value=True)

    with col2:
        st.subheader("📥 Genera Report")

        if st.button("🚀 Genera Report Excel", type="primary", use_container_width=True):
            with st.spinner("Generazione report in corso..."):
                try:
                    # Prepara i dati per il report
                    articles = []
                    consumptions = []

                    # Converti DataFrame giacenze in Article objects
                    for _, row in df_giacenze_main.iterrows():
                        article = Article(
                            article_id=str(row['COD_ART']),
                            description=row['DESCRIZIONE'],
                            supplier=row.get('FORNITORE'),
                            warehouse_qty=float(row.get('QTA_GIAC_MAG', 0)),
                            department_qty=float(row.get('QTA_GIAC_REP', 0)),
                            giacenza=float(row.get('QTA_GIAC', 0)),
                            unit_of_measure=row.get('UNITA_MISURA'),
                            unit_price=float(row.get('PREZZO_LISTINO', 0)) if pd.notna(row.get('PREZZO_LISTINO')) else None,
                            avg_price=float(row.get('PREZZO_MEDIO', 0)) if pd.notna(row.get('PREZZO_MEDIO')) else None,
                            min_stock=float(row.get('SCORTA_MINIMA', 0)) if pd.notna(row.get('SCORTA_MINIMA')) else None
                        )

                        # Applica filtri
                        if report_type == "Report Personalizzato":
                            if selected_fornitore != "Tutti" and article.supplier != selected_fornitore:
                                continue

                        articles.append(article)

                    # Converti DataFrame consumi in Consumption objects
                    if not df_consumi.empty:
                        for _, row in df_consumi.iterrows():
                            consumption = Consumption(
                                article_id=str(row['COD_ART']),
                                description=row['DESCRIZIONE'],
                                consumption_month=pd.to_datetime(row['DATA']).date().replace(day=1),
                                consumption_qty=float(row['CONSUMO_QUANTITA']),
                                department=row['REPARTO'],
                                cost=float(row.get('COSTO_CONSUMI', 0)) if pd.notna(row.get('COSTO_CONSUMI')) else None
                            )

                            # Applica filtri
                            if report_type == "Report Personalizzato":
                                if selected_reparto != "Tutti" and consumption.department != selected_reparto:
                                    continue
                                if 'date_range' in locals() and len(date_range) == 2:
                                    if not (date_range[0] <= consumption.consumption_month <= date_range[1]):
                                        continue

                            consumptions.append(consumption)

                    # Filtra per tipo di report
                    if report_type == "Solo Articoli Sotto Scorta":
                        articles = [a for a in articles if a.giacenza < (a.min_stock or 10)]
                    elif report_type == "Top 50 Articoli per Valore":
                        articles = sorted(articles,
                                        key=lambda x: x.giacenza * (x.avg_price or x.unit_price or 0),
                                        reverse=True)[:50]
                    elif report_type == "Articoli Movimento Veloce":
                        # Calcola consumo totale per articolo
                        cons_by_article = {}
                        for c in consumptions:
                            cons_by_article[c.article_id] = cons_by_article.get(c.article_id, 0) + c.consumption_qty

                        # Ordina articoli per consumo
                        fast_moving_ids = sorted(cons_by_article.items(), key=lambda x: x[1], reverse=True)[:50]
                        fast_moving_ids = [x[0] for x in fast_moving_ids]
                        articles = [a for a in articles if a.article_id in fast_moving_ids]

                    # Genera report
                    generator = ExcelReportGenerator()
                    report_path = generator.generate_report(
                        articles=articles,
                        consumptions=consumptions,
                        include_charts=include_charts
                    )

                    # Leggi il file generato
                    with open(report_path, 'rb') as f:
                        excel_data = f.read()

                    # Offri download
                    st.success("✅ Report generato con successo!")

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"inventory_report_{report_type.lower().replace(' ', '_')}_{timestamp}.xlsx"

                    st.download_button(
                        label="📥 Scarica Report Excel",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                    # Mostra anteprima
                    st.info(f"""
                    **Report Generato:**
                    - Articoli inclusi: {len(articles)}
                    - Record consumi: {len(consumptions)}
                    - Fogli inclusi: Inventario, Riepilogo, Consumi Mensili
                    {"- Grafici: ✓" if include_charts else ""}
                    """)

                except Exception as e:
                    st.error(f"Errore nella generazione del report: {str(e)}")
                    logger.error(f"Errore generazione report: {str(e)}", exc_info=True)

    # Sezione Aggiornamento da XML
    st.markdown("---")
    st.subheader("🔄 Aggiornamento da File XML Giacenze")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        Carica un file XML con le giacenze aggiornate per:
        - Aggiornare automaticamente le quantità in magazzino
        - Generare un report con i dati aggiornati
        - Tenere traccia delle modifiche
        """)

        uploaded_file = st.file_uploader(
            "Seleziona file XML giacenze",
            type=['xml', 'XML'],
            help="File XML con struttura giacenze"
        )

    with col2:
        if uploaded_file is not None:
            if st.button("📤 Aggiorna e Genera Report", type="secondary", use_container_width=True):
                with st.spinner("Elaborazione file XML..."):
                    try:
                        # Salva temporaneamente il file
                        temp_path = Path(f"temp_{uploaded_file.name}")
                        with open(temp_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())

                        # Processa con ReportManager
                        report_manager = ReportManager()
                        update_results = report_manager.update_from_xml_giacenze(temp_path)

                        # Rimuovi file temporaneo
                        temp_path.unlink()

                        # Mostra risultati
                        st.success("✅ Aggiornamento completato!")

                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("Articoli Totali", update_results['total_items'])
                        with col_stat2:
                            st.metric("Aggiornati", update_results['updated_items'])
                        with col_stat3:
                            st.metric("Nuovi", update_results['new_items'])

                        if update_results.get('errors'):
                            st.warning(f"⚠️ {len(update_results['errors'])} errori durante l'elaborazione")
                            with st.expander("Vedi errori"):
                                for error in update_results['errors']:
                                    st.text(error)

                        # Download report aggiornato
                        if 'report_path' in update_results:
                            with open(update_results['report_path'], 'rb') as f:
                                excel_data = f.read()

                            st.download_button(
                                label="📥 Scarica Report Aggiornato",
                                data=excel_data,
                                file_name=f"inventory_updated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

                    except Exception as e:
                        st.error(f"Errore nell'elaborazione del file XML: {str(e)}")
                        logger.error(f"Errore XML: {str(e)}", exc_info=True)

    # Sezione Report Programmati
    st.markdown("---")
    st.subheader("⏰ Report Programmati")

    st.info("""
    **Prossimamente:** Possibilità di programmare generazione automatica di report
    - Report settimanali di scorte basse
    - Report mensili di consumi
    - Alert automatici per articoli critici
    """)


# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main():
    """Main application entry point."""

    # Sidebar
    st.sidebar.image(
        "https://via.placeholder.com/200x100/1f77b4/ffffff?text=HotelOPS",
        use_container_width=True
    )
    st.sidebar.title("🏨 HotelOPS Economato")
    st.sidebar.markdown("Sistema Gestione Inventario")

    # Selezione fonte dati
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Fonte Dati")
    
    use_xml = st.sidebar.checkbox("📄 Usa dati XML (più recenti)", value=True)
    
    if use_xml and not GIACENZE_XML.exists():
        st.sidebar.error("❌ File XML non trovato")
        use_xml = False

    # Carica dati
    with st.spinner("Caricamento dati in corso..."):
        if use_xml:
            st.sidebar.info("📄 Caricando da XML...")
            df_giacenze_main = load_giacenze_from_xml()
            df_giacenze_detail = load_giacenze_dettaglio()  # Ancora da CSV
        else:
            st.sidebar.info("📊 Caricando da CSV...")
            df_giacenze_main = load_giacenze_principale()
            df_giacenze_detail = load_giacenze_dettaglio()

        # Clear cache for fresh data loading
        st.cache_data.clear()
        df_consumi = load_consumi_data()

        # Debug info
        if not df_consumi.empty:
            st.sidebar.markdown("### 📊 Dati Caricati")
            st.sidebar.info(f"Consumi totali: {len(df_consumi)} record")
        else:
            st.sidebar.warning("⚠️ Nessun dato consumi trovato")

    # Verifica dati
    if df_giacenze_main.empty:
        st.error("❌ Nessun dato giacenze trovato. Verifica i file.")
        st.stop()

    # Info ultimo aggiornamento
    if 'data_aggiornamento' in df_giacenze_main.columns and not df_giacenze_main.empty:
        last_update = df_giacenze_main['data_aggiornamento'].iloc[0]
        if pd.notna(last_update):
            st.sidebar.info(f"📅 Ultimo aggiornamento giacenze:\n{last_update.strftime('%d/%m/%Y %H:%M')}")

    # Menu navigazione
    st.sidebar.markdown("---")
    st.sidebar.header("📋 Menu")

    page = st.sidebar.radio(
        "Seleziona pagina",
        [
            "🏠 Dashboard",
            "🔍 Analisi Inventario",
            "📈 Analisi Consumi",
            "📦 Suggerimenti Ordini",
            "🛒 Preparazione Ordini Fornitore",
            "📊 Database Articoli Dettagliato",
            "📄 Report Excel",
            "🔄 Aggiornamento Dati",
            "🔍 Analisi Dati (Debug)"
        ]
    )

    # Router pagine
    if page == "🏠 Dashboard":
        page_dashboard(df_giacenze_main, df_giacenze_detail, df_consumi)

    elif page == "🔍 Analisi Inventario":
        page_inventory_analysis(df_giacenze_main, df_giacenze_detail, df_consumi)

    elif page == "📈 Analisi Consumi":
        page_consumption_analysis(df_consumi)

    elif page == "📦 Suggerimenti Ordini":
        page_order_suggestions(df_giacenze_main, df_consumi)

    elif page == "🛒 Preparazione Ordini Fornitore":
        page_supplier_orders(df_giacenze_main, df_consumi)

    elif page == "📊 Database Articoli Dettagliato":
        page_article_database(df_giacenze_main, df_giacenze_detail, df_consumi)

    elif page == "📄 Report Excel":
        page_excel_reports(df_giacenze_main, df_giacenze_detail, df_consumi)

    elif page == "🔄 Aggiornamento Dati":
        page_data_update()

    elif page == "🔍 Analisi Dati (Debug)":
        page_data_analysis(df_consumi)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("HotelOPS Economato v2.0")
    st.sidebar.caption("© 2025 Panorama Group")

def page_order_suggestions(df_giacenze_main, df_consumi):
    """Pagina suggerimenti ordini."""
    st.header("🎯 Suggerimenti Ordini")

    # Parametri di calcolo
    st.sidebar.markdown("### ⚙️ Parametri Calcolo")
    lead_time = st.sidebar.slider("Lead Time (giorni)", 1, 30, 7)
    stock_sicurezza = st.sidebar.slider("Stock Sicurezza (giorni)", 1, 15, 3)
    mesi_copertura_target = st.sidebar.slider("Copertura Target (mesi)", 0.5, 3.0, 1.5, 0.5)

    if df_consumi.empty:
        st.warning("⚠️ Nessun dato di consumo disponibile per calcolare i suggerimenti")
        return

    # Calcola consumo medio per articolo
    consumo_medio = df_consumi.groupby('article_id')['quantita'].agg(['mean', 'std']).reset_index()
    consumo_medio.columns = ['article_id', 'consumo_medio', 'deviazione_std']

    # Unisci con giacenze
    df_analisi = df_giacenze_main.merge(consumo_medio, on='article_id', how='left')
    df_analisi['consumo_medio'] = df_analisi['consumo_medio'].fillna(0)
    df_analisi['deviazione_std'] = df_analisi['deviazione_std'].fillna(0)

    # Calcola suggerimenti
    df_analisi['qty_suggerita'] = df_analisi.apply(
        lambda row: calcola_suggerimento_ordine(
            row['consumo_medio'],
            row['qty_totale'],
            lead_time,
            stock_sicurezza
        ),
        axis=1
    )

    # Filtra solo articoli che necessitano ordine
    df_ordini = df_analisi[df_analisi['qty_suggerita'] > 0].copy()
    df_ordini['valore_ordine'] = df_ordini['qty_suggerita'] * df_ordini['avg_price']
    df_ordini = df_ordini.sort_values('valore_ordine', ascending=False)

    # Metriche
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        n_articoli = len(df_ordini)
        st.metric("Articoli da Ordinare", format_number(n_articoli))

    with col2:
        valore_totale = df_ordini['valore_ordine'].sum()
        st.metric("Valore Totale Ordini", format_currency(valore_totale))

    with col3:
        articoli_critici = len(df_ordini[df_ordini['qty_totale'] < df_ordini['consumo_medio'] * 0.5])
        st.metric("Articoli Critici", format_number(articoli_critici), delta="⚠️ Scorta < 15 giorni")

    with col4:
        risparmio_potenziale = valore_totale * 0.05  # Assumendo 5% di sconto su ordini
        st.metric("Risparmio Potenziale", format_currency(risparmio_potenziale), delta="5% sconto volume")

    # Tabs per diverse viste
    tab1, tab2, tab3 = st.tabs(["📋 Lista Ordini", "📊 Analisi per Categoria", "⚡ Articoli Critici"])

    with tab1:
        st.subheader("Lista Articoli da Ordinare")

        # Filtri
        col1, col2 = st.columns(2)
        with col1:
            filter_classe = st.selectbox("Filtra per Classe", ["Tutte"] + sorted(df_ordini['classe'].unique()))
        with col2:
            min_value = st.number_input("Valore minimo ordine (€)", min_value=0.0, value=0.0)

        # Applica filtri
        df_filtered = df_ordini.copy()
        if filter_classe != "Tutte":
            df_filtered = df_filtered[df_filtered['classe'] == filter_classe]
        if min_value > 0:
            df_filtered = df_filtered[df_filtered['valore_ordine'] >= min_value]

        # Mostra tabella
        display_cols = [
            'article_id', 'description', 'classe', 'categoria',
            'qty_totale', 'consumo_medio', 'qty_suggerita',
            'unit_of_measure', 'avg_price', 'valore_ordine'
        ]

        st.dataframe(
            df_filtered[display_cols].style.format({
                'qty_totale': '{:.0f}',
                'consumo_medio': '{:.1f}',
                'qty_suggerita': '{:.0f}',
                'avg_price': '€{:.2f}',
                'valore_ordine': '€{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )

        # Download
        csv = df_filtered[display_cols].to_csv(index=False)
        st.download_button(
            "📥 Scarica Lista Ordini",
            csv,
            f"ordini_suggeriti_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )

    with tab2:
        st.subheader("Analisi Ordini per Categoria")

        # Raggruppa per classe e categoria
        ordini_categoria = df_ordini.groupby(['classe', 'categoria']).agg({
            'article_id': 'count',
            'qty_suggerita': 'sum',
            'valore_ordine': 'sum'
        }).reset_index()

        ordini_categoria.columns = ['Classe', 'Categoria', 'Num. Articoli', 'Quantità Tot.', 'Valore Tot.']

        # Grafico sunburst
        fig = px.sunburst(
            ordini_categoria,
            path=['Classe', 'Categoria'],
            values='Valore Tot.',
            title='Distribuzione Valore Ordini per Classe e Categoria'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabella riepilogo
        st.dataframe(
            ordini_categoria.style.format({
                'Quantità Tot.': '{:,.0f}',
                'Valore Tot.': '€{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.subheader("⚠️ Articoli Critici")
        st.info("Articoli con giacenza inferiore a 15 giorni di consumo medio")

        # Calcola giorni di copertura
        df_critici = df_analisi[df_analisi['consumo_medio'] > 0].copy()
        df_critici['giorni_copertura'] = (df_critici['qty_totale'] / df_critici['consumo_medio']) * 30
        df_critici = df_critici[df_critici['giorni_copertura'] < 15].sort_values('giorni_copertura')

        if not df_critici.empty:
            # Grafico
            fig = px.bar(
                df_critici.head(20),
                x='giorni_copertura',
                y='description',
                orientation='h',
                title='Top 20 Articoli Critici per Giorni di Copertura',
                color='giorni_copertura',
                color_continuous_scale='Reds_r'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # Tabella dettaglio
            critical_cols = [
                'article_id', 'description', 'qty_totale',
                'consumo_medio', 'giorni_copertura', 'qty_suggerita'
            ]

            st.dataframe(
                df_critici[critical_cols].style.format({
                    'qty_totale': '{:.0f}',
                    'consumo_medio': '{:.1f}',
                    'giorni_copertura': '{:.1f}',
                    'qty_suggerita': '{:.0f}'
                }).background_gradient(subset=['giorni_copertura'], cmap='Reds_r'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ Nessun articolo in situazione critica!")

def page_data_update():
    """Pagina per aggiornamento dati."""
    st.header("📥 Aggiorna Dati")

    st.info("""
    **Istruzioni per l'aggiornamento:**
    1. Aggiorna i file delle giacenze nella cartella Google Drive
    2. Aggiungi i nuovi file dei consumi nelle rispettive cartelle (2024/2025)
    3. Esegui gli script di elaborazione nell'ordine indicato
    """)

    # Sezione giacenze
    st.subheader("1️⃣ Aggiornamento Giacenze")

    with st.expander("📋 Procedura Giacenze", expanded=True):
        st.markdown("""
        1. **File origine**: `ECO_SITUAZIONEARTICOLI_[data].xlsx`
        2. **Posizione**: `/giacienze/` su Google Drive
        3. **Script da eseguire**:
           ```bash
           python clean_giacenze.py
           python scripts/transform_giacenze_clean.py
           ```
        4. **File generati**:
           - `giacenze_principale_latest.csv`
           - `giacenze_dettaglio_reparti_latest.csv`
        """)

        if st.button("🔄 Verifica File Giacenze"):
            if GIACENZE_PRINCIPALE.exists():
                st.success(f"✅ File principale trovato: {GIACENZE_PRINCIPALE.name}")
                mod_time = datetime.fromtimestamp(GIACENZE_PRINCIPALE.stat().st_mtime)
                st.info(f"Ultima modifica: {mod_time.strftime('%d/%m/%Y %H:%M')}")
            else:
                st.error("❌ File principale non trovato")

    # Sezione consumi
    st.subheader("2️⃣ Aggiornamento Consumi")

    with st.expander("📋 Procedura Consumi", expanded=True):
        st.markdown("""
        1. **Struttura cartelle**:
           - `/consumi/Consumi_Economato_2024/[Reparto]/`
           - `/consumi/Consumi_Economato_2025/[Reparto]/`
        2. **Formato file**: `[MM]_[Reparto]_[Mese]_[Anno].xlsx`
        3. **Aggiunta nuovi mesi**:
           - Copia il file Excel nel reparto corretto
           - Mantieni la struttura del nome file
           - L'app caricherà automaticamente i nuovi dati
        """)

        if st.button("🔄 Scansiona Cartelle Consumi"):
            # Conta file per anno
            count_2024 = 0
            count_2025 = 0

            if (CONSUMI_PATH / "Consumi_Economato_2024").exists():
                for folder in (CONSUMI_PATH / "Consumi_Economato_2024").iterdir():
                    if folder.is_dir():
                        count_2024 += len(list(folder.glob("*.xlsx")))

            if (CONSUMI_PATH / "Consumi_Economato_2025").exists():
                for folder in (CONSUMI_PATH / "Consumi_Economato_2025").iterdir():
                    if folder.is_dir():
                        count_2025 += len(list(folder.glob("*.xlsx")))

            col1, col2 = st.columns(2)
            with col1:
                st.metric("File Consumi 2024", count_2024)
            with col2:
                st.metric("File Consumi 2025", count_2025)

    # Log recenti
    st.subheader("📜 Attività Recenti")

    # Simula un log delle attività
    log_data = {
        'Data': [
            datetime.now().strftime('%d/%m/%Y %H:%M'),
            (datetime.now().replace(day=1)).strftime('%d/%m/%Y %H:%M'),
            (datetime.now().replace(day=15, month=6)).strftime('%d/%m/%Y %H:%M')
        ],
        'Tipo': ['Info', 'Aggiornamento', 'Aggiornamento'],
        'Descrizione': [
            'Caricamento app completato',
            'Aggiornate giacenze luglio 2024',
            'Aggiunti consumi giugno 2025'
        ]
    }

    df_log = pd.DataFrame(log_data)
    st.dataframe(df_log, use_container_width=True, hide_index=True)

def page_supplier_orders(df_giacenze_main, df_consumi):
    """Pagina preparazione ordini per fornitore."""
    st.header("🛒 Preparazione Ordini per Fornitore")
    st.markdown(
        "Prepara ordini per fornitori con calcolo automatico delle quantità "
        "basato su consumo storico e lead time."
    )

    # Verifica se abbiamo i dati dei fornitori
    if 'fornitore' not in df_giacenze_main.columns:
        st.error("❌ Dati fornitori non disponibili. Verifica il caricamento.")
        return

    # Filtra fornitori validi
    valid_suppliers = [
        s for s in df_giacenze_main['fornitore'].unique()
        if s not in ['N/D', 'DA DEFINIRE'] and not str(s).replace(',', '').replace('.', '').replace('-', '').isdigit()
    ]
    valid_suppliers = sorted(valid_suppliers)

    if not valid_suppliers:
        st.warning("⚠️ Nessun fornitore valido trovato nei dati.")
        return

    # Sidebar per filtri e parametri
    with st.sidebar:
        st.markdown("### 🎯 Filtri Fornitore")

        selected_supplier = st.selectbox(
            "Seleziona Fornitore",
            ["Tutti"] + valid_suppliers,
            help="Seleziona un fornitore specifico o visualizza tutti"
        )

        st.markdown("### ⚙️ Parametri Ordine")

        coverage_days = st.slider(
            "Giorni di Copertura",
            min_value=1,
            max_value=60,
            value=14,
            help="Numero di giorni di scorta desiderati"
        )

        safety_factor = st.slider(
            "Fattore di Sicurezza",
            min_value=1.0,
            max_value=2.0,
            value=1.2,
            step=0.1,
            help="Moltiplicatore per scorta di sicurezza (1.2 = 20% extra)"
        )

        min_stock_threshold = st.number_input(
            "Soglia Giacenza Minima",
            min_value=0.0,
            value=5.0,
            help="Mostra articoli con giacenza sotto questa soglia"
        )

    # Prepara dati
    df_filtered = df_giacenze_main.copy()

    # Applica filtro fornitore
    if selected_supplier != "Tutti":
        df_filtered = df_filtered[df_filtered['fornitore'] == selected_supplier]
    else:
        df_filtered = df_filtered[df_filtered['fornitore'].isin(valid_suppliers)]

    # Aggiungi statistiche consumo
    if not df_consumi.empty:
        # Calcola consumo mensile per articolo
        consumo_mensile = df_consumi.groupby('article_id')['quantita'].agg(['mean', 'std', 'count']).reset_index()
        consumo_mensile.columns = ['article_id', 'consumo_medio_mensile', 'deviazione_std', 'n_occorrenze']

        # Merge con giacenze
        df_filtered = df_filtered.merge(consumo_mensile, on='article_id', how='left')
        df_filtered['consumo_medio_mensile'] = df_filtered['consumo_medio_mensile'].fillna(0)
        df_filtered['consumo_giornaliero'] = df_filtered['consumo_medio_mensile'] / 30
    else:
        df_filtered['consumo_medio_mensile'] = 0
        df_filtered['consumo_giornaliero'] = 0

    # Calcola quantità da ordinare
    df_filtered['giorni_copertura_attuali'] = df_filtered.apply(
        lambda row: row['giacenza'] / row['consumo_giornaliero'] if row['consumo_giornaliero'] > 0 else float('inf'),
        axis=1
    )

    df_filtered['target_stock'] = df_filtered['consumo_giornaliero'] * coverage_days * safety_factor
    df_filtered['qty_da_ordinare'] = (df_filtered['target_stock'] - df_filtered['giacenza']).clip(lower=0)

    # Arrotonda quantità in base all'unità di misura
    df_filtered['qty_da_ordinare'] = df_filtered.apply(
        lambda row: np.ceil(row['qty_da_ordinare']) if row['unit_of_measure'] in ['PZ', 'CF', 'CT']
        else round(row['qty_da_ordinare'], 1),
        axis=1
    )

    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        n_suppliers = len(df_filtered['fornitore'].unique())
        st.metric("Fornitori", n_suppliers)

    with col2:
        n_articles = len(df_filtered)
        st.metric("Articoli", n_articles)

    with col3:
        low_stock = len(df_filtered[df_filtered['giacenza'] <= min_stock_threshold])
        st.metric("Scorte Basse", low_stock)

    with col4:
        total_value = (df_filtered['giacenza'] * df_filtered['avg_price']).sum()
        st.metric("Valore Inventario", f"€ {total_value:,.2f}")

    # Tab per diverse viste
    tab1, tab2, tab3 = st.tabs(["📋 Vista Ordini", "📊 Analisi", "📥 Export"])

    with tab1:
        st.subheader("Ordini per Fornitore")

        # Checkbox per mostrare tutti gli articoli
        show_all = st.checkbox("Mostra tutti gli articoli (inclusi quelli senza necessità di riordino)", value=False)

        # Raggruppa per fornitore
        for fornitore, group in df_filtered.groupby('fornitore'):
            # Filtra articoli da ordinare
            if not show_all:
                items_to_order = group[group['qty_da_ordinare'] > 0]
            else:
                items_to_order = group

            if len(items_to_order) > 0:
                # Calcola totali
                total_items = len(items_to_order)
                total_value = (items_to_order['qty_da_ordinare'] * items_to_order['avg_price']).sum()

                with st.expander(
                    f"**{fornitore}** - {total_items} articoli - € {total_value:,.2f}",
                    expanded=(selected_supplier == fornitore)
                ):
                    # Prepara dati per visualizzazione
                    display_df = items_to_order[[
                        'article_id', 'description', 'unit_of_measure',
                        'giacenza', 'consumo_medio_mensile', 'giorni_copertura_attuali',
                        'qty_da_ordinare', 'avg_price'
                    ]].copy()

                    display_df['valore_ordine'] = display_df['qty_da_ordinare'] * display_df['avg_price']
                    display_df['giorni_copertura_attuali'] = display_df['giorni_copertura_attuali'].replace([np.inf], 999)

                    # Rinomina colonne
                    display_df.columns = [
                        'Codice', 'Descrizione', 'U.M.', 'Giacenza',
                        'Consumo Mensile', 'Giorni Copertura', 'Q.tà Ordine',
                        'Prezzo', 'Valore'
                    ]

                    # Mostra tabella
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Giacenza': st.column_config.NumberColumn(format='%.1f'),
                            'Consumo Mensile': st.column_config.NumberColumn(format='%.1f'),
                            'Giorni Copertura': st.column_config.NumberColumn(format='%.0f'),
                            'Q.tà Ordine': st.column_config.NumberColumn(format='%.1f'),
                            'Prezzo': st.column_config.NumberColumn(format='€ %.2f'),
                            'Valore': st.column_config.NumberColumn(format='€ %.2f')
                        }
                    )

                    # Riepilogo
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Articoli da ordinare", (display_df['Q.tà Ordine'] > 0).sum())
                    with col2:
                        st.metric("Valore totale ordine", f"€ {display_df['Valore'].sum():,.2f}")
                    with col3:
                        avg_coverage = display_df[display_df['Giorni Copertura'] < 999]['Giorni Copertura'].mean()
                        st.metric("Copertura media", f"{avg_coverage:.1f} giorni" if not np.isnan(avg_coverage) else "N/A")

                    # Download CSV
                    csv = display_df.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Scarica CSV {fornitore}",
                        data=csv,
                        file_name=f"ordine_{fornitore}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime='text/csv',
                        key=f"download_{fornitore}"
                    )

    with tab2:
        st.subheader("Analisi Consumi e Copertura")

        if not df_filtered.empty and 'consumo_medio_mensile' in df_filtered.columns:
            # Top articoli per consumo
            col1, col2 = st.columns(2)

            with col1:
                top_consumed = df_filtered.nlargest(15, 'consumo_medio_mensile')[['description', 'consumo_medio_mensile']]
                fig = px.bar(
                    top_consumed,
                    x='consumo_medio_mensile',
                    y='description',
                    orientation='h',
                    title='Top 15 Articoli per Consumo Mensile',
                    labels={'consumo_medio_mensile': 'Consumo Medio Mensile', 'description': ''}
                )
                fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Analisi copertura
                coverage_data = df_filtered[df_filtered['consumo_giornaliero'] > 0].copy()
                coverage_data = coverage_data[coverage_data['giorni_copertura_attuali'] < 999]

                fig = px.scatter(
                    coverage_data,
                    x='consumo_giornaliero',
                    y='giorni_copertura_attuali',
                    size='giacenza',
                    color='fornitore',
                    title='Analisi Copertura vs Consumo',
                    labels={
                        'consumo_giornaliero': 'Consumo Giornaliero',
                        'giorni_copertura_attuali': 'Giorni di Copertura Attuali'
                    },
                    hover_data=['article_id', 'description']
                )
                fig.add_hline(
                    y=coverage_days,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Target: {coverage_days} giorni"
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

            # Analisi per fornitore
            st.subheader("Riepilogo per Fornitore")

            supplier_summary = df_filtered.groupby('fornitore').agg({
                'article_id': 'count',
                'giacenza': lambda x: (x <= min_stock_threshold).sum(),
                'qty_da_ordinare': lambda x: (x > 0).sum(),
                'avg_price': lambda x: (df_filtered.loc[x.index, 'qty_da_ordinare'] * x).sum()
            }).reset_index()

            supplier_summary.columns = ['Fornitore', 'Articoli Totali', 'Scorte Basse', 'Da Ordinare', 'Valore Ordine']
            supplier_summary = supplier_summary.sort_values('Valore Ordine', ascending=False)

            st.dataframe(
                supplier_summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Articoli Totali': st.column_config.NumberColumn(format='%d'),
                    'Scorte Basse': st.column_config.NumberColumn(format='%d'),
                    'Da Ordinare': st.column_config.NumberColumn(format='%d'),
                    'Valore Ordine': st.column_config.NumberColumn(format='€ %.2f')
                }
            )

    with tab3:
        st.subheader("Export Dati")

        export_supplier = st.selectbox(
            "Fornitore da esportare",
            ["Tutti"] + valid_suppliers,
            key='export_supplier_select'
        )

        export_only_orders = st.checkbox(
            "Esporta solo articoli da ordinare",
            value=True,
            key='export_only_orders'
        )

        # Prepara dati per export
        if export_supplier == "Tutti":
            export_df = df_filtered
        else:
            export_df = df_filtered[df_filtered['fornitore'] == export_supplier]

        if export_only_orders:
            export_df = export_df[export_df['qty_da_ordinare'] > 0]

        # Seleziona colonne per export
        export_columns = [
            'fornitore', 'article_id', 'description', 'unit_of_measure',
            'giacenza', 'consumo_medio_mensile', 'giorni_copertura_attuali',
            'qty_da_ordinare', 'avg_price'
        ]

        export_df = export_df[export_columns].copy()
        export_df['valore_ordine'] = export_df['qty_da_ordinare'] * export_df['avg_price']

        # Mostra anteprima
        st.write(f"Anteprima export ({len(export_df)} articoli):")
        st.dataframe(export_df.head(20), use_container_width=True, hide_index=True)

        # Download
        csv = export_df.to_csv(index=False)
        filename = f"ordini_{export_supplier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        st.download_button(
            label="📥 Scarica CSV Completo",
            data=csv,
            file_name=filename,
            mime='text/csv'
        )


def page_article_database(df_giacenze_main, df_giacenze_detail, df_consumi):
    """Database completo articoli con giacenze dettagliate e storico consumi mensili."""
    st.title("📊 Database Articoli Dettagliato")
    st.markdown("Vista completa di tutti gli articoli con giacenze per reparto e storico consumi mensili")

    # Filtri
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Filtro fornitore
        fornitori = ['Tutti'] + sorted(df_giacenze_main['fornitore'].unique())
        selected_fornitore = st.selectbox("Fornitore", fornitori)

    with col2:
        # Filtro categoria
        categorie = ['Tutte'] + sorted(df_giacenze_main['categoria'].unique())
        selected_categoria = st.selectbox("Categoria", categorie)

    with col3:
        # Filtro classe
        classi = ['Tutte'] + sorted(df_giacenze_main['classe'].unique())
        selected_classe = st.selectbox("Classe", classi)

    with col4:
        # Filtro articoli con/senza consumi
        filter_type = st.selectbox(
            "Mostra",
            ["Tutti", "Solo con consumi", "Solo senza consumi", "Solo con giacenza"]
        )

    # Applica filtri
    df_filtered = df_giacenze_main.copy()

    if selected_fornitore != "Tutti":
        df_filtered = df_filtered[df_filtered['fornitore'] == selected_fornitore]

    if selected_categoria != "Tutte":
        df_filtered = df_filtered[df_filtered['categoria'] == selected_categoria]

    if selected_classe != "Tutte":
        df_filtered = df_filtered[df_filtered['classe'] == selected_classe]

    # Prepara dati consumi mensili per tutti gli articoli
    if not df_consumi.empty:
        # Crea pivot table dei consumi mensili
        consumi_pivot = df_consumi.pivot_table(
            index='article_id',
            columns=['anno', 'mese_nome'],
            values='quantita',
            aggfunc='sum',
            fill_value=0
        )

        # Appiattisci i nomi delle colonne
        consumi_pivot.columns = [f"{col[1]} {col[0]}" for col in consumi_pivot.columns]
        consumi_pivot = consumi_pivot.reset_index()

        # Merge con giacenze
        df_filtered = df_filtered.merge(consumi_pivot, on='article_id', how='left')

        # Calcola totale consumi
        consumption_cols = [col for col in consumi_pivot.columns if col != 'article_id']
        df_filtered['totale_consumi'] = df_filtered[consumption_cols].fillna(0).sum(axis=1)
    else:
        consumption_cols = []
        df_filtered['totale_consumi'] = 0

    # Applica filtro tipo
    if filter_type == "Solo con consumi":
        df_filtered = df_filtered[df_filtered['totale_consumi'] > 0]
    elif filter_type == "Solo senza consumi":
        df_filtered = df_filtered[df_filtered['totale_consumi'] == 0]
    elif filter_type == "Solo con giacenza":
        df_filtered = df_filtered[df_filtered['giacenza'] > 0]

    # Prepara dettaglio giacenze per reparto
    if not df_giacenze_detail.empty:
        # Pivot giacenze per reparto
        giacenze_reparti_pivot = df_giacenze_detail.pivot_table(
            index='article_id',
            columns='reparto',
            values='quantita',
            aggfunc='sum',
            fill_value=0
        )
        giacenze_reparti_pivot.columns = [f"Giacenza_{col}" for col in giacenze_reparti_pivot.columns]
        giacenze_reparti_pivot = giacenze_reparti_pivot.reset_index()

        # Merge con dataframe principale
        df_filtered = df_filtered.merge(giacenze_reparti_pivot, on='article_id', how='left')
        reparto_cols = [col for col in giacenze_reparti_pivot.columns if col != 'article_id']
    else:
        reparto_cols = []

    # Statistiche
    st.markdown("### 📈 Statistiche")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Articoli totali", len(df_filtered))
    with col2:
        st.metric("Con giacenza", len(df_filtered[df_filtered['giacenza'] > 0]))
    with col3:
        st.metric("Con consumi", len(df_filtered[df_filtered['totale_consumi'] > 0]))
    with col4:
        st.metric("Valore totale", f"€{df_filtered['valore_totale'].sum():,.2f}")

    # Opzioni visualizzazione
    st.markdown("### ⚙️ Opzioni Visualizzazione")
    col1, col2 = st.columns(2)

    with col1:
        show_zero_values = st.checkbox("Mostra valori zero", value=False)
        show_reparto_detail = st.checkbox("Mostra dettaglio reparti", value=True)

    with col2:
        show_consumption_history = st.checkbox("Mostra storico consumi", value=True)
        show_only_recent = st.checkbox("Solo ultimi 6 mesi", value=False)

    # Prepara colonne da visualizzare
    base_cols = [
        'article_id', 'description', 'fornitore', 'categoria', 'classe',
        'unit_of_measure', 'avg_price', 'giacenza', 'valore_totale'
    ]

    display_cols = base_cols.copy()

    if show_reparto_detail and reparto_cols:
        # Aggiungi solo colonne reparti con valori se richiesto
        if not show_zero_values:
            reparto_cols_filtered = []
            for col in reparto_cols:
                if df_filtered[col].sum() > 0:
                    reparto_cols_filtered.append(col)
            display_cols.extend(reparto_cols_filtered)
        else:
            display_cols.extend(reparto_cols)

    if show_consumption_history and consumption_cols:
        # Se solo ultimi 6 mesi, prendi solo le ultime 6 colonne
        if show_only_recent:
            recent_cols = consumption_cols[-6:] if len(consumption_cols) > 6 else consumption_cols
            display_cols.extend(recent_cols)
        else:
            display_cols.extend(consumption_cols)

    display_cols.append('totale_consumi')

    # Visualizza tabella
    st.markdown("### 📋 Database Articoli")

    # Prepara dataframe per visualizzazione
    df_display = df_filtered[display_cols].copy()

    # Formattazione
    format_dict = {
        'avg_price': '€{:.2f}',
        'valore_totale': '€{:,.2f}',
        'giacenza': '{:.1f}',
        'totale_consumi': '{:.0f}'
    }

    # Aggiungi formattazione per colonne giacenze reparti
    for col in reparto_cols:
        if col in df_display.columns:
            format_dict[col] = '{:.0f}'

    # Aggiungi formattazione per colonne consumi
    for col in consumption_cols:
        if col in df_display.columns:
            format_dict[col] = '{:.0f}'

    # Mostra dataframe
    st.dataframe(
        df_display.style.format(format_dict).background_gradient(
            subset=[col for col in ['giacenza', 'totale_consumi'] + reparto_cols + consumption_cols
                    if col in df_display.columns],
            cmap='YlOrRd'
        ),
        use_container_width=True,
        height=600
    )

    # Export completo
    st.markdown("### 💾 Export Dati")
    col1, col2 = st.columns(2)

    with col1:
        # Export CSV
        csv = df_display.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV completo",
            data=csv,
            file_name=f"database_articoli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )

    with col2:
        # Export Excel con formattazione
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_display.to_excel(writer, sheet_name='Database Articoli', index=False)

            # Formattazione Excel
            worksheet = writer.sheets['Database Articoli']
            for idx, col in enumerate(df_display.columns):
                worksheet.column_dimensions[chr(65 + idx)].width = 15

        excel_data = output.getvalue()
        st.download_button(
            label="📥 Scarica Excel formattato",
            data=excel_data,
            file_name=f"database_articoli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # Analisi rapida articolo selezionato
    st.markdown("### 🔍 Analisi Dettaglio Articolo")

    articoli_list = df_filtered['article_id'].tolist()
    selected_article = st.selectbox(
        "Seleziona un articolo per vedere il dettaglio completo",
        [""] + articoli_list,
        format_func=lambda x: f"{x} - {df_filtered[df_filtered['article_id']==x]['description'].iloc[0]}" if x else "Seleziona..."
    )

    if selected_article:
        show_article_detail(selected_article, df_giacenze_main, df_giacenze_detail, df_consumi)

# -----------------------------------------------------------------------------
# MAIN APPLICATION
# -----------------------------------------------------------------------------
def main():
    """Funzione principale dell'applicazione."""
    
    # Header
    st.title("🏨 HotelOPS Economato - Gestione Completa")
    st.markdown("---")
    
    # Sidebar - Selezione fonte dati
    with st.sidebar:
        st.header("⚙️ Configurazione")
        
        # Selezione fonte dati
        data_source = st.radio(
            "📊 Fonte Dati Giacenze:",
            ["CSV (Elaborato)", "XML (Diretto PMS)"],
            help="CSV: dati elaborati e puliti | XML: dati diretti dal PMS"
        )
        
        st.markdown("---")
        
        # Info fonte dati
        if data_source == "XML (Diretto PMS)":
            st.info("🔗 **Dati diretti dal PMS**\n\nI prezzi potrebbero contenere errori di calcolo del sistema.")
        else:
            st.info("📊 **Dati elaborati**\n\nDati CSV processati e verificati.")
    
    # Carica dati in base alla selezione
    if data_source == "XML (Diretto PMS)":
        df_giacenze_main = load_giacenze_from_xml()
        if df_giacenze_main.empty:
            st.error("❌ Impossibile caricare dati XML. Passaggio automatico a CSV.")
            df_giacenze_main = load_giacenze_principale()
    else:
        df_giacenze_main = load_giacenze_principale()
    
    # Carica altri dati
    df_giacenze_detail = load_giacenze_dettaglio()
    df_consumi = load_consumi_data()
    
    # Check dati
    if df_giacenze_main.empty:
        st.error("❌ Nessun dato di giacenze disponibile!")
        return
    
    # Sidebar - Navigazione
    with st.sidebar:
        st.markdown("---")
        st.header("🧭 Navigazione")
        
        page = st.selectbox(
            "Seleziona pagina:",
            [
                "📊 Dashboard",
                "🔍 Analisi Inventario",
                "📈 Analisi Consumi", 
                "📄 Report Excel"
            ]
        )
    
    # Router pagine
    if page == "📊 Dashboard":
        page_dashboard(df_giacenze_main, df_giacenze_detail, df_consumi)
    elif page == "🔍 Analisi Inventario":
        page_inventory_analysis(df_giacenze_main, df_giacenze_detail, df_consumi)
    elif page == "📈 Analisi Consumi":
        page_consumption_analysis(df_consumi)
    elif page == "📄 Report Excel":
        page_excel_reports(df_giacenze_main, df_giacenze_detail, df_consumi)


if __name__ == "__main__":
    main()
