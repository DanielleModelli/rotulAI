from __future__ import annotations
import json

import anthropic

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
    """Agent revisor: conecta com a Claude API para validar os achados dos
    agents especialistas e produzir o veredito final.
    """

    def __init__(self, model: str | None = None):
        self.model = model or settings.claude_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def review(self, label: LabelInput, findings: list[AgentFinding]) -> ReviewVerdict:
        user_content = (
            f"Produto: {label.product_name} (id: {label.product_id})\n"
            f"Ingredientes: {label.ingredients_text}\n\n"
            f"Achados dos agents especialistas:\n"
            f"{json.dumps([f.model_dump() for f in findings], ensure_ascii=False, indent=2)}\n\n"
            "Revise os achados acima e produza o veredito final."
        )

        response = self.client.messages.parse(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ReviewVerdict,
        )
        return response.parsed_output
