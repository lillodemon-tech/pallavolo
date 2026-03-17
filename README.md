# FIPAV Scraper

Script Python per estrarre i dati dei campionati di pallavolo dal sito [fipavonline.it](https://www.fipavonline.it/live/index.html), organizzati per campionato e giornata.

## Requisiti

- Python 3.7+
- Libreria `requests`
- (Opzionale) `pycryptodome` per decifrare dati crittografati

## Installazione

```bash
pip install requests
```

Per il supporto alla decifrazione (fallback se il JSON diretto non e' disponibile):

```bash
pip install pycryptodome
```

## Utilizzo

### Vedere la lista dei comitati disponibili

```bash
python3 fipav_scraper.py
```

Output di esempio:

```
=== COMITATI REGIONALI FIPAV ===

  Liguria:
     03000  COMITATO REGIONALE LIGURIA
     03008  COMITATO TERRITORIALE LIGURIA CENTRO
     03011  COMITATO TERRITORIALE LIGURIA PONENTE
     03104  COMITATO TERRITORIALE LIGURIA LEVANTE

  Lazio:
     12000  COMITATO REGIONALE LAZIO
     12057  COMITATO TERRITORIALE FROSINONE
     ...
```

### Scaricare i dati di un comitato (visualizzazione a schermo)

```bash
python3 fipav_scraper.py --comitato 03000
```

oppure con la forma abbreviata:

```bash
python3 fipav_scraper.py -c 03000
```

### Esportare in CSV

```bash
python3 fipav_scraper.py --comitato 03000 --csv
```

Genera il file `fipav_risultati.csv`. Per specificare un nome diverso:

```bash
python3 fipav_scraper.py --comitato 03000 --csv --output risultati_liguria.csv
```

### Esportare in JSON

```bash
python3 fipav_scraper.py --comitato 03000 --json
```

Genera il file `fipav_risultati.json`, strutturato per campionato e giornata.

### Scaricare tutti i comitati

```bash
python3 fipav_scraper.py --tutti --csv
```

## Opzioni

| Opzione | Abbreviazione | Descrizione |
|---|---|---|
| `--comitato ID` | `-c ID` | ID del comitato da scaricare |
| `--tutti` | `-t` | Scarica i dati di tutti i comitati |
| `--csv` | | Esporta i risultati in formato CSV |
| `--json` | `-j` | Esporta i risultati in formato JSON |
| `--output NOME` | `-o NOME` | Nome del file di output |

## Dati estratti

Per ogni partita vengono estratti i seguenti campi:

| Campo | Descrizione |
|---|---|
| campionato | Nome del campionato (es. "Serie C Regionale Maschile") |
| girone | Nome del girone (es. "Girone Unico", "Girone A") |
| comitato | Nome del comitato regionale/territoriale |
| giornata | Numero della giornata (es. "Giornata 16") |
| data | Data della partita (gg/mm/aaaa) |
| ora | Orario di inizio |
| squadra_casa | Nome squadra di casa |
| squadra_ospite | Nome squadra ospite |
| set_casa | Set vinti dalla squadra di casa |
| set_ospite | Set vinti dalla squadra ospite |
| parziali_casa | Punti per set della squadra di casa |
| parziali_ospite | Punti per set della squadra ospite |
| palazzetto | Nome e indirizzo della struttura |
| arbitro_1 | Primo arbitro |
| arbitro_2 | Secondo arbitro |
| giocata | Se la partita e' stata giocata (True/False) |
| numero_gara | Numero identificativo della gara |
| live | Se la partita e' attualmente in corso (True/False) |

## Esempi pratici

Visualizzare a schermo i campionati del Lazio:

```bash
python3 fipav_scraper.py -c 12000
```

Esportare tutte le partite della Sardegna in CSV:

```bash
python3 fipav_scraper.py -c 19000 --csv -o sardegna.csv
```

Esportare tutti i comitati in un unico file JSON:

```bash
python3 fipav_scraper.py --tutti --json -o tutti_campionati.json
```
