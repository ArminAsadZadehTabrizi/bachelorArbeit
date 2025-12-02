# LSF HTML Extractor

Projekt zur Extraktion strukturierter Daten aus LSF-Detailansichten für universitäre Veranstaltungen.

## Beschreibung

Dieses Projekt analysiert HTML-Strukturen von LSF-Detailseiten der Heinrich Heine Universität Düsseldorf und extrahiert strukturierte Daten im JSON-Format.

## Dateien

- `lsf_extractor.py` - Hauptskript für die Datenextraktion
- `analysis_log.md` - Dokumentation der HTML-Struktur-Analyse
- HTML-Dateien - Beispiel-Detailansichten von Veranstaltungen

## Verwendung

```bash
python3 lsf_extractor.py
```

Das Skript liest die HTML-Dateien ein und gibt die extrahierten Daten als JSON aus.

## Abhängigkeiten

- Python 3
- BeautifulSoup4 (`beautifulsoup4`)
- Pathlib (Standardbibliothek)

## Installation

```bash
pip install beautifulsoup4
```

