#!/usr/bin/env python3
"""
PDF Extractor - Extrahiert Modulbeschreibungen aus PDF-Dateien

Verwendet pdfminer.six zur Text-Extraktion und sucht nach Modulbeschreibungen
mit Mustern wie "Modul:", "ECTS:", etc.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams


# Patterns für Modulbeschreibungen
MODULE_PATTERNS = {
    'modul_name': [
        r'Modul[:\s]+([^\n]+)',
        r'Modulbezeichnung[:\s]+([^\n]+)',
        r'Modulname[:\s]+([^\n]+)'
    ],
    'ects': [
        r'ECTS[:\s]+(\d+(?:[.,]\d+)?)',
        r'Leistungspunkte[:\s]+(\d+(?:[.,]\d+)?)',
        r'Credit\s+Points[:\s]+(\d+(?:[.,]\d+)?)',
        r'LP[:\s]+(\d+(?:[.,]\d+)?)'
    ],
    'semester': [
        r'(\d+\.?\s*Semester)',
        r'Semester[:\s]+(\d+)',
        r'Studienjahr[:\s]+(\d+)'
    ],
    'veranstaltungsart': [
        r'Veranstaltungsart[:\s]+([^\n]+)',
        r'Art[:\s]+([^\n]+)',
        r'(Vorlesung|Übung|Seminar|Praktikum|Projekt)'
    ],
    'sprache': [
        r'Sprache[:\s]+([^\n]+)',
        r'Language[:\s]+([^\n]+)'
    ],
    'voraussetzungen': [
        r'Voraussetzungen[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Prerequisites[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Vorkenntnisse[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)'
    ],
    'inhalte': [
        r'Inhalt[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Inhalte[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Content[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)'
    ],
    'lernziele': [
        r'Lernziele[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Learning\s+Objectives[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Ziele[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)'
    ],
    'prüfung': [
        r'Prüfung[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)',
        r'Prüfungsform[:\s]+([^\n]+)',
        r'Examination[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n[A-Z][^:]+:|$)'
    ]
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrahiert Text aus einer PDF-Datei.
    
    Args:
        pdf_path: Pfad zur PDF-Datei
        
    Returns:
        Extrahierter Text
    """
    try:
        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5
        )
        text = extract_text(pdf_path, laparams=laparams)
        return text
    except Exception as e:
        raise Exception(f"Fehler beim Extrahieren von Text aus PDF: {e}")


def find_module_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Findet Modulblöcke im Text basierend auf verschiedenen Mustern.
    
    Args:
        text: Der zu durchsuchende Text
        
    Returns:
        Liste von gefundenen Modulbeschreibungen
    """
    modules = []
    
    # Strategie 1: Suche nach "Modul:" als Startpunkt
    modul_start_pattern = re.compile(r'Modul[:\s]+([^\n]+)', re.IGNORECASE)
    modul_starts = list(modul_start_pattern.finditer(text))
    
    # Strategie 2: Suche nach ECTS-Patterns als Indikator
    ects_pattern = re.compile(r'ECTS[:\s]+(\d+(?:[.,]\d+)?)', re.IGNORECASE)
    ects_matches = list(ects_pattern.finditer(text))
    
    # Kombiniere beide Strategien
    potential_starts = []
    
    for match in modul_starts:
        potential_starts.append({
            'position': match.start(),
            'type': 'modul_keyword',
            'name': match.group(1).strip()
        })
    
    for match in ects_matches:
        # Suche rückwärts nach Modul-Name (max. 500 Zeichen)
        start_pos = max(0, match.start() - 500)
        context_before = text[start_pos:match.start()]
        
        # Prüfe ob "Modul" in diesem Kontext vorkommt
        modul_in_context = re.search(r'Modul[:\s]+([^\n]+)', context_before, re.IGNORECASE)
        if modul_in_context:
            potential_starts.append({
                'position': start_pos + modul_in_context.start(),
                'type': 'ects_near_modul',
                'name': modul_in_context.group(1).strip()
            })
    
    # Sortiere nach Position
    potential_starts.sort(key=lambda x: x['position'])
    
    # Extrahiere Module
    for i, start_info in enumerate(potential_starts):
        start_pos = start_info['position']
        
        # Bestimme Endposition (nächstes Modul oder Ende)
        if i + 1 < len(potential_starts):
            end_pos = potential_starts[i + 1]['position']
        else:
            end_pos = len(text)
        
        # Extrahiere Block
        block_text = text[start_pos:end_pos]
        
        # Extrahiere Informationen aus diesem Block
        module_info = extract_module_info(block_text, start_info['name'])
        
        if module_info:
            modules.append(module_info)
    
    return modules


def extract_module_info(block_text: str, default_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Extrahiert strukturierte Informationen aus einem Modulblock.
    
    Args:
        block_text: Text des Modulblocks
        default_name: Vordefinierter Modulname
        
    Returns:
        Dictionary mit Modulinformationen oder None
    """
    module_info = {
        'modul_name': default_name,
        'ects': None,
        'semester': None,
        'veranstaltungsart': None,
        'sprache': None,
        'voraussetzungen': None,
        'inhalte': None,
        'lernziele': None,
        'prüfung': None,
        'raw_text': block_text[:2000]  # Erste 2000 Zeichen als Raw-Text
    }
    
    # Extrahiere für jedes Pattern
    for field, patterns in MODULE_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, block_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                # Bereinige Wert
                value = re.sub(r'\s+', ' ', value)
                if len(value) > 0:
                    module_info[field] = value
                    break
    
    # Nur zurückgeben wenn mindestens Modulname oder ECTS gefunden wurde
    if module_info['modul_name'] or module_info['ects']:
        return module_info
    
    return None


def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extrahiert Modulbeschreibungen aus einer PDF-Datei.
    
    Args:
        pdf_path: Pfad zur PDF-Datei
        
    Returns:
        Dictionary mit extrahierten Informationen
    """
    result = {
        'source_file': pdf_path,
        'modules': [],
        'statistics': {
            'total_modules_found': 0,
            'modules_with_ects': 0,
            'modules_with_name': 0
        }
    }
    
    try:
        path = Path(pdf_path)
        if not path.exists():
            return {
                'source_file': pdf_path,
                'error': f'Datei nicht gefunden: {pdf_path}'
            }
        
        print(f"Extrahiere Text aus PDF: {pdf_path}", file=__import__('sys').stderr)
        text = extract_text_from_pdf(str(path))
        
        print(f"Suche nach Modulbeschreibungen...", file=__import__('sys').stderr)
        modules = find_module_blocks(text)
        
        result['modules'] = modules
        result['statistics']['total_modules_found'] = len(modules)
        result['statistics']['modules_with_ects'] = sum(1 for m in modules if m.get('ects'))
        result['statistics']['modules_with_name'] = sum(1 for m in modules if m.get('modul_name'))
        
        print(f"Gefunden: {len(modules)} Module", file=__import__('sys').stderr)
        
    except Exception as e:
        result['error'] = str(e)
        print(f"Fehler: {e}", file=__import__('sys').stderr)
    
    return result


def main():
    """Hauptfunktion: Extrahiert Module aus PDF-Dateien."""
    import sys
    
    pdf_files = [
        'modulhandbuch_bachelor_po21_de.pdf'
    ]
    
    results = {}
    
    for pdf_file in pdf_files:
        print(f"Verarbeite PDF: {pdf_file}", file=sys.stderr)
        try:
            extracted_data = extract_from_pdf(pdf_file)
            results[pdf_file] = extracted_data
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {pdf_file}: {e}", file=sys.stderr)
            results[pdf_file] = {'error': str(e)}
    
    # JSON-Ausgabe
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
