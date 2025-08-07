#!/usr/bin/env python3
"""
Script di debug per visualizzare i dettagli completi di una card Trello.
Mostra tutti i campi inclusi orari, date, descrizioni, etc.
"""

import os
import sys
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configurazione Trello
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_BOARD_ID = os.getenv('TRELLO_BOARD_SHORTLINK')

def get_card_details(card_name_pattern=None, limit=3):
    """
    Recupera e mostra i dettagli completi delle card.

    Args:
        card_name_pattern: Pattern da cercare nel nome della card (case insensitive)
        limit: Numero massimo di card da mostrare
    """
    try:
        # Parametri di autenticazione
        params = {
            'key': TRELLO_API_KEY,
            'token': TRELLO_TOKEN,
            'fields': 'all'  # Recupera tutti i campi
        }

        # Recupera tutte le card della board
        url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/cards"
        response = requests.get(url, params=params)
        response.raise_for_status()

        all_cards = response.json()

        # Filtra le card se specificato un pattern
        if card_name_pattern:
            filtered_cards = [
                card for card in all_cards
                if card_name_pattern.lower() in card['name'].lower()
            ]
        else:
            # Prendi le prime card dalla lista "DA FARE"
            # Prima recupera l'ID della lista DA FARE
            lists_url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/lists"
            lists_response = requests.get(lists_url, params={'key': TRELLO_API_KEY, 'token': TRELLO_TOKEN})
            lists = lists_response.json()

            da_fare_id = None
            for lst in lists:
                if lst['name'] == 'DA FARE':
                    da_fare_id = lst['id']
                    break

            if da_fare_id:
                filtered_cards = [card for card in all_cards if card['idList'] == da_fare_id]
            else:
                filtered_cards = all_cards

        # Mostra i dettagli delle card
        print(f"\n🔍 DETTAGLI CARD TRELLO")
        print("=" * 80)

        for i, card in enumerate(filtered_cards[:limit]):
            print(f"\n📋 CARD {i+1}: {card['name']}")
            print("-" * 80)

            # Informazioni base
            print(f"ID: {card['id']}")
            print(f"URL: {card['url']}")

            # Descrizione
            if card.get('desc'):
                print(f"\n📝 DESCRIZIONE:")
                print(card['desc'])

            # Etichette
            if card.get('labels'):
                print(f"\n🏷️  ETICHETTE:")
                for label in card['labels']:
                    print(f"  - {label['name']} ({label['color']})")

            # Date
            if card.get('due'):
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                print(f"\n📅 SCADENZA:")
                print(f"  Data/ora UTC: {card['due']}")
                print(f"  Data/ora locale: {due_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Solo data: {due_date.strftime('%d/%m/%Y')}")
                print(f"  Completata: {'✅' if card.get('dueComplete') else '❌'}")

            # Altri campi interessanti
            print(f"\n📊 ALTRI DETTAGLI:")
            print(f"  Posizione: {card.get('pos')}")
            print(f"  Ultima attività: {card.get('dateLastActivity')}")

            # Mostra tutti i campi disponibili (debug completo)
            if i == 0:  # Solo per la prima card
                print(f"\n🔧 TUTTI I CAMPI DISPONIBILI:")
                for key in sorted(card.keys()):
                    if key not in ['id', 'name', 'desc', 'labels', 'due', 'url', 'pos', 'dateLastActivity']:
                        value = card[key]
                        if isinstance(value, (dict, list)) and value:
                            print(f"  {key}: <{type(value).__name__}>")
                        elif value:
                            print(f"  {key}: {value}")

        print(f"\n\nMostrate {min(limit, len(filtered_cards))} di {len(filtered_cards)} card trovate")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Errore HTTP: {e}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Funzione principale."""
    if not all([TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID]):
        print("❌ Credenziali Trello mancanti nel file .env!")
        return 1

    # Se viene passato un argomento, usalo come pattern di ricerca
    if len(sys.argv) > 1:
        pattern = ' '.join(sys.argv[1:])
        print(f"Cerco card contenenti: '{pattern}'")
        get_card_details(pattern, limit=5)
    else:
        print("Mostro le prime card dalla lista DA FARE")
        get_card_details(limit=3)

    return 0

if __name__ == '__main__':
    sys.exit(main())
