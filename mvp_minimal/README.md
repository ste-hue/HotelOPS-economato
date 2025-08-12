# Economato - Gestione Giacenze e Consumi

Un'applicazione semplice per gestire le giacenze di magazzino e analizzare i consumi.

## Installazione

```bash
pip install -r requirements.txt
```

## Avvio

```bash
streamlit run economato.py
```

## Funzionalità

- Caricamento automatico dei file XML predefiniti
- Visualizzazione giacenze con ricerca
- Analisi consumi mensili
- Generazione report Excel con:
  - Analisi completa articoli
  - Riordini urgenti
  - Statistiche

## File Predefiniti

L'app cerca automaticamente i file in:
- Giacenze: `.../economato/giacienze/Eco_SituazioneAvanzataArticoli_giacienze11082025.xml`
- Consumi: `.../economato/consumi/xml/ECO_SituazioneConsumi_DettagliPerArticolo_dal1aprile.xml`

È possibile caricare file alternativi deselezionando le checkbox "Usa file predefinito".

## Report Excel

Il report generato include:
- **Analisi Completa**: Tutti gli articoli con giacenze, consumi mensili e calcoli
- **Riordino Urgente**: Articoli con copertura inferiore a 15 giorni
- **Statistiche**: Riepilogo generale del magazzino