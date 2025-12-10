#!/usr/bin/env python3
"""
Website HTML Extractor - Extrahiert unstrukturierte Informationen von Universitäts-Websites

Extrahiert Informationen basierend auf Keywords wie "Klausur", "Sprechstunde", "Skript", etc.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


# Keywords für die Suche
KEYWORDS = {
    'klausur': ['klausur', 'prüfung', 'exam', 'examination', 'test', 'prüfungstermin'],
    'sprechstunde': ['sprechstunde', 'office hours', 'consultation', 'sprechzeit'],
    'skript': ['skript', 'script', 'vorlesungsunterlagen', 'lecture notes', 'materialien', 'unterlagen'],
    'vorlesung': ['vorlesung', 'lecture', 'veranstaltung', 'course'],
    'übung': ['übung', 'exercise', 'tutorial', 'tutorium'],
    'seminar': ['seminar', 'workshop'],
    'praktikum': ['praktikum', 'practical', 'lab'],
    'ects': ['ects', 'credit points', 'leistungspunkte'],
    'modul': ['modul', 'module'],
    'dozent': ['dozent', 'professor', 'prof.', 'lecturer', 'instructor'],
    'raum': ['raum', 'room', 'gebäude', 'building'],
    'termin': ['termin', 'appointment', 'termine', 'schedule']
}


def extract_keyword_contexts(text: str, keyword: str, context_chars: int = 200) -> List[Dict[str, str]]:
    """
    Findet alle Vorkommen eines Keywords im Text und extrahiert Kontext.
    
    Args:
        text: Der zu durchsuchende Text
        keyword: Das zu suchende Keyword
        context_chars: Anzahl der Zeichen vor und nach dem Keyword
        
    Returns:
        Liste von Dictionaries mit Keyword, Kontext und Position
    """
    contexts = []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        context = text[start:end].strip()
        
        contexts.append({
            'keyword': keyword,
            'context': context,
            'position': match.start()
        })
    
    return contexts


def extract_structured_info(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    Extrahiert strukturierte Informationen aus einer HTML-Seite.
    
    Args:
        soup: BeautifulSoup-Objekt der HTML-Seite
        url: URL der Seite
        
    Returns:
        Dictionary mit extrahierten Informationen
    """
    result = {
        'source_url': url,
        'title': None,
        'department': None,
        'professor': None,
        'contact_info': {},
        'keywords_found': {},
        'links': [],
        'text_blocks': []
    }
    
    # Titel extrahieren
    title_tag = soup.find('title')
    if title_tag:
        result['title'] = title_tag.get_text(strip=True)
    
    # H1 als möglicher Titel
    h1 = soup.find('h1')
    if h1 and not result['title']:
        result['title'] = h1.get_text(strip=True)
    
    # Haupttext extrahieren (ohne Scripts und Styles)
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    main_text = soup.get_text(separator=' ', strip=False)
    
    # Normalisiere Whitespace
    main_text = re.sub(r'\s+', ' ', main_text)
    
    # Suche nach Keywords
    for category, keywords in KEYWORDS.items():
        result['keywords_found'][category] = []
        for keyword in keywords:
            contexts = extract_keyword_contexts(main_text, keyword)
            if contexts:
                result['keywords_found'][category].extend(contexts)
    
    # Entferne leere Kategorien
    result['keywords_found'] = {k: v for k, v in result['keywords_found'].items() if v}
    
    # Extrahiere Links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Relative URLs zu absoluten URLs konvertieren
        if href.startswith('/'):
            parsed_url = urlparse(url)
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
        elif not href.startswith('http'):
            continue
        
        if text and len(text) < 200:  # Vermeide sehr lange Link-Texte
            result['links'].append({
                'url': href,
                'text': text
            })
    
    # Extrahiere Kontaktinformationen (E-Mail, Telefon)
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    phone_pattern = re.compile(r'(\+?\d{1,3}[\s-]?)?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}')
    
    emails = email_pattern.findall(main_text)
    phones = phone_pattern.findall(main_text)
    
    if emails:
        result['contact_info']['emails'] = list(set(emails))
    if phones:
        result['contact_info']['phones'] = list(set(phones))
    
    # Extrahiere Textblöcke (Absätze, Listen)
    text_blocks = []
    for element in soup.find_all(['p', 'li', 'div']):
        text = element.get_text(strip=True)
        if text and len(text) > 20 and len(text) < 1000:  # Sinnvolle Größe
            text_blocks.append(text)
    
    result['text_blocks'] = text_blocks[:50]  # Begrenze auf 50 Blöcke
    
    # Versuche Professor/Lehrstuhlinhaber zu finden
    professor_patterns = [
        r'Prof\.?\s+Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'Professor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'Lehrstuhlinhaber[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    ]
    
    for pattern in professor_patterns:
        match = re.search(pattern, main_text, re.IGNORECASE)
        if match:
            result['professor'] = match.group(1)
            break
    
    # Versuche Abteilung/Lehrstuhl zu finden
    department_patterns = [
        r'Lehrstuhl\s+(?:für\s+)?([^,\n]+)',
        r'Abteilung\s+([^,\n]+)',
        r'Institut\s+(?:für\s+)?([^,\n]+)'
    ]
    
    for pattern in department_patterns:
        match = re.search(pattern, main_text, re.IGNORECASE)
        if match:
            result['department'] = match.group(1).strip()
            break
    
    return result


def extract_from_url(url: str) -> Dict[str, Any]:
    """
    Lädt eine URL und extrahiert Informationen.
    
    Args:
        url: URL der zu extrahierenden Seite
        
    Returns:
        Dictionary mit extrahierten Informationen
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        return extract_structured_info(soup, url)
    except Exception as e:
        return {
            'source_url': url,
            'error': str(e)
        }


def extract_from_html_file(filepath: str, source_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrahiert Informationen aus einer lokalen HTML-Datei.
    
    Args:
        filepath: Pfad zur HTML-Datei
        source_url: Optionale URL-Quelle (für Referenz)
        
    Returns:
        Dictionary mit extrahierten Informationen
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return {'error': f'Datei nicht gefunden: {filepath}'}
        
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        url = source_url or f'file://{path.absolute()}'
        return extract_structured_info(soup, url)
    except Exception as e:
        return {
            'source_url': source_url or filepath,
            'error': str(e)
        }


def main():
    """Hauptfunktion: Extrahiert Informationen von URLs oder HTML-Dateien."""
    import sys
    
    urls = [
        'https://www.cs.hhu.de/lehrstuehle-und-arbeitsgruppen/algorithmen-und-datenstrukturen',
        'https://dbs.cs.uni-duesseldorf.de/',
        'https://ccc.cs.uni-duesseldorf.de/~rothe/'
    ]
    
    results = {}
    
    for url in urls:
        print(f"Verarbeite URL: {url}", file=sys.stderr)
        try:
            extracted_data = extract_from_url(url)
            results[url] = extracted_data
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {url}: {e}", file=sys.stderr)
            results[url] = {'error': str(e)}
    
    # JSON-Ausgabe
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
