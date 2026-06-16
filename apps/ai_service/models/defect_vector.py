from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField


class DefectVector(models.Model):
    """Stores an embedding of a closed defect for historical RAG retrieval."""

    defect = models.OneToOneField(
        "defects.Defect",
        on_delete=models.CASCADE,
        related_name="vector",
        verbose_name=_("Defect"),
    )
    content = models.TextField(verbose_name=_("Content"))
    embedding = VectorField(dimensions=1536, verbose_name=_("Embedding"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Defect Vector")
        verbose_name_plural = _("Defect Vectors")
        indexes = [
            HnswIndex(
                fields=["embedding"],
                name="defect_hnsw_idx",
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Vector({self.defect_id})"
