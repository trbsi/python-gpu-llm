#!/bin/bash
set -e  # exit on error

INSTALL_UVICORN=false

# -----------------------------
# Parse arguments
# -----------------------------
for arg in "$@"; do
  case $arg in
    --with-uvicorn)
      INSTALL_UVICORN=true
      shift
      ;;
  esac
done

# -----------------------------
# Update system and install essentials
# -----------------------------
sudo apt update
sudo apt install -y \
  python3 python3-pip python3-venv git curl build-essential unzip nginx screen

# -----------------------------
# Create and activate virtual environment
# -----------------------------
VENV_DIR="/workspace/venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# needed for vLLM (CXXABI_1.3.15 is needed). but not used right now
#apt update
#apt install -y software-properties-common
#add-apt-repository ppa:ubuntu-toolchain-r/test -y
#apt update
#apt install -y libstdc++6

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
pip install bugsnag==4.8.1
pip install python-dotenv==1.2.1
pip install requests>=2.31.0
pip install vllm>=0.19.0

if [ "$INSTALL_UVICORN" = true ]; then
  pip install "uvicorn[standard]==0.40.0"
fi

# -----------------------------
# Install Hugging Face CLI
# -----------------------------
curl -LsSf https://hf.co/cli/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"

# -----------------------------
# Navigate to app
# -----------------------------
APP_DIR="/workspace/repo"
cd "$APP_DIR"
git pull || true

# -----------------------------
# Hugging Face login
# -----------------------------
if [[ -n "$HUGGING_FACE_TOKEN" ]]; then
    hf auth login --token "$HUGGING_FACE_TOKEN"
else
    echo "⚠️ No HF token provided"
fi

# -----------------------------
# Download base model
# -----------------------------
MODEL_DIR="$APP_DIR/model"
mkdir -p "$MODEL_DIR"

echo "Downloading model: $MODEL_NAME"
hf download "$MODEL_NAME" --repo-type model --local-dir "$MODEL_DIR"

# -----------------------------
# Download LoRA (optional)
# -----------------------------
if [[ -n "$MODEL_ZIP_URL" ]]; then
    curl -L -o lora_model.zip "$MODEL_ZIP_URL"
    unzip -o lora_model.zip -d .
    rm lora_model.zip
fi

# -----------------------------
# Create .env
# -----------------------------
cat > .env <<EOL
BUGSNAG_API_KEY=$BUGSNAG_API_KEY
HUGGING_FACE_TOKEN=$HUGGING_FACE_TOKEN
MODEL_NAME=$MODEL_NAME
MODEL_PATH=$MODEL_DIR
EOL

# -----------------------------
# Start FastAPI (optional)
# -----------------------------
export PYTHONUNBUFFERED=1
export HF_HUB_DISABLE_TELEMETRY=1

if [ "$INSTALL_UVICORN" = true ]; then
  echo "Starting FastAPI inside screen..."

  screen -dmS fastapi_app bash -c "
    source $VENV_DIR/bin/activate &&
    uvicorn main:app --host 0.0.0.0 --port 8000
  "

  echo "FastAPI running in screen session: fastapi_app"
else
  echo "Skipping FastAPI startup (uvicorn not installed)"
fi

# -----------------------------
# Optional GPU registration
# -----------------------------
sleep 5

if [[ -n "$VPS_ENDPOINT" ]]; then
  curl -X POST "$VPS_ENDPOINT" \
       -H "Authorization: Bearer ${REGISTRATION_TOKEN:-super-secret-token}" \
       -H "Content-Type: application/json" \
       -d "{}"
fi