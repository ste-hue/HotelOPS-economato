#!/usr/bin/env python3
"""
CLI Menu per la gestione automatica del Trello dell'economato.
Permette di preparare, pulire e gestire le task in modo automatico.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, time
from typing import Optional
import schedule
import time as time_module
from economato_trello import EconomatoTrello

# Configurazione
AUTOMATIC_PREPARE_TIME = "05:00"  # Orario per preparazione automatica
STATE_FILE = "economato_state.json"
CHECK_INTERVAL = 300  # Controlla ogni 5 minuti se serve aggiornare


class EconomatoCLI:
    def __init__(self):
        self.economato = EconomatoTrello()
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Carica lo stato salvato o crea uno nuovo."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'last_prepared_date': None,
            'automatic_mode': False
        }

    def save_state(self):
        """Salva lo stato corrente."""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def clear_screen(self):
        """Pulisce lo schermo."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def show_header(self):
        """Mostra l'intestazione del menu."""
        self.clear_screen()
        print("=" * 70)
        print("🏨 ECONOMATO TRELLO - GESTIONE AUTOMATICA")
        print("=" * 70)
        self.interactive = sys.stdin.isatty()  # Check if running interactively

        # Mostra info stato
        now = datetime.now()
        print(f"📅 Data/Ora: {now.strftime('%A %d/%m/%Y - %H:%M')}")

        if self.state['last_prepared_date']:
            last_date = datetime.fromisoformat(self.state['last_prepared_date'])
            print(f"📋 Ultima preparazione: {last_date.strftime('%d/%m/%Y')}")

        if self.state['automatic_mode']:
            print(f"🤖 Modalità automatica: ATTIVA (ore {AUTOMATIC_PREPARE_TIME})")

        print("=" * 70)

    def prepare_today(self):
        """Prepara le task per oggi."""
        print("\n🔄 Aggiornamento task DA FARE per OGGI...")

        # Controlla se serve davvero aggiornare
        if self.is_update_needed():
            # Prima pulisce la lista DA FARE
            print("\n🧹 Pulizia lista DA FARE (task vecchie)...")
            self.economato.clear_list('DA FARE')

            # Poi prepara per oggi
            print("\n📋 Creazione nuove task per oggi...")
            self.economato.prepare_day(day_offset=0, use_template=True)

            # Aggiorna stato
            self.state['last_prepared_date'] = datetime.now().date().isoformat()
            self.save_state()

            print("\n✅ Lista DA FARE aggiornata!")
        else:
            print("\n✅ Le task sono già aggiornate per oggi")

        if self.interactive:
            input("\nPremi INVIO per continuare...")

    def prepare_tomorrow(self):
        """Prepara le task per domani."""
        print("\n🔄 Preparazione task DA FARE per DOMANI...")

        # Pulisce sempre quando prepara per domani
        print("\n🧹 Pulizia lista DA FARE...")
        self.economato.clear_list('DA FARE')

        # Poi prepara per domani
        print("\n📋 Creazione task per domani...")
        self.economato.prepare_day(day_offset=1, use_template=True)

        # Aggiorna stato
        tomorrow = datetime.now() + timedelta(days=1)
        self.state['last_prepared_date'] = tomorrow.date().isoformat()
        self.save_state()

        print("\n✅ Task per domani preparate!")
        if self.interactive:
            input("\nPremi INVIO per continuare...")

    def is_update_needed(self):
        """Controlla se la lista DA FARE deve essere aggiornata."""
        today = datetime.now().date()

        # Se non è mai stato preparato
        if not self.state['last_prepared_date']:
            return True

        last_prepared = datetime.fromisoformat(self.state['last_prepared_date']).date()

        # Se l'ultima preparazione è per un giorno diverso da oggi
        return last_prepared != today

    def automatic_update(self):
        """Aggiorna automaticamente la lista DA FARE se necessario."""
        if self.is_update_needed():
            now = datetime.now()
            print(f"\n🤖 Aggiornamento automatico DA FARE - {now.strftime('%d/%m/%Y %H:%M')}")

            # Pulisce solo DA FARE e prepara per oggi
            self.economato.clear_list('DA FARE')
            self.economato.prepare_day(day_offset=0, use_template=True)

            # Aggiorna stato
            self.state['last_prepared_date'] = now.date().isoformat()
            self.save_state()

            print("✅ Lista DA FARE aggiornata automaticamente!")
            return True
        return False

    def toggle_automatic_mode(self):
        """Attiva/disattiva la modalità automatica."""
        self.state['automatic_mode'] = not self.state['automatic_mode']
        self.save_state()

        if self.state['automatic_mode']:
            print(f"\n✅ Modalità automatica ATTIVATA")
            print(f"   La lista DA FARE verrà aggiornata automaticamente ogni giorno")
            print(f"   Controllo principale alle: {AUTOMATIC_PREPARE_TIME}")
            print("\n⚠️  IMPORTANTE: Lascia questo script in esecuzione!")
        else:
            print("\n❌ Modalità automatica DISATTIVATA")

        if self.interactive:
            input("\nPremi INVIO per continuare...")

    def clean_todo_list(self):
        """Pulisce solo la lista DA FARE."""
        print("\n🧹 Pulizia lista DA FARE...")

        self.economato.clear_list('DA FARE')

        # Resetta anche lo stato
        self.state['last_prepared_date'] = None
        self.save_state()

        print("\n✅ Lista DA FARE pulita!")
        if self.interactive:
            if self.interactive:
                input("\nPremi INVIO per continuare...")

    def show_week_summary(self):
        """Mostra il riepilogo settimanale."""
        print("\n📊 Riepilogo settimanale:")
        self.economato.show_week_summary()
        input("\nPremi INVIO per continuare...")

    def run_automatic_mode(self):
        """Esegue la modalità automatica."""
        print("\n🤖 MODALITÀ AUTOMATICA ATTIVA")
        print(f"   Aggiornamento principale alle: {AUTOMATIC_PREPARE_TIME}")
        print(f"   Controllo ogni: {CHECK_INTERVAL//60} minuti")
        print("\n   Premi Ctrl+C per tornare al menu principale")

        # Schedula l'aggiornamento automatico principale
        schedule.every().day.at(AUTOMATIC_PREPARE_TIME).do(self.automatic_update)

        # Controlla subito se serve aggiornare
        if self.automatic_update():
            print("   Lista DA FARE aggiornata all'avvio")

        last_check = datetime.now()

        try:
            while self.state['automatic_mode']:
                schedule.run_pending()

                # Controlla periodicamente se serve aggiornare (es. dopo mezzanotte)
                if (datetime.now() - last_check).seconds >= CHECK_INTERVAL:
                    if self.automatic_update():
                        print(f"   🔄 Aggiornamento eseguito alle {datetime.now().strftime('%H:%M')}")
                    last_check = datetime.now()

                time_module.sleep(30)  # Controlla ogni 30 secondi

                # Mostra heartbeat ogni ora
                if datetime.now().minute == 0 and datetime.now().second < 30:
                    print(f"   ⏰ {datetime.now().strftime('%H:%M')} - Sistema attivo, lista aggiornata per: {self.state.get('last_prepared_date', 'MAI')}")

        except KeyboardInterrupt:
            print("\n\n⏹️  Modalità automatica interrotta")
            time_module.sleep(1)

    def show_menu(self):
        """Mostra il menu principale."""
        while True:
            self.show_header()

            print("\n📋 MENU PRINCIPALE:\n")
            print("  1. 📅 Aggiorna task DA FARE per OGGI")
            print("  2. 📆 Prepara task DA FARE per DOMANI")
            print("  3. 🧹 Pulisci lista DA FARE")
            print("  4. 📊 Mostra riepilogo settimanale")
            print("  5. 🤖 Attiva/Disattiva modalità automatica")

            if self.state['automatic_mode']:
                print("  6. ▶️  Avvia modalità automatica")

            print("\n  0. 🚪 Esci")

            choice = input("\n👉 Scegli un'opzione: ").strip()

            if choice == '1':
                self.prepare_today()
            elif choice == '2':
                self.prepare_tomorrow()
            elif choice == '3':
                self.clean_todo_list()
            elif choice == '4':
                self.show_week_summary()
            elif choice == '5':
                self.toggle_automatic_mode()
            elif choice == '6' and self.state['automatic_mode']:
                self.run_automatic_mode()
            elif choice == '0':
                print("\n👋 Arrivederci!")
                break
            else:
                print("\n❌ Opzione non valida!")
                if self.interactive:
                    input("\nPremi INVIO per continuare...")

    def run_once(self, action: str):
        """Esegue un'azione singola da linea di comando."""
        if action == 'today':
            self.prepare_today()
        elif action == 'tomorrow':
            self.prepare_tomorrow()
        elif action == 'clean':
            self.clean_todo_list()
        elif action == 'auto':
            self.automatic_update()
        else:
            print(f"❌ Azione sconosciuta: {action}")


def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(description='Gestione automatica Trello Economato')
    parser.add_argument('--action', choices=['today', 'tomorrow', 'clean', 'auto'],
                        help='Esegue un\'azione singola: today=aggiorna per oggi, tomorrow=prepara per domani, clean=pulisci DA FARE, auto=aggiorna se necessario')
    parser.add_argument('--daemon', action='store_true',
                        help='Esegue in modalità daemon per automazione')

    args = parser.parse_args()

    try:
        cli = EconomatoCLI()

        if args.action:
            # Esegue azione singola
            cli.run_once(args.action)
        elif args.daemon:
            # Modalità daemon
            cli.state['automatic_mode'] = True
            cli.save_state()
            cli.run_automatic_mode()
        else:
            # Menu interattivo
            cli.show_menu()

    except KeyboardInterrupt:
        print("\n\n⏹️  Programma interrotto")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
