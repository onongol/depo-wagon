from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField


class DocumentChunk(models.Model):
    """Represents a chunk of text extracted from a DepotDocument, along with its embedding vector."""

    document = models.ForeignKey(
        "ai_service.DepotDocument",
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name=_("Document"),
    )
    content = models.TextField(verbose_name=_("Content"))
    embedding = VectorField(dimensions=1536, verbose_name=_("Embedding"))
    chunk_index = models.PositiveIntegerField(verbose_name=_("Chunk Index"))
    page_number = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Page Number")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Document Chunk")
        verbose_name_plural = _("Document Chunks")
        ordering = ["document", "chunk_index"]
        indexes = [
            models.Index(fields=["document"]),
            HnswIndex(
                fields=["embedding"],
                name="embedding_hnsw_idx",
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.document.title} – {self.chunk_index}"
