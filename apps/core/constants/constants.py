from django.db import models


class WagonType(models.TextChoices):
    GONDOLA_CAR = "gondola", "Хагас"
    CONTAINER = "container", "Чингэлэг"
    FLATCAR = "flatcar", "Тавцант"
    BOXCAR = "boxcar", "Битүү"
    HOPPER = "hopper", "Хоппер"
    CISTERN = "cistern", "Цистерн"
    DUMP_CAR = "dumpcar", "Думпкар"
    DOSER = "doser", "Дозатор"
    SPECIAL = "special", "Тусгай хэрэгцээний"


class WagonStatus(models.TextChoices):
    ARRIVED = "arrived", "Ирсэн"
    INSPECTION = "inspection", "Үзлэгт"
    WAITING_REPAIR = "waiting", "Засвар хүлээж"
    REPAIR = "repair", "Засварт"
    READY = "ready", "Бэлэн"
    ACTIVE = "active", "Ашиглалтад"
    DECOMMISSIONED = "decommissioned", "Хассан"


class RepairType(models.TextChoices):
    DEPO = "depo", "Депо"
    CURRENT = "current", "Урсгал"
    MAJOR = "major", "Их засвар"


class EmployeeRole(models.TextChoices):
    INSPECTOR = "inspector", "Дефектоскопист"
    MASTER = "master", "Мастер"
    ENGINEER = "engineer", "Инженер"
    MANAGER = "manager", "Менежер"


class DefectSeverity(models.TextChoices):
    LOW = "low", "Бага"
    MEDIUM = "medium", "Дунд"
    HIGH = "high", "Өндөр"
    CRITICAL = "critical", "Онц Ноцтой"


class DefectStatus(models.TextChoices):
    OPEN = "open", "Илэрсэн"
    IN_PROGRESS = "in_progress", "Хийгдэж байна"
    RESOLVED = "resolved", "Шийдвэрлэсэн"
    CLOSED = "closed", "Хаасан"


class DefectNode(models.TextChoices):
    BODY = "body", "Их бие"
    FRAME = "frame", "Арал"
    BOGIE = "bogie", "Тэрэгцэр"
    WHEELSET = "wheelset", "Хос дугуйн"
    BEARING = "bearing", "Гүүшин"
    BRAKE = "brake", "Тоормосны систем"
    COUPLER = "coupler", "Ниших татах төхөөрөмж"
    OTHER = "other", "Бусад"


class DefectType(models.TextChoices):
    CRACK = "crack", "Ан цав"
    WEAR = "wear", "Элэгдэл"
    DEFORMATION = "deformation", "Хэв гажилт"
    FRACTURE = "fracture", "Хугарал"
    DESTRUCTION = "destruction", "Эвдрэл"
    CORROSION = "corrosion", "Зэврэлт"
    THREAD_STRIP = "thread_strip", "Эрээс гарах"
    LEAK = "leak", "Шүүрэлт"
    LOOSE = "loose", "Бэхэлгээ сулрах"
    MISSING = "missing", "Дутуу"
    OTHER = "other", "Бусад"


class DefectVerdict(models.TextChoices):
    OK = "ok", "Тэнцсэн"
    REPAIR_SOON = "repair_soon", "Төлөвлөгөөт"
    REPAIR_NOW = "repair_now", "Яаралтай"
    DECOMMISSION = "decommission", "Хассан"


class MeasurementDimension(models.TextChoices):
    LENGTH = "length", "Урт"
    WIDTH = "width", "Өргөн"
    DEPTH = "depth", "Гүн"
    DIAMETER = "diameter", "Диаметр"
    THICKNESS = "thickness", "Зузаан"
    GAP = "gap", "Зай"
    ANGLE = "angle", "Өнцөг"
    OTHER = "other", "Бусад"
