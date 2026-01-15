#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDF Builder for HHU Course Data
Phase 2: Semantic Modeling

This script converts JSON course data from LSF and PDF into RDF format using the
HHU ontology namespace. Uses an Adapter Pattern to handle the nested JSON structure.
"""

from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
import re
import json
import os


# Define namespace for HHU ontology
HHU = Namespace("http://www.hhu.de/hhu-ontology#")


def normalize_name(name):
    """
    Normalize a person's name for use in a URI.
    Removes special characters, umlauts, and spaces.
    
    Args:
        name (str): The original name
        
    Returns:
        str: Normalized name suitable for URI
    """
    # Replace umlauts
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
        'ß': 'ss'
    }
    
    for umlaut, replacement in replacements.items():
        name = name.replace(umlaut, replacement)
    
    # Remove all non-alphanumeric characters except underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    return name


def extract_courses_from_json(full_data):
    """
    Adapter function to extract course data from the nested JSON structure.
    
    This function handles the nested structure of all_data.json which contains:
    - full_data['lsf_data']['data'] - LSF courses
    - full_data['pdf_data']['data'] - PDF modules
    
    Args:
        full_data (dict): The complete loaded JSON data with nested structure
        
    Returns:
        list: Flattened list of dictionaries with standardized keys:
              - id: Course/module identifier
              - titel: Course/module title
              - ects: ECTS points
              - dozenten: List of lecturer names
    """
    courses = []
    
    # Extract LSF courses
    try:
        lsf_data = full_data.get('lsf_data', {}).get('data', {})
        print(f"Processing {len(lsf_data)} LSF entries...")
        
        for file_name, course_data in lsf_data.items():
            # Extract data from LSF format
            course_id = course_data.get('veranstaltungs_id')
            titel = course_data.get('titel')
            ects_raw = course_data.get('ects_mit_pruefung')
            personen_list = course_data.get('personen', [])
            
            # Parse ECTS - extract first number if it's a string like "10 ECTS für..."
            ects = None
            if ects_raw:
                # Try to extract numeric value from string
                if isinstance(ects_raw, str):
                    match = re.search(r'(\d+)', ects_raw)
                    if match:
                        ects = int(match.group(1))
                else:
                    try:
                        ects = int(ects_raw)
                    except (ValueError, TypeError):
                        pass
            
            # Extract lecturer names from personen list
            dozenten = []
            for person in personen_list:
                if isinstance(person, dict) and 'name' in person:
                    dozenten.append(person['name'])
            
            # Create standardized course entry
            if course_id and titel:  # Only add if we have at least ID and title
                courses.append({
                    'id': course_id,
                    'titel': titel,
                    'ects': ects,
                    'dozenten': dozenten  # Now a list
                })
        
        print(f"✓ Extracted {len(courses)} courses from LSF data")
    except Exception as e:
        print(f"Warning: Error processing LSF data: {e}")
    
    # Extract PDF modules
    try:
        pdf_data = full_data.get('pdf_data', {}).get('data', {})
        pdf_count = 0
        
        for pdf_file, pdf_content in pdf_data.items():
            modules = pdf_content.get('modules', [])
            print(f"Processing {len(modules)} modules from {pdf_file}...")
            
            for module in modules:
                modul_name = module.get('modul_name')
                ects_raw = module.get('ects')
                
                # Generate pseudo-ID for PDF modules
                # Use first 50 chars of module name, normalized
                if modul_name:
                    pseudo_id = f"PDF_{normalize_name(modul_name[:50])}"
                else:
                    # Use a counter if no name available
                    pseudo_id = f"PDF_Module_{pdf_count}"
                
                # Parse ECTS
                ects = None
                if ects_raw:
                    try:
                        ects = int(ects_raw)
                    except (ValueError, TypeError):
                        pass
                
                # PDF modules don't have lecturer information
                # We'll leave this as an empty list
                dozenten = []
                
                # Only add if we have a name
                if modul_name:
                    courses.append({
                        'id': pseudo_id,
                        'titel': modul_name,
                        'ects': ects,
                        'dozenten': dozenten
                    })
                    pdf_count += 1
        
        print(f"✓ Extracted {pdf_count} modules from PDF data")
    except Exception as e:
        print(f"Warning: Error processing PDF data: {e}")
    
    return courses


def create_ontology(graph):
    """
    Define the T-Box (ontology schema) for HHU courses.
    
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
    # Create a new graph
    g = Graph()
    
    # Bind the HHU namespace
    g.bind("hhu", HHU)
    
    # Create ontology (T-Box)
    create_ontology(g)
    
    # Create instances (A-Box)
    for entry in json_data:
        # Get data from entry
        event_id = entry.get('id')
        titel = entry.get('titel')
        dozenten = entry.get('dozenten', [])  # Now a list
        ects = entry.get('ects')
        
        # Skip entries without required fields
        if not event_id or not titel:
            continue
        
        # Create URI for the event
        event_uri = HHU[f"event_{event_id}"]
        
        # Add event type
        g.add((event_uri, RDF.type, HHU.Veranstaltung))
        
        # Add title
        g.add((event_uri, HHU.hatTitel, Literal(titel, lang="de")))
        
        # Add dozenten - iterate over the list to create multiple relations
        if dozenten and isinstance(dozenten, list):
            for dozent in dozenten:
                if dozent:  # Skip empty strings
                    # Normalize dozent name for URI
                    normalized_name = normalize_name(dozent)
                    person_uri = HHU[f"person_{normalized_name}"]
                    
                    # Add person type
                    g.add((person_uri, RDF.type, HHU.Person))
                    
                    # Add person's name as label
                    g.add((person_uri, RDFS.label, Literal(dozent, lang="de")))
                    
                    # Link event to person
                    g.add((event_uri, HHU.wirdGehaltenVon, person_uri))
        
        # Add ECTS if available
        if ects is not None:
            try:
                # Convert to integer if it's a string or float
                ects_value = int(ects)
                g.add((event_uri, HHU.hatECTS, Literal(ects_value, datatype=XSD.integer)))
            except (ValueError, TypeError):
                # If conversion fails, skip ECTS
                print(f"Warning: Could not convert ECTS value '{ects}' to integer for event {event_id}")
    
    return g


if __name__ == "__main__":
    # Path to the JSON file from Phase 1
    json_file_path = "all_data.json"
    
    # Load data from JSON file
    if os.path.exists(json_file_path):
        print(f"Loading data from {json_file_path}...")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            print("✓ Successfully loaded JSON file")
            
            # Use the Adapter Pattern to extract courses
            print("\n--- Extracting Courses Using Adapter Pattern ---")
            course_data = extract_courses_from_json(full_data)
            
            print(f"\n✓ Total courses extracted: {len(course_data)}")
            
        except Exception as e:
            print(f"✗ Error loading or processing JSON file: {e}")
            print("Falling back to test data...")
            # Fallback to test data
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
        print(f"✗ File '{json_file_path}' not found!")
        print("Using test data instead...")
        # Test data: 2 sample courses from LSF
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
                'ects': None  # No ECTS value
            }
        ]
    
    print("\n--- Converting JSON to RDF ---")
    print(f"Processing {len(course_data)} entries...")
    
    # Convert to RDF
    rdf_graph = convert_json_to_rdf(course_data)
    
    # Save to file - use different filename for full data
    if os.path.exists(json_file_path):
        output_file = "hhu_graph_full.ttl"
    else:
        output_file = "knowledge_graph.ttl"
    
    rdf_graph.serialize(destination=output_file, format='turtle')
    
    print(f"\n✓ Successfully created RDF graph with {len(rdf_graph)} triples")
    print(f"✓ Saved to: {output_file}")
    
    # Print statistics
    print("\n--- Graph Statistics ---")
    print(f"Total triples: {len(rdf_graph)}")
    print(f"Course entries processed: {len(course_data)}")
    
    # Print a preview of the graph (first 30 lines only for large graphs)
    print("\n--- Preview of RDF Graph (Turtle format) ---")
    turtle_output = rdf_graph.serialize(format='turtle')
    lines = turtle_output.split('\n')
    if len(lines) > 30:
        print('\n'.join(lines[:30]))
        print(f"\n... ({len(lines) - 30} more lines)")
    else:
        print(turtle_output)
