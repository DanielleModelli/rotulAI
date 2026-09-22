from __future__ import annotations
import json

from rotulai.config import settings
from rotulai.schemas import AgentFinding, LabelInput, ReviewVerdict

SYSTEM_PROMPT = """\
Você é um revisor especialista em segurança alimentar e rotulagem de alérgenos.
Você recebe o texto de ingredientes de um rótulo e os achados de agents
especialistas (que já buscaram, por similaridade semântica, nomes técnicos ou
disfarçados de alérgenos). Seu trabalho é validar esses achados: confirmar os
que realmente indicam presença do alérgeno, descartar falsos positivos (termos
parecidos mas que não são o alérgeno em questão) e dar um veredito final
fundamentado.
"""

PROVEDORES = ("gemini", "anthropic")


class ReviewerAgent:
    """Agent revisor: valida os achados dos especialistas e produz o veredito
    final por meio de um LLM.

    Suporta Gemini e Claude atrás da mesma interface, com o mesmo prompt e o
    mesmo schema de saída, de modo que o provedor seja uma variável controlada
    do experimento e não uma diferença de implementação.
    """

    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or settings.llm_provider).lower()
        if self.provider not in PROVEDORES:
            raise ValueError(
                f"provedor '{self.provider}' desconhecido; use um de {PROVEDORES}"
            )

        if self.provider == "gemini":
            if not settings.google_api_key:
                raise ValueError("GOOGLE_API_KEY não definida para o provedor gemini")
            from google import genai

            self.model = model or settings.gemini_model
            self._client = genai.Client(api_key=settings.google_api_key)
        else:
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY não definida para o provedor anthropic")
            import anthropic

            self.model = model or settings.claude_model
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def review(self, label: LabelInput, findings: list[AgentFinding]) -> ReviewVerdict:
        user_content = (
            f"Produto: {label.product_name} (id: {label.product_id})\n"
            f"Ingredientes: {label.ingredients_text}\n\n"
            f"Achados dos agents especialistas:\n"
            f"{json.dumps([f.model_dump() for f in findings], ensure_ascii=False, indent=2)}\n\n"
            "Revise os achados acima e produza o veredito final."
        )

        if self.provider == "gemini":
            return self._review_gemini(user_content)
        return self._review_anthropic(user_content)

    def _review_gemini(self, user_content: str) -> ReviewVerdict:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ReviewVerdict,
            ),
        )
        return response.parsed

    def _review_anthropic(self, user_content: str) -> ReviewVerdict:
        response = self._client.messages.parse(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ReviewVerdict,
        )
        return response.parsed_output
