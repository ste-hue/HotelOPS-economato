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
DEFAULT_CHECK_INTERVAL = 86400  # Controlla ogni 24 ore se serve aggiornare


class EconomatoCLI:
    def __init__(self):
        self.economato = EconomatoTrello()
        self.state = self.load_state()
        self.interactive = sys.stdin.isatty()  # Rileva se è modalità interattiva

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
            'automatic_mode': False,
            'smart_mode': True,  # Usa aggiornamento intelligente per default
            'check_interval_hours': 24  # Controlla ogni 24 ore per default
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

        # Mostra info stato
        now = datetime.now()
        print(f"📅 Data/Ora: {now.strftime('%A %d/%m/%Y - %H:%M')}")

        if self.state['last_prepared_date']:
            last_date = datetime.fromisoformat(self.state['last_prepared_date'])
            print(f"📋 Ultima preparazione: {last_date.strftime('%d/%m/%Y')}")

        if self.state['automatic_mode']:
            mode_type = "INTELLIGENTE" if self.state.get('smart_mode', True) else "TRADIZIONALE"
            check_hours = self.state.get('check_interval_hours', 24)
            print(f"🤖 Modalità automatica: ATTIVA (ore {AUTOMATIC_PREPARE_TIME}) - {mode_type}")
            print(f"   Controllo ogni: {check_hours} ore")

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

    def smart_prepare_today(self):
        """Prepara le task per oggi con aggiornamento intelligente (preserva task non completate)."""
        print("\n🔄 Aggiornamento intelligente task DA FARE per OGGI...")

        # Controlla se serve davvero aggiornare
        if self.is_update_needed():
            # Usa l'aggiornamento intelligente invece di cancellare tutto
            self.economato.smart_daily_update(day_offset=0, use_template=True)

            # Aggiorna stato
            self.state['last_prepared_date'] = datetime.now().date().isoformat()
            self.save_state()

            print("\n✅ Lista DA FARE aggiornata intelligentemente!")
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
            mode_type = "intelligente" if self.state.get('smart_mode', True) else "tradizionale"
            print(f"\n🤖 Aggiornamento automatico DA FARE ({mode_type}) - {now.strftime('%d/%m/%Y %H:%M')}")

            # Usa aggiornamento intelligente o tradizionale in base alla configurazione
            if self.state.get('smart_mode', True):
                self.economato.smart_daily_update(day_offset=0, use_template=True)
            else:
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
            mode_type = "intelligente" if self.state.get('smart_mode', True) else "tradizionale"
            print(f"\n✅ Modalità automatica ATTIVATA ({mode_type})")
            print(f"   La lista DA FARE verrà aggiornata automaticamente ogni giorno")
            print(f"   Controllo principale alle: {AUTOMATIC_PREPARE_TIME}")
            print("\n⚠️  IMPORTANTE: Lascia questo script in esecuzione!")
        else:
            print("\n❌ Modalità automatica DISATTIVATA")

        if self.interactive:
            input("\nPremi INVIO per continuare...")

    def toggle_smart_mode(self):
        """Attiva/disattiva la modalità intelligente per gli aggiornamenti automatici."""
        self.state['smart_mode'] = not self.state.get('smart_mode', True)
        self.save_state()

        if self.state['smart_mode']:
            print(f"\n🧠 Modalità INTELLIGENTE ATTIVATA")
            print(f"   Gli aggiornamenti automatici preserveranno le task non completate")
        else:
            print(f"\n🔄 Modalità TRADIZIONALE ATTIVATA")
            print(f"   Gli aggiornamenti automatici cancelleranno tutte le task esistenti")

        if self.interactive:
            input("\nPremi INVIO per continuare...")

    def configure_check_interval(self):
        """Configura l'intervallo di controllo automatico."""
        current_hours = self.state.get('check_interval_hours', 24)
        print(f"\n⏰ Configurazione Intervallo di Controllo")
        print(f"   Intervallo attuale: ogni {current_hours} ore")
        print("\n   Opzioni predefinite:")
        print("   1. Ogni ora (1 ora)")
        print("   2. Ogni 6 ore")
        print("   3. Ogni 12 ore")
        print("   4. Ogni 24 ore (consigliato)")
        print("   5. Ogni 48 ore")
        print("   6. Personalizzato")

        choice = input("\n👉 Scegli opzione (1-6): ").strip()

        interval_map = {
            '1': 1,
            '2': 6,
            '3': 12,
            '4': 24,
            '5': 48
        }

        if choice in interval_map:
            new_hours = interval_map[choice]
            self.state['check_interval_hours'] = new_hours
            self.save_state()
            print(f"\n✅ Intervallo impostato: ogni {new_hours} ore")
        elif choice == '6':
            try:
                new_hours = int(input("\n   Inserisci ore (1-168): "))
                if 1 <= new_hours <= 168:  # Max 1 settimana
                    self.state['check_interval_hours'] = new_hours
                    self.save_state()
                    print(f"\n✅ Intervallo personalizzato: ogni {new_hours} ore")
                else:
                    print("\n❌ Valore non valido (1-168 ore)")
            except ValueError:
                print("\n❌ Inserisci un numero valido")
        else:
            print("\n❌ Opzione non valida!")

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
        check_hours = self.state.get('check_interval_hours', 24)
        check_interval_seconds = check_hours * 3600

        print("\n🤖 MODALITÀ AUTOMATICA ATTIVA")
        print(f"   Aggiornamento principale alle: {AUTOMATIC_PREPARE_TIME}")
        print(f"   Controllo ogni: {check_hours} ore")
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

                # Controlla periodicamente se serve aggiornare
                if (datetime.now() - last_check).seconds >= check_interval_seconds:
                    if self.automatic_update():
                        print(f"   🔄 Aggiornamento eseguito alle {datetime.now().strftime('%H:%M')}")
                    last_check = datetime.now()

                time_module.sleep(3600)  # Controlla ogni ora

                # Mostra heartbeat ogni 24 ore alle 6:00
                if datetime.now().hour == 6 and datetime.now().minute == 0 and datetime.now().second < 60:
                    print(f"   ⏰ {datetime.now().strftime('%H:%M')} - Sistema attivo, lista aggiornata per: {self.state.get('last_prepared_date', 'MAI')}")

        except KeyboardInterrupt:
            print("\n\n⏹️  Modalità automatica interrotta")
            time_module.sleep(1)

    def show_menu(self):
        """Mostra il menu principale."""
        while True:
            self.show_header()

            print("\n📋 MENU PRINCIPALE:\n")
            print("  1. 📅 Aggiorna task DA FARE per OGGI (cancella tutto)")
            print("  2. 🧠 Aggiorna INTELLIGENTE per OGGI (preserva non completate)")
            print("  3. 📆 Prepara task DA FARE per DOMANI")
            print("  4. 🧹 Pulisci lista DA FARE")
            print("  5. 📊 Mostra riepilogo settimanale")
            print("  6. 🤖 Attiva/Disattiva modalità automatica")

            smart_status = "🧠 INTELLIGENTE" if self.state.get('smart_mode', True) else "🔄 TRADIZIONALE"
            print(f"  7. {smart_status} Cambia modalità aggiornamento automatico")

            check_hours = self.state.get('check_interval_hours', 24)
            print(f"  8. ⏰ Configura intervallo controllo (ogni {check_hours}h)")

            if self.state['automatic_mode']:
                print("  9. ▶️  Avvia modalità automatica")

            print("\n  0. 🚪 Esci")

            choice = input("\n👉 Scegli un'opzione: ").strip()

            if choice == '1':
                self.prepare_today()
            elif choice == '2':
                self.smart_prepare_today()
            elif choice == '3':
                self.prepare_tomorrow()
            elif choice == '4':
                self.clean_todo_list()
            elif choice == '5':
                self.show_week_summary()
            elif choice == '6':
                self.toggle_automatic_mode()
            elif choice == '7':
                self.toggle_smart_mode()
            elif choice == '8':
                self.configure_check_interval()
            elif choice == '9' and self.state['automatic_mode']:
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
        elif action == 'smart':
            self.smart_prepare_today()
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
    parser.add_argument('--action', choices=['today', 'smart', 'tomorrow', 'clean', 'auto'],
                        help='Esegue un\'azione singola: today=aggiorna per oggi (cancella tutto), smart=aggiorna intelligente per oggi (preserva non completate), tomorrow=prepara per domani, clean=pulisci DA FARE, auto=aggiorna se necessario')
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
