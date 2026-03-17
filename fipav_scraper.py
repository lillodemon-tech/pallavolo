!/usr/bin/env python3
"""
FIPAV Online Scraper - Estrae informazioni sui campionati di pallavolo
dal sito fipavonline.it, giornata per giornata.

Uso:
    python fipav_scraper.py                    # Mostra lista comitati
    python fipav_scraper.py --comitato 03000   # Scarica dati di un comitato
    python fipav_scraper.py --tutti             # Scarica tutti i comitati
    python fipav_scraper.py --comitato 03000 --csv  # Esporta in CSV
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installa requests: pip install requests")
    sys.exit(1)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    import hashlib
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

BASE_URL = "https://www.fipavonline.it"
COMITATI_URL = f"{BASE_URL}/live/res.json"
CACHE_URL = f"{BASE_URL}/public/cache/getGironiComiOggiv2_{{comitato_id}}.json"
CACHE_ENC_URL = f"{BASE_URL}/public/cache/getGironiComiOggiv2_{{comitato_id}}.enc"

# Chiave AES per decifrare i file .enc (estratta dal JS del sito)
AES_KEY = "2667003e35b4cede3eda114e15008a7d"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.fipavonline.it/live/index.html",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def get_session():
    """Crea una sessione HTTP con gli header corretti."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_comitati(session):
    """Scarica la lista dei comitati regionali."""
    resp = session.get(COMITATI_URL)
    resp.raise_for_status()
    return resp.json()


def decrypt_enc_data(encrypted_text):
    """Decifra i dati .enc usando CryptoJS-compatible AES decryption."""
    if not HAS_CRYPTO:
        return None
    try:
        import base64
        raw = base64.b64decode(encrypted_text)
        # CryptoJS formato: "Salted__" + 8 byte salt + ciphertext
        if raw[:8] == b"Salted__":
            salt = raw[8:16]
            ciphertext = raw[16:]
            # Derive key e iv con EVP_BytesToKey (MD5-based)
            key_iv = b""
            prev = b""
            while len(key_iv) < 48:
                prev = hashlib.md5(prev + AES_KEY.encode() + salt).digest()
                key_iv += prev
            key = key_iv[:32]
            iv = key_iv[32:48]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            return json.loads(decrypted.decode("utf-8"))
        else:
            # Senza salt
            key = hashlib.md5(AES_KEY.encode()).digest()
            key = key + hashlib.md5(key + AES_KEY.encode()).digest()
            iv = hashlib.md5(key[16:] + AES_KEY.encode()).digest()
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(raw), AES.block_size)
            return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        print(f"  [!] Errore decifrazione: {e}")
        return None


def fetch_campionati(session, comitato_id):
    """Scarica i dati dei campionati per un comitato."""
    url = CACHE_URL.format(comitato_id=comitato_id)
    try:
        resp = session.get(url)
        if resp.status_code == 200:
            return resp.json()
    except (requests.exceptions.JSONDecodeError, ValueError):
        pass

    # Fallback: prova il file .enc
    if HAS_CRYPTO:
        url_enc = CACHE_ENC_URL.format(comitato_id=comitato_id)
        try:
            resp = session.get(url_enc)
            if resp.status_code == 200:
                data = decrypt_enc_data(resp.text.strip())
                if data:
                    return data
        except Exception as e:
            print(f"  [!] Errore fetch .enc: {e}")

    print(f"  [!] Impossibile ottenere dati per comitato {comitato_id}")
    return None


def parse_campionati(data):
    """
    Parsa i dati JSON e restituisce una struttura organizzata per campionato e giornata.

    Ritorna:
        list di dict con campi:
            - campionato: nome campionato
            - girone: nome girone
            - comitato: nome comitato
            - giornata: nome giornata (es. "Giornata 16")
            - data: data partita
            - ora: orario
            - squadra_casa: nome squadra casa
            - squadra_ospite: nome squadra ospite
            - set_casa: set vinti casa
            - set_ospite: set vinti ospite
            - parziali_casa: punti per set casa
            - parziali_ospite: punti per set ospite
            - palazzetto: nome struttura
            - arbitro_1: primo arbitro
            - arbitro_2: secondo arbitro
            - giocata: se la partita è stata giocata
            - numero_gara: numero gara
            - live: se la partita è in live
    """
    if not data:
        return []

    championships = data.get("data", {}).get("championship", [])
    risultati = []

    for champ in championships:
        campionato = champ.get("title", "N/D")
        girone = champ.get("sub-title", "N/D")
        comitato = champ.get("commettee", "N/D")
        comitato_id = champ.get("commettee-id", "")
        girone_id = champ.get("id", "")

        matches = champ.get("championship-matches", [])
        for match in matches:
            team1 = match.get("team1", {})
            team2 = match.get("team2", {})

            risultati.append({
                "campionato": campionato,
                "girone": girone,
                "comitato": comitato,
                "comitato_id": comitato_id,
                "girone_id": girone_id,
                "giornata": match.get("day", "N/D"),
                "data": match.get("date", "N/D"),
                "ora": match.get("time", "N/D"),
                "squadra_casa": team1.get("title", "N/D"),
                "squadra_ospite": team2.get("title", "N/D"),
                "set_casa": match.get("team1-setwin", ""),
                "set_ospite": match.get("team2-setwin", ""),
                "parziali_casa": match.get("pt_a", []),
                "parziali_ospite": match.get("pt_b", []),
                "palazzetto": match.get("stadium", "N/D"),
                "arbitro_1": match.get("1referee", ""),
                "arbitro_2": match.get("2referee", ""),
                "giocata": match.get("played", False),
                "numero_gara": match.get("ng", ""),
                "live": match.get("is_live", "0") == "1",
                "match_id": match.get("id", ""),
            })

    return risultati


def stampa_campionati(risultati):
    """Stampa i risultati raggruppati per campionato e giornata."""
    if not risultati:
        print("Nessun dato disponibile.")
        return

    # Raggruppa per campionato+girone
    per_campionato = defaultdict(lambda: defaultdict(list))
    for r in risultati:
        chiave_camp = f"{r['campionato']} - {r['girone']}"
        per_campionato[chiave_camp][r["giornata"]].append(r)

    for campionato, giornate in sorted(per_campionato.items()):
        print(f"\n{'='*80}")
        print(f"  {campionato}")
        print(f"  Comitato: {risultati[0]['comitato']}")
        print(f"{'='*80}")

        for giornata, partite in sorted(giornate.items(), key=lambda x: _sort_giornata(x[0])):
            print(f"\n  --- {giornata} ---")
            for p in sorted(partite, key=lambda x: (x["data"], x["ora"])):
                stato = ""
                if p["live"]:
                    stato = " [LIVE]"
                elif p["giocata"]:
                    parziali_a = "-".join(str(x) for x in p["parziali_casa"]) if p["parziali_casa"] else ""
                    parziali_b = "-".join(str(x) for x in p["parziali_ospite"]) if p["parziali_ospite"] else ""
                    stato = f"  {p['set_casa']}-{p['set_ospite']}  ({parziali_a} / {parziali_b})"
                else:
                    stato = "  [da giocare]"

                print(f"    {p['data']} {p['ora']}  {p['squadra_casa']:30s} vs {p['squadra_ospite']:30s}{stato}")
                if p["palazzetto"] and p["palazzetto"] != "N/D":
                    print(f"{'':36s}  @ {p['palazzetto']}")


def _sort_giornata(g):
    """Ordina le giornate numericamente."""
    import re
    m = re.search(r"(\d+)", g)
    return int(m.group(1)) if m else 0


def esporta_csv(risultati, filename):
    """Esporta i risultati in formato CSV."""
    import csv

    if not risultati:
        print("Nessun dato da esportare.")
        return

    campi = [
        "campionato", "girone", "comitato", "giornata", "data", "ora",
        "squadra_casa", "squadra_ospite", "set_casa", "set_ospite",
        "parziali_casa", "parziali_ospite", "palazzetto",
        "arbitro_1", "arbitro_2", "giocata", "numero_gara", "live",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campi, extrasaction="ignore")
        writer.writeheader()
        for r in risultati:
            row = dict(r)
            row["parziali_casa"] = "-".join(str(x) for x in row["parziali_casa"])
            row["parziali_ospite"] = "-".join(str(x) for x in row["parziali_ospite"])
            writer.writerow(row)

    print(f"\nEsportato in: {filename} ({len(risultati)} partite)")


def esporta_json(risultati, filename):
    """Esporta i risultati in formato JSON organizzato."""
    if not risultati:
        print("Nessun dato da esportare.")
        return

    # Organizza per campionato > giornata
    output = {}
    for r in risultati:
        chiave = f"{r['campionato']} - {r['girone']}"
        if chiave not in output:
            output[chiave] = {
                "campionato": r["campionato"],
                "girone": r["girone"],
                "comitato": r["comitato"],
                "giornate": {},
            }
        giornata = r["giornata"]
        if giornata not in output[chiave]["giornate"]:
            output[chiave]["giornate"][giornata] = []
        output[chiave]["giornate"][giornata].append({
            "data": r["data"],
            "ora": r["ora"],
            "squadra_casa": r["squadra_casa"],
            "squadra_ospite": r["squadra_ospite"],
            "set_casa": r["set_casa"],
            "set_ospite": r["set_ospite"],
            "parziali_casa": r["parziali_casa"],
            "parziali_ospite": r["parziali_ospite"],
            "palazzetto": r["palazzetto"],
            "arbitro_1": r["arbitro_1"],
            "arbitro_2": r["arbitro_2"],
            "giocata": r["giocata"],
            "numero_gara": r["numero_gara"],
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nEsportato in: {filename} ({len(risultati)} partite)")


def _extract_comitati_list(data):
    """Estrae la lista piatta di (id, nome) dai dati comitati."""
    comitati_ids = []
    regioni = data.get("regioni", data)
    for regione_nome, regione_data in regioni.items():
        if isinstance(regione_data, dict):
            for c in regione_data.get("comitati", []):
                comitati_ids.append((c["id"], c["nome"], regione_nome))
        elif isinstance(regione_data, list):
            for c in regione_data:
                if isinstance(c, dict) and "id" in c:
                    comitati_ids.append((c["id"], c["nome"], regione_nome))
    return comitati_ids


def lista_comitati(session):
    """Mostra la lista dei comitati disponibili."""
    data = fetch_comitati(session)
    comitati = _extract_comitati_list(data)

    print("\n=== COMITATI REGIONALI FIPAV ===\n")
    regione_corrente = ""
    for com_id, com_nome, regione in sorted(comitati, key=lambda x: (x[2], x[0])):
        if regione != regione_corrente:
            regione_corrente = regione
            print(f"\n  {regione}:")
        print(f"    {com_id:>8s}  {com_nome}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="FIPAV Scraper - Estrai dati campionati pallavolo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python fipav_scraper.py                         # Lista comitati
  python fipav_scraper.py --comitato 03000        # Dati comitato Liguria
  python fipav_scraper.py --comitato 03000 --csv  # Esporta in CSV
  python fipav_scraper.py --comitato 03000 --json # Esporta in JSON
  python fipav_scraper.py --tutti --csv           # Tutti i comitati in CSV
        """,
    )
    parser.add_argument(
        "--comitato", "-c",
        help="ID del comitato (es. 03000 per Liguria). Usa senza argomenti per vedere la lista.",
    )
    parser.add_argument(
        "--tutti", "-t",
        action="store_true",
        help="Scarica dati di tutti i comitati",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Esporta risultati in CSV",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Esporta risultati in JSON",
    )
    parser.add_argument(
        "--output", "-o",
        help="Nome file di output (default: fipav_risultati.csv/.json)",
    )

    args = parser.parse_args()
    session = get_session()

    # Se nessun comitato specificato, mostra la lista
    if not args.comitato and not args.tutti:
        lista_comitati(session)
        print("Usa --comitato ID per scaricare i dati di un comitato specifico.")
        print("Usa --tutti per scaricare tutti i comitati.")
        return

    # Raccogli i comitati da processare
    comitati_ids = []
    if args.tutti:
        data = fetch_comitati(session)
        for com_id, com_nome, _ in _extract_comitati_list(data):
            comitati_ids.append((com_id, com_nome))
    else:
        comitati_ids = [(args.comitato, args.comitato)]

    # Scarica e processa
    tutti_risultati = []
    for com_id, com_nome in comitati_ids:
        print(f"\n>>> Scaricamento dati: {com_nome} ({com_id})...")
        data = fetch_campionati(session, com_id)
        if data:
            risultati = parse_campionati(data)
            tutti_risultati.extend(risultati)
            print(f"    Trovati {len(risultati)} partite")
            if not args.csv and not args.json:
                stampa_campionati(risultati)

    # Esporta se richiesto
    if args.csv:
        filename = args.output or "fipav_risultati.csv"
        esporta_csv(tutti_risultati, filename)
    elif args.json:
        filename = args.output or "fipav_risultati.json"
        esporta_json(tutti_risultati, filename)

    if tutti_risultati:
        # Riepilogo
        campionati_unici = set(f"{r['campionato']} - {r['girone']}" for r in tutti_risultati)
        giornate_uniche = set(r["giornata"] for r in tutti_risultati)
        print(f"\n--- Riepilogo ---")
        print(f"Campionati: {len(campionati_unici)}")
        print(f"Giornate:   {len(giornate_uniche)}")
        print(f"Partite:    {len(tutti_risultati)}")


if __name__ == "__main__":
    main()
