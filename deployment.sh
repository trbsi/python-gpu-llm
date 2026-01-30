#!/bin/bash
set -e  # exit on error

# -----------------------------
# Update system and install essentials
# -----------------------------
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv git curl build-essential unzip nginx

# -----------------------------
# Create and activate virtual environment
# -----------------------------
VENV_DIR="/workspace/venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip + wheel
pip install --upgrade pip setuptools wheel

# -----------------------------
# Install Python libraries
# -----------------------------
pip install torch==2.10.0
pip install transformers==5.0.0
pip install accelerate==1.12.0
pip install peft==0.18.1
pip install bitsandbytes==0.49.1
pip install huggingface-hub==1.3.5

pip install fastapi==0.128.0
pip install uvicorn[standard]==0.40.0
pip install bugsnag==4.8.1
pip install python-dotenv==1.2.1

# -----------------------------
# Install Hugging Face CLI officially
# -----------------------------
curl -LsSf https://hf.co/cli/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"  # ensure 'hf' is in PATH

# -----------------------------
# Navigate to FastAPI app
# -----------------------------
APP_DIR="/workspace/repo"
cd "$APP_DIR"
git pull || true

# -----------------------------
# Hugging Face login (non-interactive)
# -----------------------------
if [[ -n "$HUGGING_FACE_TOKEN" ]]; then
    echo "Logging into Hugging Face CLI..."
    hf auth login --token "$HUGGING_FACE_TOKEN"
else
    echo "⚠️  HUGGING_FACE_TOKEN not set, assuming public model"
fi

# -----------------------------
# Download BASE MODEL LOCALLY
# -----------------------------
MODEL_DIR="$APP_DIR/model"
mkdir -p "$MODEL_DIR"

echo "Downloading base model: $MODEL_NAME"
hf download "$MODEL_NAME" --repo-type model --local-dir "$MODEL_DIR"

echo "Base model downloaded to $MODEL_DIR"

# -----------------------------
# Download LoRA model if URL provided
# -----------------------------
if [[ -n "$MODEL_ZIP_URL" ]]; then
    MODEL_ZIP="lora_model.zip"
    echo "Downloading LoRA model from $MODEL_ZIP_URL..."
    curl -L -o "$MODEL_ZIP" "$MODEL_ZIP_URL"

    echo "Unzipping LoRA model..."
    unzip -o "$MODEL_ZIP" -d .
    rm "$MODEL_ZIP"
    echo "LoRA model extracted."
fi

# -----------------------------
# Create .env file
# -----------------------------
cat > .env <<EOL
BUGSNAG_API_KEY=$BUGSNAG_API_KEY
HUGGING_FACE_TOKEN=$HUGGING_FACE_TOKEN
MODEL_NAME=$MODEL_NAME
MODEL_PATH=$MODEL_DIR
EOL

echo ".env file created"

# -----------------------------
# Start FastAPI in background
# -----------------------------
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    > uvicorn.log 2>&1 &

UVICORN_PID=$!
echo "FastAPI started with PID $UVICORN_PID on 0.0.0.0:8000"

# -----------------------------
# Optional: self-register GPU with VPS
# -----------------------------
sleep 5

if [[ -n "$VPS_ENDPOINT" ]]; then
  echo "Register GPU."
  curl -X POST "$VPS_ENDPOINT" \
       -H "Authorization: Bearer ${REGISTRATION_TOKEN:-super-secret-token}" \
       -H "Content-Type: application/json" \
       -d "{}"
fi
