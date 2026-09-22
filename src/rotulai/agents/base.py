from __future__ import annotations
from abc import ABC, abstractmethod

from rotulai.config import settings
from rotulai.db.chroma_client import get_terms_collection, semantic_match
from rotulai.schemas import AgentFinding, LabelInput, MatchedTerm
from rotulai.agents.utils import split_ingredients


class SpecialistAgent(ABC):
    """Interface que todo agent especialista (laticínios, chocolate, ...) implementa.

    Para plugar uma nova categoria de alérgeno:
      1. Criar uma classe que herde de SpecialistAgent (ou de SemanticTermAgent,
         abaixo, se a detecção for por similaridade semântica no ChromaDB).
      2. Decorá-la com @register_agent("nome_da_categoria").
      3. Implementar analyze() (dispensável se herdar de SemanticTermAgent).
    O DecisorAgent descobre agents novos automaticamente via registry — não
    precisa alterar nada fora do arquivo do novo agent.
    """

    category: str

    @abstractmethod
    def analyze(self, label: LabelInput) -> AgentFinding: ...


class SemanticTermAgent(SpecialistAgent):
    """Implementação padrão: compara cada ingrediente do rótulo contra a
    coleção de termos conhecidos (nomes disfarçados/técnicos) da própria
    categoria no ChromaDB, via similaridade semântica.

    Cobre a maioria dos casos de "achar nome escondido de alérgeno". Um novo
    agent só precisa herdar disso e ser registrado — sem reimplementar a
    busca vetorial.
    """

    def __init__(self, threshold: float | None = None):
        self.threshold = threshold if threshold is not None else settings.similarity_threshold
        self.collection = get_terms_collection(self.category)

    def analyze(self, label: LabelInput) -> AgentFinding:
        matches: list[MatchedTerm] = []
        for ingredient in split_ingredients(label.ingredients_text):
            for document, _metadata, similarity in semantic_match(self.collection, ingredient):
                if similarity >= self.threshold:
                    matches.append(
                        MatchedTerm(
                            term_found=ingredient,
                            known_hidden_name=document,
                            similarity=round(similarity, 3),
                        )
                    )

        return AgentFinding(
            category=self.category,
            hidden_allergen_detected=len(matches) > 0,
            matches=matches,
        )
