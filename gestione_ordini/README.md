

Gestione Ordini — Manuale del Macchinista

Cosa fa
	•	Legge giacenze e consumi aggiornati.
	•	Calcola cosa manca per non restare senza scorte.
	•	Raggruppa articoli per fornitore.
	•	Genera un documento d’ordine pronto.

Come lo fa
	1.	Legge il database (giacenze, consumi, fornitori).
	2.	Calcola il fabbisogno con margine di sicurezza.
	3.	Raggruppa per fornitore.
	4.	Scrive il file Excel o Google Sheet.

Comandi
Generare ordini:

python gestione_ordini_cli.py --generate

Simulazione (nessun salvataggio):

python gestione_ordini_cli.py --simulate

Filtrare per reparto:

python gestione_ordini_cli.py --generate --reparto BAR

Regole
	•	Aggiorna sempre giacenze e consumi prima di generare.
	•	Usa la simulazione per verificare i calcoli.
	•	Non mischiare ordini manuali e automatici senza aggiornare lo storico.

Risultato
	•	Documento d’ordine pulito e pronto.
	•	Nessun articolo dimenticato.
	•	Processo veloce e ripetibile.

⸻
