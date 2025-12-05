#!/bin/bash

source ~/.bashrc

# Set Neo4j home
export NEO4J_HOME=src/neo4j/neo4j-community-5.16.0

# Stop Neo4j
$NEO4J_HOME/bin/neo4j stop