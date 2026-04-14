import json
import os
from typing import Optional
from urllib import request


class OpenRouterClient:
    def __init__(self, api_key: str, model: str, base_url: str, app_name: str, http_referer: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.app_name = app_name
        self.http_referer = http_referer

    @classmethod
    def from_env(cls):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return None

        return cls(
            api_key=api_key,
            model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            app_name=os.getenv("OPENROUTER_APP_NAME", "Metis Intelligence"),
            http_referer=os.getenv("OPENROUTER_HTTP_REFERER"),
        )

    def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.app_name,
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer

        req = request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content = body["choices"][0]["message"]["content"]
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return content
