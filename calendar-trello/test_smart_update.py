#!/usr/bin/env python3
"""
Script di test per la funzionalità Smart Daily Update.
Testa il nuovo metodo smart_daily_update che preserva le task non completate.
"""

import sys
import os
from datetime import datetime, timedelta
from economato_trello import EconomatoTrello

def print_separator(title):
    """Stampa un separatore con titolo."""
    print("\n" + "=" * 80)
    print(f"🧪 {title}")
    print("=" * 80)

def test_smart_update_vs_traditional():
    """Confronta l'aggiornamento smart vs tradizionale."""
    print_separator("TEST: Smart Update vs Traditional Update")

    try:
        # Inizializza il manager
        manager = EconomatoTrello()

        print("\n1️⃣ Stato iniziale della lista DA FARE:")
        print("-" * 50)

        # Recupera card esistenti
        if 'DA FARE' in manager.trello_lists:
            import requests
            url = f"https://api.trello.com/1/lists/{manager.trello_lists['DA FARE']}/cards"
            params = {
                'key': manager.trello_api_key,
                'token': manager.trello_token
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                existing_cards = response.json()
                print(f"📋 Card esistenti: {len(existing_cards)}")
                for i, card in enumerate(existing_cards[:5], 1):  # Mostra prime 5
                    print(f"  {i}. {card['name']}")
                if len(existing_cards) > 5:
                    print(f"  ... e altre {len(existing_cards) - 5} card")
            else:
                print("❌ Errore recupero card esistenti")
                return
        else:
            print("❌ Lista DA FARE non trovata")
            return

        print(f"\n2️⃣ Test Smart Update (preserva task esistenti):")
        print("-" * 50)

        # Esegue smart update
        manager.smart_daily_update(day_offset=0, use_template=True)

        print(f"\n3️⃣ Confronto con metodo tradizionale:")
        print("-" * 50)
        print("ℹ️  Il metodo tradizionale cancellerebbe TUTTE le card esistenti")
        print("ℹ️  e creerebbe solo quelle del giorno corrente")
        print("ℹ️  Il metodo smart preserva quelle che coincidono e rimuove solo quelle obsolete")

    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()

def test_different_days():
    """Testa l'aggiornamento per giorni diversi."""
    print_separator("TEST: Smart Update per giorni diversi")

    try:
        manager = EconomatoTrello()

        days = ['oggi', 'domani', 'dopodomani']
        offsets = [0, 1, 2]

        for day, offset in zip(days, offsets):
            target_date = datetime.now() + timedelta(days=offset)
            weekday_it = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica'][target_date.weekday()]

            print(f"\n📅 Test per {day} ({weekday_it} {target_date.strftime('%d/%m/%Y')}):")
            print("-" * 60)

            # Recupera eventi per questo giorno
            events_by_calendar = manager.get_events_for_day(target_date, use_template=True)

            total_events = sum(len(events) for events in events_by_calendar.values())
            print(f"📊 Eventi trovati nel template: {total_events}")

            for calendar_name, events in events_by_calendar.items():
                if events:
                    print(f"  📋 {calendar_name}: {len(events)} eventi")
                    for event in events[:3]:  # Mostra primi 3
                        title = event.get('summary', 'Senza titolo')
                        print(f"    - {title}")
                    if len(events) > 3:
                        print(f"    ... e altri {len(events) - 3}")

            if total_events == 0:
                print("  ℹ️  Nessun evento trovato per questo giorno")

    except Exception as e:
        print(f"❌ Errore durante il test giorni: {e}")
        import traceback
        traceback.print_exc()

def test_duplicate_detection():
    """Testa il rilevamento dei duplicati."""
    print_separator("TEST: Rilevamento Duplicati")

    try:
        manager = EconomatoTrello()

        print("🔍 Questo test simula il rilevamento dei duplicati...")
        print("   (senza effettuare modifiche reali)")

        # Simula task esistenti
        existing_tasks = [
            "SCARICO Fornitore ABC",
            "CARICO Reparto Cucina",
            "ORDINE Frutta e Verdura",
        ]

        # Simula nuove task del giorno
        new_tasks = [
            "SCARICO Fornitore ABC",  # Duplicato - da preservare
            "CARICO Reparto Bar",     # Nuovo - da aggiungere
            "ORDINE Carne e Pesce",   # Nuovo - da aggiungere
        ]

        print(f"\n📋 Task esistenti simulate:")
        for task in existing_tasks:
            print(f"  ✓ {task}")

        print(f"\n📋 Nuove task del giorno simulate:")
        for task in new_tasks:
            print(f"  • {task}")

        # Analisi duplicati
        existing_set = set(existing_tasks)
        new_set = set(new_tasks)

        to_preserve = new_set & existing_set
        to_add = new_set - existing_set
        to_remove = existing_set - new_set

        print(f"\n📊 Analisi:")
        print(f"  🔄 Da preservare: {len(to_preserve)}")
        for task in to_preserve:
            print(f"    ✓ {task}")

        print(f"  ➕ Da aggiungere: {len(to_add)}")
        for task in to_add:
            print(f"    + {task}")

        print(f"  🗑️  Da rimuovere: {len(to_remove)}")
        for task in to_remove:
            print(f"    - {task}")

    except Exception as e:
        print(f"❌ Errore durante il test duplicati: {e}")

def show_usage():
    """Mostra le opzioni di utilizzo."""
    print_separator("SMART UPDATE TESTER")
    print("\nOpzioni disponibili:")
    print("  1. Test completo (smart vs traditional)")
    print("  2. Test giorni diversi")
    print("  3. Test rilevamento duplicati")
    print("  4. Esegui tutti i test")
    print("  0. Esci")

def main():
    """Funzione principale."""
    print("🧪 ECONOMATO TRELLO - SMART UPDATE TESTER")
    print("=" * 80)
    print("⚠️  ATTENZIONE: Questo script effettua test reali su Trello!")
    print("   Assicurati di avere i permessi corretti e un backup.")

    while True:
        show_usage()
        choice = input("\n👉 Scegli un'opzione: ").strip()

        if choice == '0':
            print("\n👋 Test completati!")
            break
        elif choice == '1':
            test_smart_update_vs_traditional()
        elif choice == '2':
            test_different_days()
        elif choice == '3':
            test_duplicate_detection()
        elif choice == '4':
            print("\n🚀 Esecuzione di tutti i test...")
            test_duplicate_detection()
            test_different_days()
            test_smart_update_vs_traditional()
            print("\n✅ Tutti i test completati!")
        else:
            print("\n❌ Opzione non valida!")

        if choice in ['1', '2', '3', '4']:
            input("\nPremi INVIO per continuare...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrotti dall'utente")
    except Exception as e:
        print(f"\n❌ Errore imprevisto: {e}")
        import traceback
        traceback.print_exc()
