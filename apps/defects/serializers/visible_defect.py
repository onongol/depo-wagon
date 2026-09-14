from apps.defects.models import Defect


class VisibleDefectMixin:
    """Accept only a defect the requesting user can see, as if no other existed."""

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        fields["defect"].queryset = (
            Defect.objects.visible_to(request.user)
            if request is not None
            else Defect.objects.none()
        )
        return fields
