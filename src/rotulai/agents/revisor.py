from __future__ import annotations
import json

import openai

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


class ReviewerAgent:
    """Agent revisor: conecta com a API da OpenAI para validar os achados dos
    agents especialistas e produzir o veredito final.
    """

    def __init__(self, model: str | None = None):
        self.model = model or settings.openai_model
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    def review(self, label: LabelInput, findings: list[AgentFinding]) -> ReviewVerdict:
        user_content = (
            f"Produto: {label.product_name} (id: {label.product_id})\n"
            f"Ingredientes: {label.ingredients_text}\n\n"
            f"Achados dos agents especialistas:\n"
            f"{json.dumps([f.model_dump() for f in findings], ensure_ascii=False, indent=2)}\n\n"
            "Revise os achados acima e produza o veredito final."
        )

        response = self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ReviewVerdict,
        )
        return response.choices[0].message.parsed
