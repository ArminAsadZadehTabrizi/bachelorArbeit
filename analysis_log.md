# LSF HTML-Struktur Analyse - Methodik-Dokumentation

## 1. HTML-Struktur: Datenkapselung

### 1.1 Übersichtliche Struktur

Die LSF-Detailansichten verwenden eine **tabellenbasierte Struktur** mit semantischen HTML-Elementen. Die Daten sind in klar abgegrenzten Abschnitten organisiert, die über Anchor-Links (`<a name="...">`) navigierbar sind.

### 1.2 Grunddaten-Tabelle

**Lokalisierung:**
- Anchor: `<a name="basicdata"></a>`
- Tabelle: `<table summary="Grunddaten zur Veranstaltung">`

**Struktur:**
- Verwendet `headers`-Attribut für Accessibility (WCAG-konform)
- Jede Zeile enthält zwei Spalten (Key-Value-Paare)
- IDs folgen Schema: `basic_1`, `basic_3`, `basic_5`, etc.

**Wichtige Felder:**
- `basic_1`: Veranstaltungsart (z.B. "Vorlesung Präsenz", "Übung")
- `basic_3`: VeranstaltungsID (numerisch)
- `basic_5`: Semester (z.B. "WiSe 2025/26")
- `basic_11`: ECTS-Felder (mehrfach verwendet für "ohne Prüfung" und "mit Prüfung")
- `basic_13`: Hyperlink (Hauptlink)
- `basic_15`: Weitere Links (kann `rowspan` haben für mehrere Links)
- `basic_16`: Sprache

**Selektor-Strategie:**
```python
# Robust: Suche nach ID, dann nach headers-Attribut
art_th = table.find('th', {'id': 'basic_1'})
art_td = table.find('td', {'headers': 'basic_1'})
```

### 1.3 Termine-Tabelle

**Lokalisierung:**
- Anchor: `<a name="terms"></a>`
- Tabelle: `<table summary="Übersicht über alle Veranstaltungstermine">`

**Struktur:**
- Header-Zeile mit Spalten: Tag, Zeit, Rhythmus, Dauer, Raum, Raumplan, Lehrperson, Status, Bemerkung, fällt aus am, Max. Teilnehmer
- Datenzeilen mit alternierenden Klassen: `mod_n_odd` / `mod_n_even`
- Raum kann als Link (`<a>`) oder als Text vorliegen

**Besonderheiten:**
- Dauer kann verschiedene Formate haben:
  - Datumsbereich: "14.10.2025 bis 03.02.2026"
  - Einzeltermin: "am 14.11.2025"
- Rhythmus: "woch" (wöchentlich), "Einzel" (Einzeltermin)
- Bemerkung kann leer sein oder spezielle Hinweise enthalten

**Selektor-Strategie:**
```python
# Überspringe Header-Zeile
rows = table.find_all('tr')[1:]
# Extrahiere Zellen nach Index (robust gegen leere Zellen)
```

### 1.4 Personen-Tabelle

**Lokalisierung:**
- Anchor: `<a name="persons"></a>`
- Tabelle: `<table summary="Verantwortliche Dozenten">`

**Struktur:**
- Zwei Spalten: Name (mit Link), Zuständigkeit
- Zuständigkeiten: "verantwort", "begleitend"

**Selektor-Strategie:**
```python
# Name kann in Link oder direkt im TD stehen
person_link = cells[0].find('a', class_='regular')
person_name = person_link.get_text() if person_link else cells[0].get_text()
```

### 1.5 Studiengänge-Tabelle

**Lokalisierung:**
- Anchor: `<a name="curricular"></a>` (mehrfach vorhanden!)
- Tabelle: `<table summary="Übersicht über die zugehörigen Studiengänge">`

**Struktur:**
- Spalten: Abschluss, Studiengang (mit Link), Semester, PO-Version
- Studiengang-Name enthält oft PO-Version im Text: "Informatik (BSc, PO 2021)"

**Wichtig für Graph-Relationen:**
Diese Tabelle ist **kritisch** für die Kanten im Wissensgraphen, da sie die Zuordnung von Veranstaltungen zu Studiengängen zeigt.

**Selektor-Strategie:**
```python
# Suche spezifisch nach summary-Attribut, da mehrere Tabellen mit name="curricular" existieren
tables = soup.find_all('table', {'summary': 'Übersicht über die zugehörigen Studiengänge'})
```

### 1.6 Module-Tabelle

**Lokalisierung:**
- Gleicher Anchor wie Studiengänge: `<a name="curricular"></a>`
- Tabelle: `<table summary="Übersicht über die zugehörigen Module">`

**Struktur:**
- Einfache Tabelle mit einer Spalte "Modul"
- Kann leer sein (keine Module zugeordnet)

### 1.7 Einrichtungen-Tabelle

**Lokalisierung:**
- Anchor: `<a name="institutions"></a>`
- Tabelle: `<table summary="Übersicht über die zugehörigen Einrichtungen">`

**Struktur:**
- Einfache Liste von Einrichtungen (meist eine pro Veranstaltung)

## 2. Daten-Anomalien

### 2.1 ECTS-Daten: Unsaubere Formate

**Beobachtete Varianten:**

1. **Einfache Zahl:**
   - `"10"`

2. **Zahl mit Text:**
   - `"10 ECTS für Vorlesung und Übung"`

3. **Bedingte Angaben:**
   - `"7 ECTS ab PO 2021, 9 ECTS in PO 2016 (zusammen mit Hardwarenaher Programmierung)"`

4. **Leer:**
   - `""` oder nur Whitespace

**Konsequenz für Extraktion:**
- **Rohdaten extrahieren** (wie implementiert)
- Keine Parsing-Logik in Phase 1
- Spätere Phase: Regex-basierte Extraktion von Zahlen mit Kontext

### 2.2 Termine: Inkonsistente Formate

**Dauer-Formate:**
- `"14.10.2025 bis 03.02.2026"` (Bereich)
- `"am 14.11.2025"` (Einzeltermin)
- Leer bei wöchentlichen Terminen ohne explizite Dauer

**Raum-Formate:**
- Als Link: `<a>0-Hörsaal - 2511.HS 5C</a>`
- Als Text: `"&nbsp;"` (leer)
- Online-Termine: `"&nbsp;"` (kein Raum)

**Status/Bemerkung:**
- Kann spezielle Hinweise enthalten: "Vorlesung (4 SWS)", "Übungstest 1"
- Bemerkung kann sehr lang sein mit HTML-Formatierung

### 2.3 Hyperlinks: Verschiedene Formate

**Hauptlink (`basic_13`):**
- Meist leer (`&nbsp;`)

**Weitere Links (`basic_15`):**
- LSF-interne Redirects: `state=redirect&destination=...`
- URL ist URL-encoded im `destination`-Parameter
- Externe Links: ILIAS, Moodle, Lehrstuhlseiten

**Selektor-Strategie:**
```python
# Erkenne externe Links durch:
# 1. "redirect" im href
# 2. "destination=" Parameter
# 3. URL-Decoding notwendig
```

### 2.4 Personen: Variierende Formate

**Name-Formate:**
- Mit Titel: "Univ.-Prof. Dr. Klau, Gunnar"
- Ohne Titel: "Hillebrand, Johanna"
- Mit Komma: "Klau, Gunnar"
- Ohne Komma: "Brenneis, Markus"

**Zuständigkeit:**
- Immer vorhanden: "verantwort" oder "begleitend"

## 3. Selektoren-Strategie: Begründung

### 3.1 Warum `headers`-Attribut statt CSS-Klassen?

**Vorteile:**
- **Semantisch korrekt**: HTML5-Standard für Accessibility
- **Robust**: IDs ändern sich seltener als CSS-Klassen
- **Präzise**: Eindeutige Zuordnung zwischen `<th>` und `<td>`

**Nachteil:**
- Erfordert zwei Schritte: Erst `<th>` finden, dann `<td>` mit passendem `headers`

**Alternative (nicht verwendet):**
- CSS-Klassen wie `mod_n_basic` sind zu generisch (werden mehrfach verwendet)

### 3.2 Warum `summary`-Attribut für Tabellen?

**Vorteile:**
- **Eindeutig**: Jede Tabelle hat eindeutigen `summary`-Text
- **Semantisch**: Accessibility-Standard
- **Robust**: Weniger anfällig für Layout-Änderungen

**Beispiel:**
```python
# Robust gegen mehrere Tabellen mit gleichem Anchor
table = soup.find('table', {'summary': 'Übersicht über die zugehörigen Studiengänge'})
```

### 3.3 Warum Index-basierte Zellenextraktion bei Terminen?

**Vorteile:**
- **Einfach**: Direkter Zugriff auf Spalten
- **Schnell**: Keine komplexen Selektoren nötig

**Nachteil:**
- **Fragil**: Bricht bei Spaltenänderungen

**Alternative (nicht verwendet):**
- Header-basierte Zuordnung wäre robuster, aber komplexer

### 3.4 Warum `find_next()` statt direkter Suche?

**Vorteile:**
- **Kontext-bewusst**: Findet Tabelle direkt nach Anchor
- **Robust**: Funktioniert auch wenn dazwischen andere Elemente sind

**Beispiel:**
```python
anchor = soup.find('a', {'name': 'basicdata'})
table = anchor.find_next('table', {'summary': 'Grunddaten zur Veranstaltung'})
```

### 3.5 Fehlerbehandlung: None vs. Leere Listen

**Strategie:**
- **None** für einzelne Werte (z.B. `titel`, `sprache`)
- **Leere Listen** für Collections (z.B. `termine`, `personen`)

**Begründung:**
- Unterscheidung zwischen "nicht gefunden" (None) und "leer" ([])
- Erleichtert spätere Validierung

## 4. Bekannte Limitationen

### 4.1 ECTS-Parsing

- **Aktuell**: Nur Rohdaten-Extraktion
- **Zukünftig**: Regex-basierte Extraktion von Zahlen mit Kontext-Erkennung

### 4.2 Termine-Parsing

- **Aktuell**: Dauer als String
- **Zukünftig**: Datumsparsing für Bereiche und Einzeltermine

### 4.3 Hyperlink-Extraktion

- **Aktuell**: Basis-Implementierung für externe Links
- **Zukünftig**: Vollständige URL-Decodierung und Kategorisierung (ILIAS, Moodle, etc.)

### 4.4 Personen-Namen

- **Aktuell**: Rohdaten mit Titel
- **Zukünftig**: Parsing in Vor-/Nachname, Titel-Extraktion

## 5. Graph-Relationen: Studiengänge

Die **Studiengänge-Tabelle** ist der Schlüssel für Graph-Kanten:

```
Veranstaltung --[gehört_zu]--> Studiengang
```

**Extrahiert:**
- Studiengang-Name (mit PO-Version)
- Abschluss (Bachelor, Master, etc.)
- PO-Version (für Versionierung im Graph)

**Verwendung:**
- Jeder Studiengang wird zu einem Knoten im Graph
- Jede Veranstaltung erhält Kanten zu allen zugehörigen Studiengängen

## 6. Nächste Schritte (Phase 2)

1. **Datenbereinigung:**
   - ECTS-Parsing mit Regex
   - Datumsparsing für Termine
   - Personen-Namen-Normalisierung

2. **Validierung:**
   - Pflichtfelder prüfen
   - Datenkonsistenz-Checks

3. **Graph-Modellierung:**
   - Entity-Identifikation (Veranstaltungen, Personen, Studiengänge)
   - Relation-Typen definieren
   - Property-Mapping


