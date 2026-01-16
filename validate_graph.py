#!/usr/bin/env python3
"""
validate_graph.py
Validiert den RDF-Graphen (hhu_graph_full.ttl) mithilfe von SHACL.
Phase 3: Datenqualitätsprüfung
"""

from rdflib import Graph, Namespace
from pyshacl import validate

# SHACL Shape-Graph als Turtle-String
# WICHTIG: Verwendet inline shape für bessere Kompatibilität mit numerischen Werten
shapes_graph_ttl = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix hhu: <http://www.hhu.de/hhu-ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Shape für Veranstaltungen
hhu:VeranstaltungShape
    a sh:NodeShape ;
    sh:targetClass hhu:Veranstaltung ;
    
    # Regel 1: Pflichtfeld - genau ein Titel
    sh:property [
        sh:path hhu:hatTitel ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:message "Jede Veranstaltung muss genau einen Titel haben" ;
    ] ;
    
    # Regel 2: Datentyp - Titel muss String/Literal sein
    sh:property [
        sh:path hhu:hatTitel ;
        sh:nodeKind sh:Literal ;
        sh:message "Der Titel muss ein Literal sein" ;
    ] ;
    
    # Regel 3: Wertebereich - ECTS maximal 30
    sh:property [
        sh:path hhu:hatECTS ;
        sh:maxInclusive 30 ;
        sh:message "ECTS-Punkte dürfen maximal 30 betragen" ;
    ] .
"""

def main():
    # Datengraph laden
    print("Lade Datengraph hhu_graph_full.ttl...")
    data_graph = Graph()
    data_graph.parse("hhu_graph_full.ttl", format="turtle")
    print(f"Graph geladen: {len(data_graph)} Tripel\n")
    
    # SHACL Shape-Graph erstellen
    shapes_graph = Graph()
    shapes_graph.parse(data=shapes_graph_ttl, format="turtle")
    
    # Validierung durchführen
    print("Führe SHACL-Validierung durch...\n")
    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference=None,  # Keine Inferenz, um Performance zu verbessern
        abort_on_first=False,
        advanced=True,  # Advanced features aktivieren
        allow_warnings=True
    )
    
    # Ergebnisse ausgeben
    print("=" * 60)
    if conforms:
        print("✓ VALIDIERUNG ERFOLGREICH")
        print("Der Graph entspricht allen SHACL-Regeln.")
    else:
        print("✗ VALIDIERUNG FEHLGESCHLAGEN")
        print("Der Graph verletzt eine oder mehrere SHACL-Regeln.\n")
        
        # Fehler aus dem results_graph extrahieren
        SH = Namespace("http://www.w3.org/ns/shacl#")
        
        # Alle ValidationResults iterieren
        validation_results = list(results_graph.subjects(
            predicate=SH.resultSeverity,
            object=SH.Violation
        ))
        
        print(f"Gefundene Fehler: {len(validation_results)}\n")
        
        for i, result in enumerate(validation_results, 1):
            # Fokus-Knoten (welche Veranstaltung betroffen ist)
            focus_node = results_graph.value(result, SH.focusNode)
            
            # Pfad (welche Property betroffen ist)
            path = results_graph.value(result, SH.resultPath)
            
            # Fehlermeldung
            message = results_graph.value(result, SH.resultMessage)
            
            # Wert (falls vorhanden)
            value = results_graph.value(result, SH.value)
            
            print(f"Fehler #{i}:")
            print(f"  Veranstaltung: {focus_node}")
            if path:
                print(f"  Property: {path}")
            if value:
                print(f"  Wert: {value}")
            print(f"  Grund: {message}")
            print()
    
    print("=" * 60)
    
    # Falls keine Fehler gefunden wurden, manuelle Prüfung durchführen
    if conforms:
        print("\n⚠️  Manuelle Prüfung: ECTS-Werte über 30 suchen...")
        HHU = Namespace("http://www.hhu.de/hhu-ontology#")
        
        fehlerhafte_veranstaltungen = []
        for s, p, o in data_graph.triples((None, HHU.hatECTS, None)):
            try:
                ects_wert = int(o)
                if ects_wert > 30:
                    # Titel der Veranstaltung holen
                    titel = data_graph.value(s, HHU.hatTitel)
                    fehlerhafte_veranstaltungen.append((s, ects_wert, titel))
            except (ValueError, TypeError):
                pass
        
        if fehlerhafte_veranstaltungen:
            print(f"\n✗ WARNUNG: {len(fehlerhafte_veranstaltungen)} Veranstaltung(en) mit ungültigen ECTS-Werten gefunden:\n")
            for uri, ects, titel in fehlerhafte_veranstaltungen:
                print(f"  • {titel}")
                print(f"    URI: {uri}")
                print(f"    ECTS: {ects} (Maximal erlaubt: 30)")
                print()
            print("⚠️  Hinweis: SHACL-Validierung hat diese Fehler NICHT erkannt.")
            print("    Dies liegt an der Darstellung numerischer Werte in RDF.")
        else:
            print("✓ Keine ECTS-Werte über 30 gefunden.")
    
    # Detaillierter Report nur bei tatsächlichen SHACL-Fehlern
    if not conforms:
        print("\nDetaillierter SHACL-Report:")
        print(results_text)

if __name__ == "__main__":
    main()
