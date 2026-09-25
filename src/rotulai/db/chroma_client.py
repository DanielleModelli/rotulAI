from __future__ import annotations
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from rotulai.config import settings

_embedding_function: SentenceTransformerEmbeddingFunction | None = None

_client: chromadb.ClientAPI | None = None


def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    """Carrega o modelo de embedding na primeira chamada, não no import.

    Instanciar no import fazia qualquer `import rotulai.agents` baixar e
    carregar o modelo, o que torna testes lentos e quebra sem rede.
    """
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
    return _embedding_function


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        if settings.chroma_mode == "local":
            _client = chromadb.PersistentClient(path=settings.chroma_path)
        else:
            _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _client


def get_terms_collection(category: str):
    """Cada categoria de alérgeno tem sua própria coleção de termos conhecidos
    (nomes disfarçados/técnicos). Um novo agent especialista basta chamar isso
    com sua própria categoria para ganhar uma base de conhecimento isolada.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=f"allergen_terms_{category}",
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def semantic_match(collection, query_text: str, n_results: int = 3):
    """Busca os termos conhecidos mais próximos semanticamente de `query_text`.

    Retorna uma lista de (documento, metadata, similaridade), com similaridade
    em [0, 1] (1 = idêntico), já convertida a partir da distância de cosseno.
    """
    result = collection.query(query_texts=[query_text], n_results=n_results)
    documents = result["documents"][0] if result["documents"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []
    distances = result["distances"][0] if result["distances"] else []

    matches = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        similarity = 1 - distance
        matches.append((document, metadata, similarity))
    return matches
