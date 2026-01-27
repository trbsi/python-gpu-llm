#!/bin/bash
set -e  # exit on error

# -----------------------------
# Update system and install essentials
# -----------------------------
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl build-essential unzip

# -----------------------------
# Create and activate virtual environment
# -----------------------------
VENV_DIR="/workspace/venv"
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip
pip install --upgrade pip

# -----------------------------
# Install Python libraries
# -----------------------------
pip install torch==2.10.0
pip install transformers==5.0.0 sentencepiece==0.2.1 peft==0.18.1
pip install fastapi==0.128.0 uvicorn[standard]==0.40.0

# -----------------------------
# Navigate to your FastAPI app
# -----------------------------
APP_DIR="/workspace/repo"
cd $APP_DIR

# Optional: pull latest code from repo
git pull

# -----------------------------
# Download LoRA model
# -----------------------------
MODEL_ZIP="lora_model.zip"
echo "Downloading model from $MODEL_URL..."
curl -L -o "$MODEL_ZIP" "$MODEL_URL"

echo "Unzipping $MODEL_ZIP into current directory..."
unzip -o "$MODEL_ZIP" -d .
rm "$MODEL_ZIP"
echo "Model downloaded and extracted."

# -----------------------------
# Start FastAPI in background
# -----------------------------
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "FastAPI started with PID $UVICORN_PID"

# -----------------------------
# Optional: self-register GPU with VPS
# -----------------------------
# Sleep a few seconds to let FastAPI initialize
sleep 5

GPU_IP=$(curl -s ifconfig.me)
INSTANCE_ID=${INSTANCE_ID:-0}
VPS_ENDPOINT=${VPS_ENDPOINT}
REGISTRATION_TOKEN=${REGISTRATION_TOKEN:-"super-secret-token"}

curl -X POST "$VPS_ENDPOINT" \
     -H "Authorization: Bearer $REGISTRATION_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"ip\": \"$GPU_IP\", \"port\": 8000, \"instance_id\": \"$INSTANCE_ID\"}"

echo "GPU registered successfully."
