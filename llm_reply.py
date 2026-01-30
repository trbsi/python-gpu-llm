import os

import bugsnag
import torch
from huggingface_hub import login
from peft import PeftModel
from transformers import AutoTokenizer, BitsAndBytesConfig, AutoModelForCausalLM, Mistral3ForConditionalGeneration


class LlmReplyService:
    _tokenizer = None
    _model = None

    def init(self):
        try:
            if LlmReplyService._tokenizer is None or LlmReplyService._model is None:
                print('Loading model...')

                login(token=os.getenv("HUGGING_FACE_TOKEN"))
                base_model = os.getenv("MODEL_NAME")
                base_model_path = os.getenv("MODEL_PATH")
                trained_model = './trained_model'

                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )

                print('Prepare tokenizer')
                tokenizer = AutoTokenizer.from_pretrained(base_model)

                print('Prepare base model')
                if 'Ministral-3' in base_model:
                    model = Mistral3ForConditionalGeneration.from_pretrained(
                        base_model_path,
                        dtype=torch.float16,
                        device_map='cuda',
                        quantization_config=bnb_config,
                    )
                else:
                    model = AutoModelForCausalLM.from_pretrained(
                        base_model_path,
                        dtype=torch.float16,
                        device_map='cuda',
                        quantization_config=bnb_config,
                    )

                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token

                print('Load peft')
                model = PeftModel.from_pretrained(model, trained_model)
                model.eval()

                LlmReplyService._tokenizer = tokenizer
                LlmReplyService._model = model

                print('Model loaded.')
        except Exception as e:
            bugsnag.notify(e)
            print(e)

    def get_local_reply(self, chat_history: list) -> str:
        tokenizer = LlmReplyService._tokenizer
        model = LlmReplyService._model

        input_text = tokenizer.apply_chat_template(
            chat_history,
            tokenize=False,
            system_message="Assistant should respond in short, casual sentences.",
            add_generation_prompt=True
        )

        input_tokens = tokenizer(input_text, return_tensors='pt').to(model.device)

        output = model.generate(
            **input_tokens,
            max_new_tokens=75,
            temperature=0.85,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

        input_token_length = input_tokens['input_ids'].shape[1]
        generated_tokens = output[0][input_token_length:]
        reply = tokenizer.decode(generated_tokens, skip_special_tokens=True)

        return reply
