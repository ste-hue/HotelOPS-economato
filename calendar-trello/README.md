# Economato Trello Manager

Sistema semplificato per gestire il Trello dell'economato sincronizzando automaticamente gli eventi dai calendari Google Calendar.

## 🎯 Funzionalità

- **Preparazione Giornaliera**: Aggiunge automaticamente le attività del giorno desiderato su Trello
- **Gestione Flessibile**: Prepara il Trello per oggi, domani o qualsiasi giorno della settimana
- **Pulizia Rapida**: Cancella tutte le card dalla lista "DA ESEGUIRE" con un comando
- **Etichettatura Automatica**: Applica le etichette corrette in base al tipo di attività
- **Template o Live**: Usa il template settimanale o leggi direttamente dai calendari Google

## 📅 Calendari Gestiti

- **CARICO A REPARTO** (etichetta verde)
- **ORDINE FORNITORE** (etichetta gialla)
- **RICHIESTA REPARTO** (etichetta arancione)
- **SCARICO FORNITORE** (etichetta rossa)

## 🚀 Setup Iniziale

### 1. Ambiente virtuale e dipendenze

```bash
# Attiva l'ambiente virtuale
workon hotelops_env

# Installa le dipendenze
pip install -r requirements.txt
```

### 2. Configurazione

Le credenziali sono già configurate nel file `.env`:
- API Trello configurate
- Service Account Google configurato
- Board Trello: https://trello.com/b/0c2HB9nw/economato

## 📱 Utilizzo

### Modalità Interattiva (Consigliata)

```bash
# Assicurati di essere nell'ambiente corretto
workon hotelops_env

# Esegui lo script principale
python economato_trello.py
```

Menu disponibile:
1. Prepara Trello per oggi
2. Prepara Trello per domani
3. Prepara Trello per un giorno specifico della settimana
4. Pulisci lista DA ESEGUIRE
5. Mostra riepilogo settimana
6. Usa calendari live invece del template

### Modalità Linea di Comando

```bash
# Prepara il Trello per oggi
python economato_trello.py today

# Prepara il Trello per domani
python economato_trello.py tomorrow

# Pulisci la lista DA FARE
python economato_trello.py clear

# Mostra riepilogo settimana
python economato_trello.py summary

# Verifica lo stato attuale della board
python check_board_status.py
```

## 🔄 Workflow Tipico

### Preparazione Giornaliera
1. Ogni sera, esegui lo script e scegli "Prepara Trello per domani"
2. Le attività vengono aggiunte automaticamente alla lista "DA FARE"
3. Ogni attività ha l'etichetta corretta e l'orario nella descrizione

### Gestione Attività Non Completate
1. Le attività non completate rimangono nella lista
2. Puoi aggiungere nuove attività per lo stesso giorno senza duplicati
3. Usa "Pulisci lista DA FARE" per ripartire da zero

### Preparazione Settimanale
1. Seleziona "Prepara Trello per un giorno specifico"
2. Scegli il giorno della settimana
3. Il sistema prepara automaticamente tutte le attività per quel giorno

## 📊 Template Settimanale

Il sistema usa un template della settimana del 13-19 gennaio 2025 che contiene:
- 24 eventi per CARICO A REPARTO
- 37 eventi per ORDINE FORNITORE
- 19 eventi per RICHIESTA REPARTO
- 41 eventi per SCARICO FORNITORE

Totale: 121 eventi settimanali ricorrenti

## 🛠️ File di Sistema

- `economato_trello.py` - Script principale
- `check_board_status.py` - Script per verificare lo stato della board
- `test_connection.py` - Script per testare le connessioni
- `week_template_2025_01_15_service_account.json` - Template settimanale
- `HotelopsSuite.json` - Credenziali Service Account Google
- `.env` - Variabili d'ambiente (API keys)

## ⚡ Automazione

Per automazione con cron:

```bash
# Ogni giorno alle 18:00, prepara il Trello per domani
0 18 * * * cd /path/to/calendar-trello && source /path/to/virtualenvwrapper.sh && workon hotelops_env && python economato_trello.py tomorrow

# Ogni lunedì alle 6:00, pulisci la lista DA FARE
0 6 * * 1 cd /path/to/calendar-trello && source /path/to/virtualenvwrapper.sh && workon hotelops_env && python economato_trello.py clear

# Ogni ora, verifica lo stato della board e invia report (opzionale)
0 * * * * cd /path/to/calendar-trello && source /path/to/virtualenvwrapper.sh && workon hotelops_env && python check_board_status.py > /tmp/board_status.log
```

## 🔍 Troubleshooting

### Le card non vengono create
- Verifica che le credenziali Trello nel `.env` siano valide
- Controlla che la board sia accessibile: https://trello.com/b/0c2HB9nw/economato

### Eventi mancanti
- Il template potrebbe non avere eventi per quel giorno
- Prova a usare la modalità "calendari live" dal menu

### Errori di autenticazione Google
- Verifica che il file `HotelopsSuite.json` sia presente
- Controlla che il service account abbia accesso ai calendari

## 📞 Supporto

Per problemi o domande, contatta il team IT.
