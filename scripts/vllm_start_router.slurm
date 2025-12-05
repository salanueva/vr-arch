#!/bin/bash
#SBATCH --job-name=vr-arch
#SBATCH --cpus-per-task=4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=64GB
#SBATCH --gres=gpu:1
#SBATCH --output=vr-arch_server.log
#SBATCH --error=vr-arch_server.err

# Cleanup background processes on exit
cleanup() {
    echo "Cleaning up background processes..."
    pkill -P $$
    exit
}
trap cleanup EXIT INT TERM


### TODO: DEFINE THE FOLLOWING VARIABLES ###
# Activate the virtual environment
source .venv/bin/activate

# Set cache directory
export HF_HOME="/ncache/hub"

# Set LoRA path: copy and paste the path to your LoRA model here (it is printed after downloading the model using download_lora_weights.py in scripts/)
lora_path="/sorgin1/users/oijurco/.cache/huggingface/hub/models--neo4j--text2cypher-gemma-2-9b-it-finetuned-2024v1/snapshots/e0e780fad9183c342b9f576b152b76f307e69a6d"
############################################


echo "Starting text2cypher server on port 8007..."

vllm serve google/gemma-2-9b-it \
    --port 8007 \
    --enable-lora \
    --lora-modules '{"name": "text2cypher", "path": "$lora_path", "base_model_name": "google/gemma-2-9b-it"}' \
    --quantization bitsandbytes \
    --load-format bitsandbytes \
    --max-model-len 4096 \
    --max-lora-rank 64 \
    --enforce-eager \
    --gpu-memory-utilization 0.65 &

sleep 30

### TODO: ADJUST THE MODEL, PORT OR PARAMETERS AS NEEDED ###
# echo "Starting router/modify LLM server on port 8011..."
# vllm serve Qwen/Qwen3-4B \e
#     --port 8011 \
#     --reasoning-parser qwen3 \
#     --max-model-len 8192 \
#     --dtype bfloat16 \
#     --enforce-eager \
#     --gpu-memory-utilization 0.3 &

echo "Starting router/modify LLM server on port 8010..."
vllm serve Qwen/Qwen3-8B \
    --port 8010 \
    --reasoning-parser qwen3 \
    --max-model-len 8192 \
    --dtype bfloat16 \
    --enforce-eager \
    --gpu-memory-utilization 0.3 &

# echo "Starting router/modify LLM server on port 8008..."
# vllm serve Qwen/Qwen3-14B \
#     --port 8008 \
#     --reasoning-parser qwen3 \
#     --max-model-len 8192 \
#     --dtype bfloat16 \
#     --enforce-eager \
#     --gpu-memory-utilization 0.3 &


# echo "Starting router/modify LLM server on port 8009..."
# vllm serve Qwen/Qwen3-32B \
#     --port 8009 \
#     --reasoning-parser qwen3 \
#     --max-model-len 8192 \
#     --dtype bfloat16 \
#     --enforce-eager \
#     --gpu-memory-utilization 0.3 &
############################################################

sleep 30

echo "Both servers started. Monitoring processes..."
while true; do
    if ! pgrep -f "port 8007" > /dev/null; then
        echo "Text2cypher server (port 8007) has stopped. Exiting..."
        break
    fi
    if ! pgrep -f "port 8010" > /dev/null; then
        echo "Helper server (port 8010) has stopped. Exiting..."
        break
    fi
    sleep 60
done

echo "Job ending, cleaning up..."