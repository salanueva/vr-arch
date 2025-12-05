from huggingface_hub import snapshot_download

sql_lora_path = snapshot_download(repo_id="neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1")
print(sql_lora_path)