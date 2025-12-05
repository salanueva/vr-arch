#!/bin/bash

### TODO: INSTALL Java 17 AND SPEFICY JAVA_HOME PATH BELOW ###
echo 'export JAVA_HOME=/usr/local/java/jdk-17.0.12' >> ~/.bashrc
##############################################################

echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Install Neo4j
export NEO4J_HOME=src/neo4j

mkdir -p $NEO4J_HOME
wget -O $NEO4J_HOME/neo4j.tar.gz https://neo4j.com/artifact.php?name=neo4j-community-5.16.0-unix.tar.gz
tar -xvzf $NEO4J_HOME/neo4j.tar.gz
mv neo4j-community-* $NEO4J_HOME
rm $NEO4J_HOME/neo4j.tar.gz
