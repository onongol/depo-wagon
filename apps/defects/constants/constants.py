from django.db import models
from django.utils.translation import gettext_lazy as _


class DefectSeverity(models.TextChoices):
    LOW = "low", _("Low")  # Бага
    MEDIUM = "medium", _("Medium")  # Дунд
    HIGH = "high", _("High")  # Өндөр
    CRITICAL = "critical", _("Critical")  # Онц ноцтой


class DefectStatus(models.TextChoices):
    OPEN = "open", _("Open")  # Илэрсэн
    IN_PROGRESS = "in_progress", _("In Progress")  # Хийгдэж байна
    CLOSED = "closed", _("Closed")  # Хаасан


class DefectNode(models.TextChoices):
    BODY = "body", _("Body")  # Их бие
    FRAME = "frame", _("Frame")  # Арал
    BOGIE = "bogie", _("Bogie")  # Тэрэгцэр
    WHEELSET = "wheelset", _("Wheelset")  # Хос дугуй
    BEARING = "bearing", _("Bearing")  # Гүүшин
    BRAKE = "brake", _("Brake System")  # Тоормосны систем
    COUPLER = "coupler", _("Coupler")  # Нийлүүлэх төхөөрөмж
    OTHER = "other", _("Other")  # Бусад


class DefectType(models.TextChoices):
    CRACK = "crack", _("Crack")  # Ан цав
    WEAR = "wear", _("Wear")  # Элэгдэл
    DEFORMATION = "deformation", _("Deformation")  # Хэв гажилт
    FRACTURE = "fracture", _("Fracture")  # Хугарал
    DESTRUCTION = "destruction", _("Destruction")  # Эвдрэл
    CORROSION = "corrosion", _("Corrosion")  # Зэврэлт
    THREAD_STRIP = "thread_strip", _("Thread Strip")  # Эрээс гарах
    LEAK = "leak", _("Leak")  # Шүүрэлт
    LOOSE = "loose", _("Loose Fastening")  # Бэхэлгээ сулрах
    MISSING = "missing", _("Missing Part")  # Дутуу
    OTHER = "other", _("Other")  # Бусад


class DefectVerdict(models.TextChoices):
    OK = "ok", _("OK")  # Тэнцсэн
    REPAIR_SOON = "repair_soon", _("Repair Soon")  # Төлөвлөгөөт засвар
    REPAIR_NOW = "repair_now", _("Repair Now")  # Яаралтай засвар
    DECOMMISSION = "decommission", _("Decommission")  # Хаасан


class MeasurementDimension(models.TextChoices):
    LENGTH = "length", _("Length")  # Урт
    WIDTH = "width", _("Width")  # Өргөн
    DEPTH = "depth", _("Depth")  # Гүн
    DIAMETER = "diameter", _("Diameter")  # Диаметр
    THICKNESS = "thickness", _("Thickness")  # Зузаан
    GAP = "gap", _("Gap")  # Зай
    ANGLE = "angle", _("Angle")  # Өнцөг
    OTHER = "other", _("Other")  # Бусад
