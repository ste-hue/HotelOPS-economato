#!/usr/bin/env python3
"""
Script per verificare lo stato attuale della board Trello dell'economato.
Mostra un riepilogo delle card presenti in ogni lista.
"""

import os
import sys
from datetime import datetime
from collections import defaultdict
import requests
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configurazione Trello
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_BOARD_ID = os.getenv('TRELLO_BOARD_SHORTLINK')

def get_board_status():
    """Recupera lo stato attuale della board Trello."""
    try:
        # Parametri di autenticazione
        params = {
            'key': TRELLO_API_KEY,
            'token': TRELLO_TOKEN
        }

        # Recupera informazioni board
        board_url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}"
        board_response = requests.get(board_url, params=params)
        board_response.raise_for_status()
        board_info = board_response.json()

        print(f"\n📋 BOARD: {board_info['name']}")
        print(f"🔗 URL: {board_info['url']}")
        print("=" * 70)

        # Recupera liste
        lists_url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/lists"
        lists_response = requests.get(lists_url, params=params)
        lists_response.raise_for_status()
        lists = lists_response.json()

        # Recupera tutte le card
        cards_url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/cards"
        cards_params = params.copy()
        cards_params['fields'] = 'name,desc,due,labels,idList,dateLastActivity'
        cards_response = requests.get(cards_url, params=cards_params)
        cards_response.raise_for_status()
        cards = cards_response.json()

        # Organizza card per lista
        cards_by_list = defaultdict(list)
        for card in cards:
            cards_by_list[card['idList']].append(card)

        # Statistiche per etichetta
        label_stats = defaultdict(int)
        total_cards = 0

        # Mostra stato per ogni lista
        for lst in lists:
            list_cards = cards_by_list[lst['id']]
            if list_cards or lst['name'] in ['DA FARE', 'IN LAVORAZIONE', 'ESEGUITO']:
                print(f"\n📂 {lst['name']} ({len(list_cards)} card)")
                print("-" * 60)

                # Ordina card per data di scadenza
                list_cards.sort(key=lambda x: x.get('due') or '', reverse=False)

                for i, card in enumerate(list_cards[:20], 1):  # Mostra max 20 card per lista
                    # Prepara info card
                    card_name = card['name'][:50] + "..." if len(card['name']) > 50 else card['name']

                    # Etichette
                    labels = []
                    for label in card.get('labels', []):
                        if label['name']:
                            labels.append(f"[{label['name']}]")
                            label_stats[label['name']] += 1

                    labels_str = ' '.join(labels) if labels else ''

                    # Data scadenza
                    due_str = ''
                    if card.get('due'):
                        due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                        due_str = f"📅 {due_date.strftime('%d/%m')}"

                    print(f"  {i:2}. {card_name} {labels_str} {due_str}")

                if len(list_cards) > 20:
                    print(f"     ... e altre {len(list_cards) - 20} card")

                total_cards += len(list_cards)

        # Mostra statistiche
        print("\n\n📊 STATISTICHE")
        print("=" * 70)
        print(f"Totale card nella board: {total_cards}")

        if label_stats:
            print("\nDistribuzione per etichetta:")
            for label, count in sorted(label_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_cards) * 100 if total_cards > 0 else 0
                bar_length = int(percentage / 2)
                bar = "█" * bar_length
                print(f"  {label:20} {count:3} ({percentage:5.1f}%) {bar}")

        # Card per lista principale
        print("\nCard per lista principale:")
        for lst in lists:
            if lst['name'] in ['DA FARE', 'IN LAVORAZIONE', 'ESEGUITO', 'IN GESTIONE ESTERNA', 'IN CONSEGNA']:
                count = len(cards_by_list[lst['id']])
                if count > 0 or lst['name'] in ['DA FARE', 'IN LAVORAZIONE', 'ESEGUITO']:
                    percentage = (count / total_cards) * 100 if total_cards > 0 else 0
                    bar_length = int(percentage / 2)
                    bar = "█" * bar_length
                    print(f"  {lst['name']:20} {count:3} ({percentage:5.1f}%) {bar}")

        # Mostra orario ultimo aggiornamento
        print(f"\n🕐 Ultimo controllo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Errore HTTP: {e}")
        print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

    return True

def main():
    """Funzione principale."""
    print("\n🏪 ECONOMATO TRELLO - STATO BOARD")
    print("=" * 70)

    if not all([TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID]):
        print("❌ Credenziali Trello mancanti nel file .env!")
        return 1

    if get_board_status():
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())
