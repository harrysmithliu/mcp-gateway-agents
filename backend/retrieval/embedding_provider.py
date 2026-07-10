from dataclasses import dataclass, field
from typing import Any, Callable

from backend.retrieval.ingestion_models import EmbeddingRequest, EmbeddingResponse


class EmbeddingProvider:
    """Defines the minimal interface for an embedding provider."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError


@dataclass(slots=True)
class MockEmbeddingProvider(EmbeddingProvider):
    """Provides deterministic local embeddings for ingestion pipeline scaffolding."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        vectors = [
            build_mock_embedding_vector(
                text=text,
                vector_dimensions=request.config.vector_dimensions,
            )
            for text in request.texts
        ]

        return EmbeddingResponse(
            vectors=vectors,
            model_name=request.config.model_name,
        )


@dataclass(slots=True)
class LocalSentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Loads a local sentence-transformers model and embeds texts on demand."""

    model_name: str
    device: str = "cpu"
    normalize_embeddings: bool = True
    sentence_transformer_factory: Callable[..., object] | None = None
    _model: object | None = field(default=None, init=False, repr=False)

    def _build_sentence_transformer_factory(self) -> Callable[..., object]:
        if self.sentence_transformer_factory is not None:
            return self.sentence_transformer_factory

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for local embedding runtime."
            ) from exc
        return SentenceTransformer

    def _get_model(self) -> object:
        if self._model is None:
            sentence_transformer_factory = self._build_sentence_transformer_factory()
            try:
                self._model = sentence_transformer_factory(
                    self.model_name,
                    device=self.device,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for local embedding runtime."
                ) from exc
        return self._model

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        model = self._get_model()
        vectors = model.encode(
            request.texts,
            normalize_embeddings=self.normalize_embeddings,
        )

        return EmbeddingResponse(
            vectors=[
                [float(value) for value in vector]
                for vector in vectors
            ],
            model_name=request.config.model_name,
        )


def build_mock_embedding_vector(
    text: str,
    vector_dimensions: int,
) -> list[float]:
    """Builds a deterministic mock embedding vector for one text input."""

    if vector_dimensions <= 0:
        raise ValueError("vector_dimensions must be positive")

    seed_values = [
        float(len(text)),
        float(len(text.split())),
        float(sum(ord(character) for character in text) % 1000) / 1000.0,
    ]

    repeated_values = (
        seed_values
        * ((vector_dimensions + len(seed_values) - 1) // len(seed_values))
    )

    return repeated_values[:vector_dimensions]
