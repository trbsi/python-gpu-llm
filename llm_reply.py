import os
import torch
import bugsnag
from huggingface_hub import login

from transformers import (
    AutoTokenizer,
    BitsAndBytesConfig,
    AutoModelForCausalLM,
)


# Uses base model to generate replies
class LlmReplyService:
    _tokenizer = None
    _model = None

    def init(self):
        try:
            if self._tokenizer is not None and self._model is not None:
                return

            print("Loading quantized model...")
            login(token=os.getenv("HUGGING_FACE_TOKEN"))
            model_name = os.getenv("MODEL_NAME")  # e.g. dphn/Dolphin-Mistral-24B-Venice-Edition

            # -----------------------------
            # 4-bit quantization config
            # -----------------------------
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )

            print("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                use_fast=True
            )

            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            print("Loading base model (quantized)...")

            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="cuda",
                quantization_config=bnb_config,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                attn_implementation="flash_attention_2",
            )

            model.eval()

            self._tokenizer = tokenizer
            self._model = model

            print("Quantized model loaded successfully.")

        except Exception as e:
            bugsnag.notify(e)
            print(f"Model loading failed: {e}")

    """
    chat_history = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "Explain black holes simply."}
    ]
    """

    def get_local_reply(self, chat_history: list, max_tokens: int = 120) -> str:
        tokenizer = self._tokenizer
        model = self._model

        if model is None or tokenizer is None:
            raise RuntimeError("Model not initialized. Call init() first.")

        prompt = tokenizer.apply_chat_template(
            chat_history,
            tokenize=False,
            add_generation_prompt=True,
            # system_message=""
        )

        inputs = tokenizer(prompt, return_tensors="pt")

        # move inputs to model device (important for device_map="auto")
        inputs = inputs.to(model.device)

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        generated_tokens = output[0][input_len:]

        return tokenizer.decode(generated_tokens, skip_special_tokens=True)

    def get_local_reply_batch(self, chat_histories: list, max_tokens: int = 300):
        tokenizer = self._tokenizer
        model = self._model

        prompts = [
            tokenizer.apply_chat_template(
                chat,
                tokenize=False,
                add_generation_prompt=True,
            )
            for chat in chat_histories
        ]

        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True
        )

        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        results = []
        for i in range(len(outputs)):
            input_len = inputs["input_ids"].shape[1]
            generated_tokens = outputs[i][input_len:]
            text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            results.append(text)

        return results
