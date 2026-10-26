from asgiref.sync import sync_to_async


@sync_to_async
def get_wagon_by_number(number: str):
    from apps.core.models import Wagon

    try:
        return Wagon.objects.get(number=number)
    except Wagon.DoesNotExist:
        return None
