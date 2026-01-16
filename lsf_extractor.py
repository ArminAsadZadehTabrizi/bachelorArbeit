"""
LSF HTML Extractor - Prototyp für Datenstruktur-Analyse

Extrahiert strukturierte Daten aus LSF-Detailansichten für universitäre Veranstaltungen.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup


def parse_detail_page(html_content: str) -> Dict[str, Any]:
    """
    Extrahiert strukturierte Daten aus einer LSF-Detailseite.
    
    Args:
        html_content: HTML-Inhalt der Detailseite
        
    Returns:
        Dictionary mit extrahierten Datenfeldern
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {
        'titel': None,
        'veranstaltungsart': None,
        'veranstaltungs_id': None,
        'semester': None,
        'ects_ohne_pruefung': None,
        'ects_mit_pruefung': None,
        'sprache': None,
        'hyperlinks': [],
        'personen': [],
        'termine': [],
        'studiengaenge': [],
        'module': [],
        'einrichtungen': []
    }
    
    # 1. Titel und Veranstaltungsart aus h1
    h1 = soup.find('h1')
    if h1:
        h1_text = h1.get_text(strip=True)
        # Entferne " - Einzelansicht" am Ende
        result['titel'] = h1_text.replace(' - Einzelansicht', '').strip()
    
    # 2. Grunddaten-Tabelle
    basicdata_table = soup.find('a', {'name': 'basicdata'})
    if basicdata_table:
        basicdata_table = basicdata_table.find_next('table', {'summary': 'Grunddaten zur Veranstaltung'})
        if basicdata_table:
            # Veranstaltungsart
            art_th = basicdata_table.find('th', {'id': 'basic_1'})
            if art_th:
                art_td = basicdata_table.find('td', {'headers': 'basic_1'})
                if art_td:
                    result['veranstaltungsart'] = art_td.get_text(strip=True)
            
            # VeranstaltungsID
            id_th = basicdata_table.find('th', {'id': 'basic_3'})
            if id_th:
                id_td = basicdata_table.find('td', {'headers': 'basic_3'})
                if id_td:
                    result['veranstaltungs_id'] = id_td.get_text(strip=True)
            
            # Semester
            sem_th = basicdata_table.find('th', {'id': 'basic_5'})
            if sem_th:
                sem_td = basicdata_table.find('td', {'headers': 'basic_5'})
                if sem_td:
                    result['semester'] = sem_td.get_text(strip=True)
            
            # ECTS-Felder: Beide haben id="basic_11" und sind in derselben Zeile
            # Struktur: <tr><th>ECTS ohne</th><td></td><th>ECTS mit</th><td></td></tr>
            for row in basicdata_table.find_all('tr'):
                # Prüfe ob diese Zeile ECTS-Felder enthält
                row_text = row.get_text()
                if 'ECTS ohne Prüfung' in row_text or 'ECTS mit Prüfung' in row_text:
                    # Finde alle Elemente in dieser Zeile in Reihenfolge
                    elements = row.find_all(['th', 'td'], recursive=False)
                    
                    # Durchlaufe Elemente und finde ECTS-Felder
                    for i, elem in enumerate(elements):
                        if elem.name == 'th' and 'ECTS ohne Prüfung' in elem.get_text():
                            # Nächstes TD nach diesem TH
                            if i + 1 < len(elements) and elements[i + 1].name == 'td':
                                text = elements[i + 1].get_text(strip=True)
                                result['ects_ohne_pruefung'] = text if text else None
                        
                        if elem.name == 'th' and 'ECTS mit Prüfung' in elem.get_text():
                            # Nächstes TD nach diesem TH
                            if i + 1 < len(elements) and elements[i + 1].name == 'td':
                                text = elements[i + 1].get_text(strip=True)
                                result['ects_mit_pruefung'] = text if text else None
                    
                    # Wenn beide gefunden, weiter zur nächsten Zeile
                    if result['ects_ohne_pruefung'] is not None or result['ects_mit_pruefung'] is not None:
                        break
            
            # Sprache
            sprache_th = basicdata_table.find('th', {'id': 'basic_16'})
            if sprache_th:
                sprache_td = basicdata_table.find('td', {'headers': 'basic_16'})
                if sprache_td:
                    result['sprache'] = sprache_td.get_text(strip=True)
            
            # Hyperlink 
            hyperlink_th = basicdata_table.find('th', {'id': 'basic_13'})
            if hyperlink_th:
                hyperlink_td = basicdata_table.find('td', {'headers': 'basic_13'})
                if hyperlink_td:
                    link = hyperlink_td.find('a', class_='regular')
                    if link and link.get('href'):
                        href = link.get('href')
                        # Nur externe Links (nicht LSF-interne)
                        if href and not href.startswith('/qisserver') and 'lsf.hhu.de' not in href:
                            result['hyperlinks'].append({
                                'url': href,
                                'text': link.get_text(strip=True),
                                'type': 'hauptlink'
                            })
            
            # Weitere Links
            weitere_links_th = basicdata_table.find('th', {'id': 'basic_15'})
            if weitere_links_th:
                # Kann mehrere Zeilen haben
                weitere_links_tds = basicdata_table.find_all('td', {'headers': 'basic_15'})
                for td in weitere_links_tds:
                    links = td.find_all('a', class_='regular')
                    for link in links:
                        href = link.get('href')
                        if href:
                            # Externe Links erkennen (enthält "redirect" oder externe Domains)
                            if 'redirect' in href or 'http' in href:
                                # URL aus redirect-Parameter extrahieren
                                if 'destination=' in href:
                                    match = re.search(r'destination=([^&]+)', href)
                                    if match:
                                        import urllib.parse
                                        decoded = urllib.parse.unquote(match.group(1))
                                        result['hyperlinks'].append({
                                            'url': decoded,
                                            'text': link.get_text(strip=True),
                                            'type': 'weiterer_link'
                                        })
                                else:
                                    result['hyperlinks'].append({
                                        'url': href,
                                        'text': link.get_text(strip=True),
                                        'type': 'weiterer_link'
                                    })
    
    # 3. Termine-Tabelle
    terms_anchor = soup.find('a', {'name': 'terms'})
    if terms_anchor:
        terms_table = terms_anchor.find_next('table', {'summary': 'Übersicht über alle Veranstaltungstermine'})
        if terms_table:
            rows = terms_table.find_all('tr')[1:]  
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 5:
                    termin = {
                        'tag': cells[0].get_text(strip=True) if len(cells) > 0 else None,
                        'zeit': cells[1].get_text(strip=True) if len(cells) > 1 else None,
                        'rhythmus': cells[2].get_text(strip=True) if len(cells) > 2 else None,
                        'dauer': cells[3].get_text(strip=True) if len(cells) > 3 else None,
                        'raum': None,
                        'lehrperson': None,
                        'status': None,
                        'bemerkung': None
                    }
                    
                    # Raum (kann Link sein)
                    if len(cells) > 4:
                        raum_cell = cells[4]
                        raum_link = raum_cell.find('a')
                        if raum_link:
                            termin['raum'] = raum_link.get_text(strip=True)
                        else:
                            termin['raum'] = raum_cell.get_text(strip=True)
                    
                    # Lehrperson
                    if len(cells) > 6:
                        termin['lehrperson'] = cells[6].get_text(strip=True)
                    
                    # Status
                    if len(cells) > 7:
                        termin['status'] = cells[7].get_text(strip=True)
                    
                    # Bemerkung
                    if len(cells) > 8:
                        termin['bemerkung'] = cells[8].get_text(strip=True)
                    
                    result['termine'].append(termin)
    
    # 4. Personen-Tabelle
    persons_anchor = soup.find('a', {'name': 'persons'})
    if persons_anchor:
        persons_table = persons_anchor.find_next('table', {'summary': 'Verantwortliche Dozenten'})
        if persons_table:
            rows = persons_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    person_link = cells[0].find('a', class_='regular')
                    person_name = person_link.get_text(strip=True) if person_link else cells[0].get_text(strip=True)
                    zustaendigkeit = cells[1].get_text(strip=True) if len(cells) > 1 else None
                    
                    result['personen'].append({
                        'name': person_name,
                        'zustaendigkeit': zustaendigkeit
                    })
    
    # 5. Studiengänge-Tabelle
    curricular_anchor = soup.find('a', {'name': 'curricular'})
    if curricular_anchor:
        # Es kann mehrere Tabellen mit name="curricular" geben (Studiengänge, Module)
        # Suche spezifisch nach Studiengänge-Tabelle
        tables = soup.find_all('table', {'summary': 'Übersicht über die zugehörigen Studiengänge'})
        if tables:
            stg_table = tables[0]
            rows = stg_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    stg_link = cells[1].find('a', class_='regular')
                    stg_name = stg_link.get_text(strip=True) if stg_link else cells[1].get_text(strip=True)
                    
                    result['studiengaenge'].append({
                        'abschluss': cells[0].get_text(strip=True) if len(cells) > 0 else None,
                        'studiengang': stg_name,
                        'semester': cells[2].get_text(strip=True) if len(cells) > 2 else None,
                        'po_version': cells[3].get_text(strip=True) if len(cells) > 3 else None
                    })
        
        # Module-Tabelle
        module_tables = soup.find_all('table', {'summary': 'Übersicht über die zugehörigen Module'})
        if module_tables:
            module_table = module_tables[0]
            rows = module_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    module_text = cells[0].get_text(strip=True)
                    if module_text:
                        result['module'].append(module_text)
    
    # 6. Einrichtungen-Tabelle
    institutions_anchor = soup.find('a', {'name': 'institutions'})
    if institutions_anchor:
        institutions_table = institutions_anchor.find_next('table', {'summary': 'Übersicht über die zugehörigen Einrichtungen'})
        if institutions_table:
            rows = institutions_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    einrichtung_link = cells[0].find('a', class_='regular')
                    einrichtung_name = einrichtung_link.get_text(strip=True) if einrichtung_link else cells[0].get_text(strip=True)
                    if einrichtung_name:
                        result['einrichtungen'].append(einrichtung_name)
    
    return result


def main():
    """Hauptfunktion: Liest alle Detail-Dateien ein und gibt JSON aus."""
    base_path = Path(__file__).parent
    
    # Liste der Detail-Dateien (ohne Veranstaltungsverzeichnis)
    detail_files = [
        '- Vorlesung Präsenz: Algorithmen und Datenstrukturen Heinrich Heine Universität Düsseldorf.html',
        '- Vorlesung (Hybrid Plus: Präsenz + Streaming + Aufzeichnung): Programmierung Heinrich Heine Univers.html',
        '- Vorlesung (Hybrid Plus: Präsenz + Streaming + Aufzeichnung): Rechnerarchitektur Heinrich Heine Uni.html',
        '- Übung: Programmierung (Übung) Heinrich Heine Universität Düsseldorf.html'
    ]
    
    results = {}
    
    for filename in detail_files:
        filepath = base_path / filename
        if filepath.exists():
            print(f"Verarbeite: {filename}", file=__import__('sys').stderr)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                extracted_data = parse_detail_page(html_content)
                results[filename] = extracted_data
            except Exception as e:
                print(f"Fehler beim Verarbeiten von {filename}: {e}", file=__import__('sys').stderr)
                results[filename] = {'error': str(e)}
        else:
            print(f"Datei nicht gefunden: {filename}", file=__import__('sys').stderr)
            results[filename] = {'error': 'Datei nicht gefunden'}
    
    # JSON-Ausgabe
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

