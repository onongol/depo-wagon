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
    CRITICAL = "critical", "Шүүмжлэлт"


class DefectStatus(models.TextChoices):
    OPEN = "open", "Нээлттэй"
    IN_PROGRESS = "in_progress", "Хийгдэж байна"
    RESOLVED = "resolved", "Шийдвэрлэсэн"
    CLOSED = "closed", "Хаасан"
