#!/bin/bash
set -e  # exit on error

# -----------------------------
# Update system and install essentials
# -----------------------------
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl build-essential unzip nginx

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
pip install transformers==5.0.0
pip install sentencepiece==0.2.1
pip install peft==0.18.1
pip install fastapi==0.128.0
pip install uvicorn[standard]==0.40.0
pip install bugsnag==4.8.1
pip install python-dotenv==1.2.1
pip install huggingface-hub==1.3.4
pip install -U bitsandbytes

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
# Create .env file
# -----------------------------
cat > .env <<EOL
BUGSNAG_API_KEY=$BUGSNAG_API_KEY
HUGGING_FACE_TOKEN=$HUGGING_FACE_TOKEN
EOL

echo ".env file created"

# -----------------------------
# Start FastAPI in background (localhost only)
# -----------------------------
exec uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "FastAPI started with PID $UVICORN_PID on 0.0.0.0:8000"

# -----------------------------
# Optional: self-register GPU with VPS
# -----------------------------
# Sleep a few seconds to let FastAPI initialize
sleep 5

VPS_ENDPOINT=${VPS_ENDPOINT}
REGISTRATION_TOKEN=${REGISTRATION_TOKEN:-"super-secret-token"}

echo "Register GPU."
curl -X POST "$VPS_ENDPOINT" \
     -H "Authorization: Bearer $REGISTRATION_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{}"
