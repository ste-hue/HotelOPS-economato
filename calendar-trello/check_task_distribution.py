#!/usr/bin/env python3
"""
Script rapido per controllare la distribuzione delle task nelle liste Trello.
Mostra quante task ci sono in ogni lista e alcune statistiche utili.
"""

import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configurazione Trello
TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_BOARD_ID = os.getenv('TRELLO_BOARD_ID')

def get_board_data():
    """Recupera dati completi della board."""
    try:
        url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}"
        params = {
            'key': TRELLO_API_KEY,
            'token': TRELLO_TOKEN,
            'lists': 'open',
            'cards': 'open',
            'card_fields': 'name,due,dateLastActivity,idList'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"❌ Errore recupero dati board: {e}")
        return None

def format_duration(date_str):
    """Formatta la durata da una data."""
    if not date_str:
        return "Sconosciuto"

    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(date.tzinfo)
        diff = now - date

        if diff.days > 0:
            return f"{diff.days}g fa"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h fa"
        else:
            minutes = diff.seconds // 60
            return f"{minutes}m fa"
    except:
        return "Sconosciuto"

def analyze_tasks():
    """Analizza la distribuzione delle task."""
    print("🔍 ANALISI DISTRIBUZIONE TASK - ECONOMATO TRELLO")
    print("=" * 70)

    # Recupera dati
    board_data = get_board_data()
    if not board_data:
        return

    # Organizza dati
    lists = {lst['id']: lst for lst in board_data['lists']}
    cards_by_list = {}

    for lst_id in lists:
        cards_by_list[lst_id] = []

    for card in board_data['cards']:
        if card['idList'] in cards_by_list:
            cards_by_list[card['idList']].append(card)

    # Statistiche generali
    total_cards = len(board_data['cards'])
    print(f"📊 RIEPILOGO GENERALE")
    print(f"   Totale task attive: {total_cards}")
    print(f"   Ultima analisi: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Analisi per lista
    print(f"\n📋 DISTRIBUZIONE PER LISTA:")
    print("-" * 70)

    # Ordina liste per importanza
    important_lists = ['DA FARE', 'IN LAVORAZIONE', 'ESEGUITO', 'IN GESTIONE ESTERNA', 'IN CONSEGNA']

    for lst in board_data['lists']:
        list_name = lst['name']
        list_cards = cards_by_list[lst['id']]
        count = len(list_cards)

        if count > 0 or list_name in important_lists:
            percentage = (count / total_cards * 100) if total_cards > 0 else 0

            # Icona in base al tipo di lista
            if list_name == 'DA FARE':
                icon = "📝"
            elif list_name == 'IN LAVORAZIONE':
                icon = "⚙️"
            elif list_name == 'ESEGUITO':
                icon = "✅"
            elif 'GESTIONE' in list_name:
                icon = "🏢"
            elif 'CONSEGNA' in list_name:
                icon = "🚚"
            else:
                icon = "📂"

            print(f"{icon} {list_name:20} {count:3} task ({percentage:5.1f}%)")

            # Dettagli extra per DA FARE
            if list_name == 'DA FARE' and count > 0:
                print("   📊 Dettagli task DA FARE:")

                # Task con scadenza oggi/passata
                today = datetime.now().date()
                overdue = 0
                due_today = 0
                no_due = 0

                for card in list_cards[:5]:  # Mostra prime 5
                    due_str = "Nessuna scadenza"
                    if card.get('due'):
                        try:
                            due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00')).date()
                            if due_date < today:
                                overdue += 1
                                due_str = f"SCADUTA ({due_date.strftime('%d/%m')})"
                            elif due_date == today:
                                due_today += 1
                                due_str = f"OGGI ({due_date.strftime('%d/%m')})"
                            else:
                                due_str = f"{due_date.strftime('%d/%m')}"
                        except:
                            no_due += 1
                    else:
                        no_due += 1

                    last_activity = format_duration(card.get('dateLastActivity'))
                    task_name = card['name'][:40] + "..." if len(card['name']) > 40 else card['name']
                    print(f"      • {task_name}")
                    print(f"        Scadenza: {due_str} | Ultima attività: {last_activity}")

                if count > 5:
                    print(f"      ... e altre {count - 5} task")

                print(f"   🚨 Task scadute: {overdue}")
                print(f"   📅 Task in scadenza oggi: {due_today}")
                print(f"   ⏱️  Task senza scadenza: {no_due}")

    # Analisi task vecchie
    print(f"\n⏰ ANALISI ATTIVITÀ:")
    print("-" * 70)

    week_ago = datetime.now() - timedelta(days=7)
    old_tasks = 0
    recent_tasks = 0

    for card in board_data['cards']:
        if card.get('dateLastActivity'):
            try:
                last_activity = datetime.fromisoformat(card['dateLastActivity'].replace('Z', '+00:00'))
                if last_activity < week_ago:
                    old_tasks += 1
                else:
                    recent_tasks += 1
            except:
                old_tasks += 1
        else:
            old_tasks += 1

    print(f"🆕 Task attive (ultima settimana): {recent_tasks}")
    print(f"🕰️  Task ferme (oltre 1 settimana): {old_tasks}")

    if old_tasks > 0:
        print(f"   ⚠️  Ci sono {old_tasks} task che potrebbero aver bisogno di attenzione")

    # Raccomandazioni
    print(f"\n💡 RACCOMANDAZIONI:")
    print("-" * 70)

    da_fare_count = len(cards_by_list.get(next((lst['id'] for lst in board_data['lists'] if lst['name'] == 'DA FARE'), None), []))
    eseguito_count = len(cards_by_list.get(next((lst['id'] for lst in board_data['lists'] if lst['name'] == 'ESEGUITO'), None), []))

    if da_fare_count > 20:
        print("📝 Lista DA FARE molto piena - considera di spostare task completate")

    if da_fare_count > eseguito_count * 3:
        print("⚡ Molte task da fare vs completate - verifica il carico di lavoro")

    if old_tasks > total_cards * 0.3:
        print("🔄 Molte task ferme - potrebbe servire una revisione generale")

    print(f"\n✅ Analisi completata! Usa Smart Update per aggiungere nuove task preservando quelle esistenti.")

def main():
    """Funzione principale."""
    try:
        analyze_tasks()
    except KeyboardInterrupt:
        print("\n\n⏹️  Analisi interrotta")
    except Exception as e:
        print(f"\n❌ Errore imprevisto: {e}")

if __name__ == "__main__":
    main()
