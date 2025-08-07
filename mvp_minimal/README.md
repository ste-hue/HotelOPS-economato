# Economato MVP - Versione Minimale

## Cosa fa
- Carica file XML di giacenze e consumi
- Mostra una tabella filtrabile
- Esporta un report Excel consolidato

## Come avviarlo
```bash
streamlit run app.py
```

## Struttura del progetto
```
mvp_minimal/
├── app.py           # Tutta l'applicazione (106 righe)
├── requirements.txt # 3 dipendenze
└── README.md        # Questo file
```

## Funzionalità
1. **Upload**: Carica XML giacenze + XML consumi (multipli)
2. **Visualizza**: Tabella con filtro per testo
3. **Esporta**: Excel con fogli giacenze, consumi per mese e riepilogo

## Note
- Niente validazioni complesse
- Niente configurazioni
- Niente moduli separati
- Solo quello che serve per funzionare