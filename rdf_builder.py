#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDF Builder for HHU Course Data
Phase 2: Semantic Modeling

This script converts JSON course data from LSF into RDF format using the
HHU ontology namespace.
"""

from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
import re


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
                         Expected keys: 'titel', 'dozent', 'ects', 'id'
    
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
        dozent = entry.get('dozent')
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
        
        # Add dozent if available
        if dozent:
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
    # Test data: 2 sample courses from LSF
    test_data = [
        {
            'id': '12345',
            'titel': 'Einführung in die Informatik',
            'dozent': 'Prof. Dr. Max Müller',
            'ects': 6
        },
        {
            'id': '67890',
            'titel': 'Künstliche Intelligenz',
            'dozent': 'Dr. Anna Schmidt',
            'ects': None  # No ECTS value
        }
    ]
    
    print("Converting JSON to RDF...")
    print(f"Processing {len(test_data)} test entries...")
    
    # Convert to RDF
    rdf_graph = convert_json_to_rdf(test_data)
    
    # Save to file
    output_file = "knowledge_graph.ttl"
    rdf_graph.serialize(destination=output_file, format='turtle')
    
    print(f"\n✓ Successfully created RDF graph with {len(rdf_graph)} triples")
    print(f"✓ Saved to: {output_file}")
    
    # Print a preview of the graph
    print("\n--- Preview of RDF Graph (Turtle format) ---")
    print(rdf_graph.serialize(format='turtle'))
