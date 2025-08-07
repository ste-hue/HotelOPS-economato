#!/usr/bin/env python3
"""
Analisi del bug di calcolo PrezzoMedio nel PMS
Spiega esattamente perché il caffè costa €758.45 invece di €17.00
"""

import xml.etree.ElementTree as ET
from pathlib import Path

def analyze_pms_pricing_bug():
    """Analizza il bug di calcolo del PrezzoMedio nel PMS."""
    
    # File XML
    xml_file = Path(__file__).parent.parent / "temp_Eco Situation July 15.xml"
    
    if not xml_file.exists():
        print(f"❌ File XML non trovato: {xml_file}")
        return
    
    print("🔍 ANALISI BUG CALCOLO PMS - CAFFE BEV.CAF.00014")
    print("=" * 60)
    
    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    namespace = '{Eco_SituazioneAvanzataArticoli}'
    
    # Trova il caffè problematico
    caffe_trovato = False
    
    for detail in root.findall(f'.//{namespace}Detail'):
        attrs = detail.attrib
        
        if attrs.get('CodiceArticolo') == 'BEV.CAF.00014':
            caffe_trovato = True
            
            # Estrai tutti i valori
            prezzo_unitario = float(attrs.get('EuroUnitazio', 0))
            prezzo_medio = float(attrs.get('PrezzoMedio', 0))
            giacenza_magazzino = float(attrs.get('Esistenza_1', 0))  # 70 kg
            giacenza_reparti = float(attrs.get('textbox19', 0))     # 24 kg
            giacenza_totale = float(attrs.get('textbox23', 0))      # 94 kg
            valore_totale = float(attrs.get('textbox25', 0))        # €71,294.629
            
            print(f"📦 Articolo: {attrs.get('Descrizione', 'N/D')}")
            print(f"🏷️  Codice: {attrs.get('CodiceArticolo', 'N/D')}")
            print(f"🏭 Fornitore: {attrs.get('RagioneSociale', 'N/D')}")
            print(f"📏 Unità: {attrs.get('UM', 'N/D')}")
            print()
            
            print("📊 DATI ESTRATTI DAL PMS:")
            print(f"   • EuroUnitazio (prezzo corretto): €{prezzo_unitario:.4f}")
            print(f"   • PrezzoMedio (calcolato dal PMS): €{prezzo_medio:.4f}")
            print(f"   • Esistenza_1 (magazzino): {giacenza_magazzino:.0f} kg")
            print(f"   • textbox19 (reparti): {giacenza_reparti:.0f} kg")
            print(f"   • textbox23 (totale): {giacenza_totale:.0f} kg")
            print(f"   • textbox25 (valore totale): €{valore_totale:.3f}")
            print()
            
            print("🧮 CALCOLI DI VERIFICA:")
            print()
            
            # 1. Verifica calcolo corretto
            valore_corretto = giacenza_totale * prezzo_unitario
            print(f"1️⃣  CALCOLO CORRETTO:")
            print(f"   Valore = Giacenza × Prezzo Unitario")
            print(f"   Valore = {giacenza_totale:.0f} kg × €{prezzo_unitario:.2f}/kg")
            print(f"   Valore = €{valore_corretto:.2f}")
            print()
            
            # 2. Calcolo del PMS (errato)
            print(f"2️⃣  CALCOLO DEL PMS (ERRATO):")
            print(f"   Il PMS calcola: PrezzoMedio = Valore Totale ÷ Giacenza")
            print(f"   PrezzoMedio = €{valore_totale:.3f} ÷ {giacenza_totale:.0f} kg")
            print(f"   PrezzoMedio = €{valore_totale/giacenza_totale:.4f}")
            print()
            
            # 3. Analisi dell'errore
            differenza_valore = valore_totale - valore_corretto
            ratio_errore = prezzo_medio / prezzo_unitario
            
            print(f"🚨 ANALISI ERRORE:")
            print(f"   • Valore PMS: €{valore_totale:.2f}")
            print(f"   • Valore corretto: €{valore_corretto:.2f}")
            print(f"   • Sovrastima: €{differenza_valore:.2f}")
            print(f"   • Fattore moltiplicativo: {ratio_errore:.1f}x")
            print()
            
            # 4. Ipotesi sulla causa
            print(f"💡 IPOTESI SULLA CAUSA DEL BUG:")
            print()
            
            # Possibile spiegazione: il PMS accumula valori storici
            print("4️⃣  POSSIBILI CAUSE:")
            print("   A) Il campo 'textbox25' (valore totale) accumula:")
            print("      - Valori storici di carico/scarico")
            print("      - Rettifiche di inventario non ripulite")
            print("      - Valorizzazioni a prezzi diversi nel tempo")
            print()
            print("   B) Il PMS NON ricalcola il valore quando:")
            print("      - Cambia il prezzo unitario")
            print("      - Vengono fatte movimentazioni")
            print("      - Si fanno inventari fisici")
            print()
            
            # 5. Calcolo teorico per arrivare a €758.45
            valore_teorico_per_758 = 758.4535 * giacenza_totale
            print(f"   C) Per ottenere €758.45/kg con {giacenza_totale:.0f} kg:")
            print(f"      Il valore totale dovrebbe essere €{valore_teorico_per_758:.2f}")
            print(f"      Il PMS ha €{valore_totale:.2f}")
            print(f"      Differenza: €{abs(valore_totale - valore_teorico_per_758):.2f}")
            print()
            
            # 6. Impatto finanziario
            print(f"💰 IMPATTO FINANZIARIO:")
            print(f"   • Sovravalutazione inventario: €{differenza_valore:.2f}")
            print(f"   • Percentuale errore: {(differenza_valore/valore_corretto)*100:.1f}%")
            print()
            
            # 7. Raccomandazioni
            print(f"🔧 RACCOMANDAZIONI PER IL TEAM IT:")
            print("   1. Verificare il calcolo del campo 'textbox25' (valore totale)")
            print("   2. Controllare se ci sono accumuli storici non ripuliti")
            print("   3. Implementare ricalcolo automatico: Valore = Giacenza × EuroUnitazio")
            print("   4. Aggiungere controlli di coerenza tra PrezzoMedio e EuroUnitazio")
            print("   5. Verificare altri articoli con ratio >2x tra i due prezzi")
            print()
            
            break
    
    if not caffe_trovato:
        print("❌ Articolo BEV.CAF.00014 non trovato nel file XML")
        return
    
    print("📋 RIEPILOGO:")
    print("Il PMS ha un bug nel calcolo del PrezzoMedio perché:")
    print("• Il campo 'textbox25' (valore totale) contiene dati sporchi/storici")
    print("• Il PrezzoMedio viene calcolato come: Valore Totale ÷ Giacenza")
    print("• Invece dovrebbe essere sempre uguale a 'EuroUnitazio'")
    print("• Il campo 'EuroUnitazio' contiene il prezzo corretto (€17.00)")
    print()
    print("✅ SOLUZIONE IMPLEMENTATA nell'app:")
    print("Usare sempre 'EuroUnitazio' invece di 'PrezzoMedio' quando la differenza è >5x")

if __name__ == "__main__":
    analyze_pms_pricing_bug()
