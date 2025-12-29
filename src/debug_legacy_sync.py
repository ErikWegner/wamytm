import os
import logging
import sys
from imap_app.sync_service import EmailSyncService

# Logging konfigurieren
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
logger = logging.getLogger('imap_app')
logger.setLevel(logging.INFO)

print("\n=== Manueller Sync (Legacy Mode: Nur Environment-Variablen) ===\n")

# 1. Konfiguration direkt aus Environment lesen (umgeht Datenbank)
host = os.environ.get('IMAP_HOST')
username = os.environ.get('IMAP_USERNAME')
password = os.environ.get('IMAP_PASSWORD')

print(f"Lese Environment-Variablen:")
print(f"IMAP_HOST: {host}")
print(f"IMAP_USERNAME: {username}")
print(f"IMAP_PASSWORD: {'***' if password else 'NICHT GESETZT'}")
print(f"IMAP_PORT: {os.environ.get('IMAP_PORT', '993 (default)')}")
print(f"IMAP_USE_SSL: {os.environ.get('IMAP_USE_SSL', 'True (default)')}")
print(f"IMAP_VERIFY_CERT: {os.environ.get('IMAP_VERIFY_CERT', 'True (default)')}")

if not all([host, username, password]):
    print("\n❌ FEHLER: IMAP_HOST, IMAP_USERNAME oder IMAP_PASSWORD fehlen im Environment!")
    sys.exit(1)

config = {
    'host': host,
    'port': int(os.environ.get('IMAP_PORT', '993')),
    'username': username,
    'password': password,
    'use_ssl': os.environ.get('IMAP_USE_SSL', 'True').lower() in ('true', '1', 'yes'),
    'verify_cert': os.environ.get('IMAP_VERIFY_CERT', 'True').lower() in ('true', '1', 'yes'),
    'folder': os.environ.get('IMAP_FOLDER', 'INBOX'),
}

print(f"\nStarte Sync mit: {config['username']}@{config['host']}:{config['port']}")
print(f"Passwort (Klartext): '{config['password']}'")

# 2. Service initialisieren und Sync starten
try:
    service = EmailSyncService(config)
    log = service.sync()
    
    print(f"\nErgebnis: {log.status}")
    if log.status == 'error':
        print(f"❌ Fehler: {log.error_message}")
    else:
        print(f"✅ Erfolg! Neu: {log.emails_new}, Aktualisiert: {log.emails_updated}")

except Exception as e:
    print(f"\n❌ KRITISCHER FEHLER: {e}")
    import traceback
    traceback.print_exc()
