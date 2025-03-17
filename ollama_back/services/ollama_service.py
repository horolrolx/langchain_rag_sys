import requests
from config.config import Config
from langchain_core.language_models import LLM

SYSTEM_PROMPT = (
    "당신은 최첨단 AI 비서입니다. "
    "질문에 답변할 때는 항상 논리적이고 단계적으로 사고하세요. "
    "필요한 정보가 없을 경우, '주어진 정보로는 정확한 답변을 제공할 수 없습니다.'라고 솔직하게 답하세요. "
    "기술적 개념은 쉽게 풀어 설명하되, 핵심 내용은 유지하세요."
)

class OllamaLLM(LLM):
    @property
    def _llm_type(self) -> str:
        return "ollama"

    def _call(self, prompt: str, stop=None) -> str:
        url = "http://host.docker.internal:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "model": "exaone3.5:latest",
        }

        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '정보를 찾을 수 없습니다.')