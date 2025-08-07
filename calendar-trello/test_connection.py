#!/usr/bin/env python3
"""
Script di test per verificare la connessione a Google Calendar e Trello.
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Carica variabili d'ambiente
load_dotenv()

def test_google_connection():
    """Testa la connessione a Google Calendar."""
    print("\n🔍 TEST CONNESSIONE GOOGLE CALENDAR")
    print("=" * 50)

    try:
        # Verifica file credenziali
        if not os.path.exists('HotelopsSuite.json'):
            print("❌ File HotelopsSuite.json non trovato!")
            return False

        # Carica credenziali
        credentials = service_account.Credentials.from_service_account_file(
            'HotelopsSuite.json',
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )

        # Impersona utente
        delegated_credentials = credentials.with_subject('magazzino@panoramagroup.it')

        # Crea servizio
        service = build('calendar', 'v3', credentials=delegated_credentials)

        # Prova a listare i calendari
        calendar_list = service.calendarList().list(maxResults=10).execute()
        calendars = calendar_list.get('items', [])

        print(f"✅ Connessione Google OK - Trovati {len(calendars)} calendari:")
        for cal in calendars[:5]:  # Mostra solo i primi 5
            print(f"   - {cal.get('summary', 'Senza nome')}")

        return True

    except Exception as e:
        print(f"❌ Errore connessione Google: {e}")
        return False

def test_trello_connection():
    """Testa la connessione a Trello."""
    print("\n🔍 TEST CONNESSIONE TRELLO")
    print("=" * 50)

    try:
        # Recupera credenziali
        api_key = os.getenv('TRELLO_API_KEY')
        token = os.getenv('TRELLO_TOKEN')
        board_id = os.getenv('TRELLO_BOARD_SHORTLINK')

        if not all([api_key, token, board_id]):
            print("❌ Credenziali Trello mancanti nel file .env!")
            print(f"   API_KEY: {'✓' if api_key else '✗'}")
            print(f"   TOKEN: {'✓' if token else '✗'}")
            print(f"   BOARD_ID: {'✓' if board_id else '✗'}")
            return False

        # Test API - recupera info board
        url = f"https://api.trello.com/1/boards/{board_id}"
        params = {
            'key': api_key,
            'token': token,
            'fields': 'name,desc,url'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        board_info = response.json()
        print(f"✅ Connessione Trello OK")
        print(f"   Board: {board_info.get('name', 'N/A')}")
        print(f"   URL: {board_info.get('url', 'N/A')}")

        # Recupera liste
        url = f"https://api.trello.com/1/boards/{board_id}/lists"
        response = requests.get(url, params={'key': api_key, 'token': token})
        lists = response.json()

        print(f"\n   Liste trovate ({len(lists)}):")
        for lst in lists:
            print(f"   - {lst['name']}")

        return True

    except requests.exceptions.HTTPError as e:
        print(f"❌ Errore HTTP Trello: {e}")
        print(f"   Status code: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Errore connessione Trello: {e}")
        return False

def test_template():
    """Verifica la presenza del template settimanale."""
    print("\n🔍 TEST TEMPLATE SETTIMANALE")
    print("=" * 50)

    template_file = 'week_template_2025_01_15_service_account.json'

    if not os.path.exists(template_file):
        print(f"❌ Template {template_file} non trovato!")
        return False

    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)

        total_events = 0
        print(f"✅ Template caricato correttamente")
        print(f"\n   Eventi per calendario:")

        for cal_name, cal_data in template.get('calendars', {}).items():
            events_count = cal_data.get('events_count', 0)
            total_events += events_count
            print(f"   - {cal_name}: {events_count} eventi")

        print(f"\n   Totale eventi nel template: {total_events}")

        # Mostra distribuzione per giorno
        days_count = {i: 0 for i in range(7)}
        weekdays_it = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']

        for cal_data in template['calendars'].values():
            for event in cal_data.get('events', []):
                if 'dateTime' in event.get('start', {}):
                    event_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    days_count[event_date.weekday()] += 1

        print(f"\n   Distribuzione settimanale:")
        for day_idx, count in days_count.items():
            print(f"   - {weekdays_it[day_idx]}: {count} eventi")

        return True

    except Exception as e:
        print(f"❌ Errore lettura template: {e}")
        return False

def main():
    """Esegue tutti i test."""
    print("\n🏪 ECONOMATO TRELLO - TEST DI CONNESSIONE")
    print("=" * 60)
    print(f"Data/ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Esegui test
    google_ok = test_google_connection()
    trello_ok = test_trello_connection()
    template_ok = test_template()

    # Riepilogo
    print("\n📊 RIEPILOGO TEST")
    print("=" * 50)
    print(f"Google Calendar: {'✅ OK' if google_ok else '❌ ERRORE'}")
    print(f"Trello API:      {'✅ OK' if trello_ok else '❌ ERRORE'}")
    print(f"Template:        {'✅ OK' if template_ok else '❌ ERRORE'}")

    if all([google_ok, trello_ok, template_ok]):
        print("\n✅ TUTTI I TEST PASSATI - Sistema pronto all'uso!")
        return 0
    else:
        print("\n❌ ALCUNI TEST FALLITI - Verifica la configurazione")
        return 1

if __name__ == '__main__':
    sys.exit(main())
