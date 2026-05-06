# 🚀 LLM Server Setup Script

This script prepares a GPU server for running a FastAPI-based LLM service with Hugging Face models.

---

## ✅ Features

* Installs system dependencies (Python, Git, Nginx, etc.)
* Creates Python virtual environment
* Installs ML + API dependencies
* Downloads Hugging Face model locally
* Optional LoRA model support
* Optional FastAPI startup
* Runs server inside **screen** session (persistent background)

---

## 📦 Requirements

* Ubuntu / Debian server
* Root or sudo access
* (Optional) NVIDIA GPU + CUDA

---
## Run rewrite_title.py

```
apt-get install screen
screen -S rewrite
git clone https://github.com/trbsi/python-gpu-llm.git
cd python-gpu-llm
export MODEL_NAME="dphn/Dolphin-Mistral-24B-Venice-Edition"
export HUGGING_FACE_TOKEN="your_token_here"
./deployment.sh
source /workspace/venv/bin/activate
python rewrite_title.py --limit=10 --workers=2 --type=title_and_description --lang=en
```

---
## ⚙️ Environment Variables

Set before running:

```bash
export MODEL_NAME="dphn/Dolphin-Mistral-24B-Venice-Edition"
export HUGGING_FACE_TOKEN="your_token_here"
export BUGSNAG_API_KEY="your_key"
export MODEL_ZIP_URL="optional_lora_url"
export VPS_ENDPOINT="optional_endpoint"
```

---

## 🚀 Usage

### 1. Make script executable

```bash
chmod +x deployment.sh
```

---

### 2. Run setup (without API server)

```bash
./deployment.sh
```

---

### 3. Run setup + start FastAPI

```bash
./deployment.sh --with-uvicorn
```

---

## 🧠 Using screen

### Start session manually

```bash
screen -S mysession
```

### List sessions

```bash
screen -ls
```

### Attach to running FastAPI

```bash
screen -r fastapi_app
```

### Detach safely

```
CTRL + A, then D
```

---

## ⚠️ Notes

* If `--with-uvicorn` is not used → server is NOT started
* Model is downloaded locally (large disk usage!)
* Ensure enough VRAM for your model

---

## 🛠 Troubleshooting

### screen not found

```bash
sudo apt install screen
```

### cannot connect to API

```bash
screen -r fastapi_app
```

### missing model

Check:

```bash
echo $MODEL_NAME
```

---

## 🔥 Recommended workflow

1. Run setup
2. Start API with `--with-uvicorn`
3. Attach via screen for logs
4. Use nginx for production proxy

---

## 🚀 Next improvements

* systemd service instead of screen
* Docker version
* auto GPU detection
* S3 model storage

