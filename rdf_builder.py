
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
import re
import json
import os


# Define namespace für HHU ontology
HHU = Namespace("http://www.hhu.de/hhu-ontology#")


def normalize_name(name):
    """
    Normalisiert einen Namen für die Verwendung in einer URI.
    Entfernt Sonderzeichen, Umlauten und Leerzeichen.
    
    Args:
        name (str): Der ursprüngliche Name
        
    Returns:
        str: Normalisierter Name, der für URI geeignet ist
    """
    # Replace umlauts
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss'
    }
    
    for umlaut, replacement in replacements.items():
        name = name.replace(umlaut, replacement)
    
    # Entferne alle nicht-alphanumerischen Zeichen außer Unterstrichen
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    return name


def extract_courses_from_json(full_data):
    """
    Adapter-Funktion, um Kursdaten aus der verschachtelten JSON-Struktur zu extrahieren.
    
    Diese Funktion verarbeitet die verschachtelte Struktur von all_data.json, die folgende Elemente enthält:
    - full_data['lsf_data']['data'] - LSF-Kurse
    - full_data['pdf_data']['data'] - PDF-Module
    
    Args:
        full_data (dict): Die vollständig geladene JSON-Daten mit verschachtelter Struktur
        
    Returns:
        list: Flattened list of dictionaries with standardized keys:
              - id: Kurs/Modul-Bezeichner
              - titel: Kurs/Modul-Titel
              - ects: ECTS-Punkte
              - dozenten: Liste der Dozenten-Namen
    """
    courses = []
    
    # Extrahiere LSF-Kurse
    try:
        lsf_data = full_data.get('lsf_data', {}).get('data', {})
        print(f"Processing {len(lsf_data)} LSF entries...")
        
        for file_name, course_data in lsf_data.items():
            # Extrahiere Daten aus LSF-Format
            course_id = course_data.get('veranstaltungs_id')
            titel = course_data.get('titel')
            ects_raw = course_data.get('ects_mit_pruefung')
            personen_list = course_data.get('personen', [])
            
            # Parse ECTS - extrahiere die erste Nummer wenn es sich um eine Zeichenkette handelt wie "10 ECTS für..."
            ects = None
            if ects_raw:
                # Versuche, eine numerische Wert aus der Zeichenkette zu extrahieren
                if isinstance(ects_raw, str):
                    match = re.search(r'(\d+)', ects_raw)
                    if match:
                        ects = int(match.group(1))
                else:
                    try:
                        ects = int(ects_raw)
                    except (ValueError, TypeError):
                        pass
            
            # Extrahiere Dozenten-Namen aus der personen-Liste
            dozenten = []
            for person in personen_list:
                if isinstance(person, dict) and 'name' in person:
                    dozenten.append(person['name'])
            
            # Erstelle standardisierte Kurs-Einträge
            if course_id and titel:  # Nur hinzufügen wenn wir mindestens ID und Titel haben
                courses.append({
                    'id': course_id,
                    'titel': titel,
                    'ects': ects,
                    'dozenten': dozenten  # Jetzt eine Liste
                })
        
        print(f"✓ Extracted {len(courses)} courses from LSF data")
    except Exception as e:
        print(f"Warning: Error processing LSF data: {e}")
    
    # Extrahiere PDF-Module
    try:
        pdf_data = full_data.get('pdf_data', {}).get('data', {})
        pdf_count = 0
        
        for pdf_file, pdf_content in pdf_data.items():
            modules = pdf_content.get('modules', [])
            print(f"Processing {len(modules)} modules from {pdf_file}...")
            
            for module in modules:
                modul_name = module.get('modul_name')
                ects_raw = module.get('ects')
                
                # Generiere pseudo-ID für PDF-Module
                # Verwende die ersten 50 Zeichen des Modulnamens, normalisiert
                if modul_name:
                    pseudo_id = f"PDF_{normalize_name(modul_name[:50])}"
                else:
                    # Verwende einen Counter wenn kein Name verfügbar
                    pseudo_id = f"PDF_Module_{pdf_count}"
                
                # Parse ECTS
                ects = None
                if ects_raw:
                    try:
                        ects = int(ects_raw)
                    except (ValueError, TypeError):
                        pass
                dozenten = []
                
                # Füge den Modul hinzu
                if modul_name:
                    courses.append({
                        'id': pseudo_id,
                        'titel': modul_name,
                        'ects': ects,
                        'dozenten': dozenten
                    })
                    pdf_count += 1
        
        print(f" Extracted {pdf_count} modules from PDF data")
    except Exception as e:
        print(f"Warning: Error processing PDF data: {e}")
    
    return courses


def create_ontology(graph):
    """
    Define die T-Box (ontology schema) für HHU Kurse.
    
    Args:
        graph (Graph): The RDF graph to add definitions to
    """
    # Define classes
    graph.add((HHU.Veranstaltung, RDF.type, RDFS.Class))
    graph.add((HHU.Veranstaltung, RDFS.label, Literal("Veranstaltung", lang="de")))
    graph.add((HHU.Veranstaltung, RDFS.comment, Literal("Eine Lehrveranstaltung an der HHU", lang="de")))
    
    graph.add((HHU.Person, RDF.type, RDFS.Class))
    graph.add((HHU.Person, RDFS.label, Literal("Person", lang="de")))
    graph.add((HHU.Person, RDFS.comment, Literal("Eine Person (Dozent/in) an der HHU", lang="de")))
    
    # Define properties
    graph.add((HHU.hatTitel, RDF.type, RDF.Property))
    graph.add((HHU.hatTitel, RDFS.label, Literal("hat Titel", lang="de")))
    
    graph.add((HHU.wirdGehaltenVon, RDF.type, RDF.Property))
    graph.add((HHU.wirdGehaltenVon, RDFS.label, Literal("wird gehalten von", lang="de")))
    graph.add((HHU.wirdGehaltenVon, RDFS.domain, HHU.Veranstaltung))
    graph.add((HHU.wirdGehaltenVon, RDFS.range, HHU.Person))
    
    graph.add((HHU.hatECTS, RDF.type, RDF.Property))
    graph.add((HHU.hatECTS, RDFS.label, Literal("hat ECTS-Punkte", lang="de")))
    graph.add((HHU.hatECTS, RDFS.domain, HHU.Veranstaltung))


def convert_json_to_rdf(json_data):
    """
    Convert JSON course data to RDF triples.
    
    Args:
        json_data (list): List of dictionaries containing course data.
                         Expected keys: 'titel', 'dozenten' (list), 'ects', 'id'
    
    Returns:
        Graph: RDF graph containing the converted data
    """

    # Erstelle ein neues Graph
    g = Graph()
    
    # Verbinde den HHU namespace
    g.bind("hhu", HHU)
    
    # Create ontology (T-Box)
    create_ontology(g)
    
    # Create instances (A-Box)
    for entry in json_data:
        event_id = entry.get('id')
        titel = entry.get('titel')
        dozenten = entry.get('dozenten', [])  # Now a list
        ects = entry.get('ects')
        
        # Skip einträge ohne notwendige Felder
        if not event_id or not titel:
            continue
        
        # Erstelle URI für die Veranstaltung
        event_uri = HHU[f"event_{event_id}"]
        
        # Add event type
        g.add((event_uri, RDF.type, HHU.Veranstaltung))
        
        # Add title
        g.add((event_uri, HHU.hatTitel, Literal(titel, lang="de")))
        
        # Add dozenten - iteriere über die Liste um mehrere Beziehungen zu erstellen
        if dozenten and isinstance(dozenten, list):
            for dozent in dozenten:
                if dozent:  # Skip empty strings
                    # Normalize dozent name for URI
                    normalized_name = normalize_name(dozent)
                    person_uri = HHU[f"person_{normalized_name}"]
                    
                    # Add person type
                    g.add((person_uri, RDF.type, HHU.Person))
                    
                    # Add person's name als label
                    g.add((person_uri, RDFS.label, Literal(dozent, lang="de")))
                    
                    # Link event zu person
                    g.add((event_uri, HHU.wirdGehaltenVon, person_uri))
        
        # Füge ECTS-Wert hinzu, wenn verfügbar
        if ects is not None:
            try:
                # Konvertiere ECTS-Wert zu Integer
                ects_value = int(ects)
                g.add((event_uri, HHU.hatECTS, Literal(ects_value, datatype=XSD.integer)))
            except (ValueError, TypeError):
                # Wenn die Konversion fehlschlägt, springe ECTS-Wert überspringen
                print(f"Warning: Could not convert ECTS value '{ects}' to integer for event {event_id}")
    
    return g


if __name__ == "__main__":
    # Pfad zur JSON-Datei aus Phase 1
    json_file_path = "all_data.json"
    
    # Lade die JSON-Daten
    if os.path.exists(json_file_path):
        print(f"Loading data from {json_file_path}...")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            print("✓ Successfully loaded JSON file")
            
            # Benutze den Adapter Pattern um die Kurse zu extrahieren
            print("\n--- Extracting Courses Using Adapter Pattern ---")
            course_data = extract_courses_from_json(full_data)
            
            print(f"\n Total courses extracted: {len(course_data)}")
            
        except Exception as e:
            print(f" Error loading or processing JSON file: {e}")
            print("Falling back to test data...")
            course_data = [
                {
                    'id': '12345',
                    'titel': 'Einführung in die Informatik',
                    'dozenten': ['Prof. Dr. Max Müller', 'Dr. Anna Schmidt'],
                    'ects': 6
                },
                {
                    'id': '67890',
                    'titel': 'Künstliche Intelligenz',
                    'dozenten': ['Dr. Anna Schmidt'],
                    'ects': None
                }
            ]
    else:
        print(f" File '{json_file_path}' not found!")
        print("Using test data instead...")
        course_data = [
            {
                'id': '12345',
                'titel': 'Einführung in die Informatik',
                'dozenten': ['Prof. Dr. Max Müller', 'Dr. Anna Schmidt'],
                'ects': 6
            },
            {
                'id': '67890',
                'titel': 'Künstliche Intelligenz',
                'dozenten': ['Dr. Anna Schmidt'],
                'ects': None  
            }
        ]
    
    print("\n--- Converting JSON to RDF ---")
    print(f"Processing {len(course_data)} entries...")
    
    # Konvertiere die JSON-Daten in RDF
    rdf_graph = convert_json_to_rdf(course_data)
    
    # Speichere den Graphen in einer Turtle-Datei
    if os.path.exists(json_file_path):
        output_file = "hhu_graph_full.ttl"
    else:
        output_file = "knowledge_graph.ttl"
    
    rdf_graph.serialize(destination=output_file, format='turtle')
    
    print(f"\n Successfully created RDF graph with {len(rdf_graph)} triples")
    print(f"Saved to: {output_file}")
    
    # Print statistics
    print("\n--- Graph Statistics ---")
    print(f"Total triples: {len(rdf_graph)}")
    print(f"Course entries processed: {len(course_data)}")
    
    # Print eine preview des Graphen 
    print("\n--- Preview of RDF Graph (Turtle format) ---")
    turtle_output = rdf_graph.serialize(format='turtle')
    lines = turtle_output.split('\n')
    if len(lines) > 30:
        print('\n'.join(lines[:30]))
        print(f"\n... ({len(lines) - 30} more lines)")
    else:
        print(turtle_output)
