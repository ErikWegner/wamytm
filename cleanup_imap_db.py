#!/usr/bin/env python
"""
Cleanup-Skript für die imap_app Datenbank.
Löscht alle IMAP_APP Tabellen, Indizes, Constraints und Sequences.
"""
import os
import sys
import django

# Django Setup
sys.path.insert(0, '/home/florian/wamytm/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wamytmsite.settings')
django.setup()

from django.db import connections

def cleanup_imap_db():
    cursor = connections['imap_app'].cursor()
    
    print("=== Cleanup imap_app Datenbank ===\n")
    
    # 1. Lösche alle Tabellen
    print("1. Lösche Tabellen...")
    cursor.execute("SELECT table_name FROM user_tables WHERE table_name LIKE 'IMAP_APP%'")
    tables = [row[0] for row in cursor.fetchall()]
    for table in tables:
        print(f"   DROP TABLE {table} CASCADE CONSTRAINTS PURGE")
        cursor.execute(f"DROP TABLE {table} CASCADE CONSTRAINTS PURGE")
    print(f"   ✓ {len(tables)} Tabellen gelöscht\n")
    
    # 2. Lösche übrig gebliebene Indizes
    print("2. Lösche Indizes...")
    cursor.execute("SELECT index_name FROM user_indexes WHERE index_name LIKE 'IMAP_APP%'")
    indexes = [row[0] for row in cursor.fetchall()]
    for index in indexes:
        try:
            print(f"   DROP INDEX {index}")
            cursor.execute(f"DROP INDEX {index}")
        except Exception as e:
            print(f"   ⚠ Fehler bei {index}: {e}")
    print(f"   ✓ {len(indexes)} Indizes bearbeitet\n")
    
    # 3. Lösche Sequences
    print("3. Lösche Sequences...")
    cursor.execute("SELECT sequence_name FROM user_sequences WHERE sequence_name LIKE 'IMAP_APP%'")
    sequences = [row[0] for row in cursor.fetchall()]
    for seq in sequences:
        print(f"   DROP SEQUENCE {seq}")
        cursor.execute(f"DROP SEQUENCE {seq}")
    print(f"   ✓ {len(sequences)} Sequences gelöscht\n")
    
    # 4. Lösche django_migrations Einträge
    print("4. Lösche django_migrations Einträge...")
    cursor.execute("DELETE FROM django_migrations WHERE app='imap_app'")
    deleted = cursor.rowcount
    print(f"   ✓ {deleted} Einträge gelöscht\n")
    
    connections['imap_app'].connection.commit()
    print("=== Cleanup abgeschlossen ===")

if __name__ == '__main__':
    cleanup_imap_db()
