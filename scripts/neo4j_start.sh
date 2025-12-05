#!/bin/bash
#SBATCH --job-name=neo4j-server
#SBATCH --cpus-per-task=1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=8GB
#SBATCH --gres=gpu:0
#SBATCH --output=neo4j_server.log
#SBATCH --error=neo4j_server.err
source ~/.bashrc

# Configure Neo4j
export NEO4J_HOME=src/neo4j/neo4j-community-5.16.0
sed -i 's/#dbms.default_listen_address=0.0.0.0/dbms.default_listen_address=0.0.0.0/' $NEO4J_HOME/conf/neo4j.conf
sed -i 's/#dbms.security.auth_enabled=false/dbms.security.auth_enabled=true/' $NEO4J_HOME/conf/neo4j.conf
sed -i 's/#dbms.security.procedures.unrestricted=my.extensions.example,my.procedures.*/dbms.security.procedures.unrestricted=algo.*,apoc.*/' $NEO4J_HOME/conf/neo4j.conf
sed -i 's/#server.directories.plugins=plugins/server.directories.plugins=plugins/' $NEO4J_HOME/conf/neo4j.conf

# Start Neo4j
$NEO4J_HOME/bin/neo4j start