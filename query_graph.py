
"""
SPARQL Query Script for HHU Knowledge Graph
Phase 3: Nutzung und Validierung

Dieses Skript demonstriert die Nützlichkeit des generierten Wissensgraphen
durch drei Proof-of-Concept Abfragen für die Evaluation der Bachelorarbeit.
"""

from rdflib import Graph, Namespace

#  Graph laden
print("=" * 80)
print("HHU Knowledge Graph - SPARQL Query Demonstrator")
print("=" * 80)
print("\nLade Graph aus hhu_graph_full.ttl...")

g = Graph()
g.parse("hhu_graph_full.ttl", format="turtle")

# Namespace definieren 
HHU = Namespace("http://www.hhu.de/hhu-ontology#")

print(f" Graph erfolgreich geladen: {len(g)} Tripel\n")


# ABFRAGE A: Überblick - Anzahl Veranstaltungen und Personen
print("=" * 80)
print("ABFRAGE A: Überblick über den Graphen")
print("=" * 80)

query_a = """
PREFIX hhu: <http://www.hhu.de/hhu-ontology#>

SELECT (COUNT(DISTINCT ?veranstaltung) AS ?anzahl_veranstaltungen)
       (COUNT(DISTINCT ?person) AS ?anzahl_personen)
WHERE {
    ?veranstaltung a hhu:Veranstaltung .
    ?person a hhu:Person .
}
"""

results_a = g.query(query_a)
for row in results_a:
    print(f"\n  Statistik:")
    print(f"   • Veranstaltungen im Graph: {row.anzahl_veranstaltungen}")
    print(f"   • Personen im Graph:        {row.anzahl_personen}")

print("\n" + "-" * 80 + "\n")


# ABFRAGE B: Filterung nach Wert - Veranstaltungen mit > 5 ECTS
print("=" * 80)
print("ABFRAGE B: Veranstaltungen mit mehr als 5 ECTS")
print("=" * 80)

query_b = """
PREFIX hhu: <http://www.hhu.de/hhu-ontology#>

SELECT ?titel ?ects
WHERE {
    ?veranstaltung a hhu:Veranstaltung ;
                   hhu:hatTitel ?titel ;
                   hhu:hatECTS ?ects .
    FILTER (?ects > 5)
}
ORDER BY DESC(?ects)
"""

results_b = g.query(query_b)
result_count_b = 0

print("\n Gefundene Veranstaltungen (sortiert nach ECTS, absteigend):\n")
for row in results_b:
    result_count_b += 1
    print(f"   [{result_count_b}] {row.titel}")
    print(f"       → ECTS: {row.ects}")
    print()

if result_count_b == 0:
    print("    Keine Veranstaltungen mit mehr als 5 ECTS gefunden.\n")
else:
    print(f" Insgesamt {result_count_b} Veranstaltung(en) gefunden.\n")

print("-" * 80 + "\n")


# ABFRAGE C: Relationale Suche - Veranstaltungen von bestimmten Dozenten
print("=" * 80)
print("ABFRAGE C: Veranstaltungen von Dozenten (Mauve oder Conrad)")
print("=" * 80)

query_c = """
PREFIX hhu: <http://www.hhu.de/hhu-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dozent ?veranstaltung_titel
WHERE {
    ?veranstaltung a hhu:Veranstaltung ;
                   hhu:hatTitel ?veranstaltung_titel ;
                   hhu:wirdGehaltenVon ?person .
    
    # Hier nutzen wir rdfs:label, da wir das im Builder so gesetzt haben
    ?person a hhu:Person ;
            rdfs:label ?dozent .
            
    FILTER (regex(?dozent, "Mauve", "i") || regex(?dozent, "Conrad", "i"))
}
ORDER BY ?dozent ?veranstaltung_titel
"""

results_c = g.query(query_c)
result_count_c = 0

print("\n Gefundene Veranstaltungen:\n")
current_dozent = None
for row in results_c:
    result_count_c += 1
    if current_dozent != row.dozent:
        if current_dozent is not None:
            print()
        current_dozent = row.dozent
        print(f"   Dozent: {row.dozent}")
    print(f"      • {row.veranstaltung_titel}")

if result_count_c == 0:
    print("     Keine Veranstaltungen für die gesuchten Dozenten gefunden.\n")
else:
    print(f"\n Insgesamt {result_count_c} Veranstaltung(en) gefunden.\n")

print("-" * 80 + "\n")


# Abschluss
print("=" * 80)
print(" Alle Abfragen erfolgreich ausgeführt")
print("=" * 80)
print("\nDiese Queries demonstrieren:")
print("  • Aggregation (COUNT)")
print("  • Filterung nach Werten (FILTER >)")
print("  • Relationale Suche über Objektbeziehungen")
print("  • Pattern Matching mit Regex")
print("  • Sortierung (ORDER BY)")
print("\n Der Wissensgraph ist einsatzbereit für die Evaluation! \n")
