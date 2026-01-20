#!/usr/bin/env python3
"""
Extraction Orchestrator - Kombiniert alle Extraktoren

Ruft lsf_extractor, website_extractor und pdf_extractor auf
und kombiniert die Ergebnisse in einer einzigen JSON-Datei.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Import der Extraktoren
from lsf_extractor import parse_detail_page
from website_extractor import extract_from_url
from pdf_extractor import extract_from_pdf


def run_lsf_extraction() -> Dict[str, Any]:
    """
    Führt die LSF-Extraktion durch.
    
    Returns:
        Dictionary mit LSF-Daten
    """
    print("=" * 60, file=sys.stderr)
    print("Phase 1: LSF-Extraktion", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    base_path = Path(__file__).parent
    detail_files = [
        'data:/- Vorlesung Präsenz: Algorithmen und Datenstrukturen Heinrich Heine Universität Düsseldorf.html',
        'data:/- Vorlesung (Hybrid Plus: Präsenz + Streaming + Aufzeichnung): Programmierung Heinrich Heine Univers.html',
        'data:/- Vorlesung (Hybrid Plus: Präsenz + Streaming + Aufzeichnung): Rechnerarchitektur Heinrich Heine Uni.html',
        'data:/- Übung: Programmierung (Übung) Heinrich Heine Universität Düsseldorf.html'
    ]
    
    results = {}
    
    for filename in detail_files:
        filepath = base_path / filename
        if filepath.exists():
            print(f"  Verarbeite: {filename}", file=sys.stderr)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                extracted_data = parse_detail_page(html_content)
                results[filename] = extracted_data
            except Exception as e:
                print(f"  Fehler: {e}", file=sys.stderr)
                results[filename] = {'error': str(e)}
        else:
            print(f"  Datei nicht gefunden: {filename}", file=sys.stderr)
            results[filename] = {'error': 'Datei nicht gefunden'}
    
    return {
        'source': 'lsf_extractor',
        'data': results,
        'count': len(results)
    }


def run_website_extraction() -> Dict[str, Any]:
    """
    Führt die Website-Extraktion durch.
    
    Returns:
        Dictionary mit Website-Daten
    """
    print("\n" + "=" * 60, file=sys.stderr)
    print("Phase 2: Website-Extraktion", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    urls = [
        'https://www.cs.hhu.de/lehrstuehle-und-arbeitsgruppen/algorithmen-und-datenstrukturen',
        'https://dbs.cs.uni-duesseldorf.de/',
        'https://ccc.cs.uni-duesseldorf.de/~rothe/'
    ]
    
    results = {}
    
    for url in urls:
        print(f"  Verarbeite URL: {url}", file=sys.stderr)
        try:
            extracted_data = extract_from_url(url)
            results[url] = extracted_data
        except Exception as e:
            print(f"  Fehler: {e}", file=sys.stderr)
            results[url] = {'error': str(e)}
    
    return {
        'source': 'website_extractor',
        'data': results,
        'count': len(results)
    }


def run_pdf_extraction() -> Dict[str, Any]:
    """
    Führt die PDF-Extraktion durch.
    
    Returns:
        Dictionary mit PDF-Daten
    """
    print("\n" + "=" * 60, file=sys.stderr)
    print("Phase 3: PDF-Extraktion", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    pdf_files = [
        'data:/modulhandbuch_bachelor_po21_de.pdf'
    ]
    
    results = {}
    
    for pdf_file in pdf_files:
        print(f"  Verarbeite PDF: {pdf_file}", file=sys.stderr)
        try:
            extracted_data = extract_from_pdf(pdf_file)
            results[pdf_file] = extracted_data
        except Exception as e:
            print(f"  Fehler: {e}", file=sys.stderr)
            results[pdf_file] = {'error': str(e)}
    
    return {
        'source': 'pdf_extractor',
        'data': results,
        'count': len(results)
    }


def combine_results(lsf_data: Dict[str, Any], 
                    website_data: Dict[str, Any], 
                    pdf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kombiniert alle Extraktionsergebnisse in einer strukturierten JSON.
    
    Args:
        lsf_data: Daten vom LSF-Extraktor
        website_data: Daten vom Website-Extraktor
        pdf_data: Daten vom PDF-Extraktor
        
    Returns:
        Kombiniertes Dictionary
    """
    combined = {
        'metadata': {
            'extraction_date': datetime.now().isoformat(),
            'sources': ['lsf_extractor', 'website_extractor', 'pdf_extractor'],
            'version': '1.0'
        },
        'lsf_data': lsf_data,
        'website_data': website_data,
        'pdf_data': pdf_data,
        'statistics': {
            'lsf_entries': lsf_data.get('count', 0),
            'website_entries': website_data.get('count', 0),
            'pdf_entries': pdf_data.get('count', 0),
            'total_modules_from_pdf': sum(
                len(v.get('modules', [])) 
                for v in pdf_data.get('data', {}).values() 
                if isinstance(v, dict) and 'modules' in v
            )
        }
    }
    
    return combined


def main():
    """Hauptfunktion: Führt alle Extraktionen durch und speichert das Ergebnis."""
    print("Starte Extraktions-Pipeline...\n", file=sys.stderr)
    
    # Führe alle Extraktionen durch
    try:
        lsf_data = run_lsf_extraction()
    except Exception as e:
        print(f"Fehler bei LSF-Extraktion: {e}", file=sys.stderr)
        lsf_data = {'source': 'lsf_extractor', 'error': str(e), 'data': {}, 'count': 0}
    
    try:
        website_data = run_website_extraction()
    except Exception as e:
        print(f"Fehler bei Website-Extraktion: {e}", file=sys.stderr)
        website_data = {'source': 'website_extractor', 'error': str(e), 'data': {}, 'count': 0}
    
    try:
        pdf_data = run_pdf_extraction()
    except Exception as e:
        print(f"Fehler bei PDF-Extraktion: {e}", file=sys.stderr)
        pdf_data = {'source': 'pdf_extractor', 'error': str(e), 'data': {}, 'count': 0}
    
    # Kombiniere Ergebnisse
    print("\n" + "=" * 60, file=sys.stderr)
    print("Kombiniere Ergebnisse...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    combined_data = combine_results(lsf_data, website_data, pdf_data)
    
    # Speichere in JSON-Datei
    output_file = Path(__file__).parent / 'all_data.json'
    print(f"\nSpeichere Ergebnisse in: {output_file}", file=sys.stderr)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    
    # Zeige Statistiken
    stats = combined_data['statistics']
    print("\n" + "=" * 60, file=sys.stderr)
    print("Statistiken:", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  LSF-Einträge: {stats['lsf_entries']}", file=sys.stderr)
    print(f"  Website-Einträge: {stats['website_entries']}", file=sys.stderr)
    print(f"  PDF-Einträge: {stats['pdf_entries']}", file=sys.stderr)
    print(f"  Module aus PDF: {stats['total_modules_from_pdf']}", file=sys.stderr)
    print(f"\nErgebnisse gespeichert in: {output_file}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == '__main__':
    main()
