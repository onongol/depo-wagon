from django.db import models
from django.utils.translation import gettext_lazy as _


class WagonType(models.TextChoices):
    GONDOLA_CAR = "gondola", _("Gondola Car")  # Хагас
    CONTAINER = "container", _("Container")  # Чингэлэг
    FLATCAR = "flatcar", _("Flatcar")  # Тавцант
    BOXCAR = "boxcar", _("Boxcar")  # Битүү
    HOPPER = "hopper", _("Hopper")  # Хоппер
    CISTERN = "cistern", _("Cistern")  # Цистерн
    DUMP_CAR = "dumpcar", _("Dump Car")  # Думпкар
    DOSER = "doser", _("Doser")  # Дозатор
    SPECIAL = "special", _("Special Purpose")  # Тусгай зориулалтын


class WagonStatus(models.TextChoices):
    ARRIVED = "arrived", _("Arrived")  # Ирсэн
    INSPECTION = "inspection", _("Inspection")  # Үзлэгт
    WAITING_REPAIR = "waiting", _("Waiting for Repair")  # Засвар хүлээж
    REPAIR = "repair", _("Under Repair")  # Засварт
    READY = "ready", _("Ready")  # Бэлэн
    ACTIVE = "active", _("In Service")  # Ашиглалтад
    DECOMMISSIONED = "decommissioned", _("Decommissioned")  # Хассан


class RepairType(models.TextChoices):
    DEPO = "depo", _("Depot")  # Депо
    CURRENT = "current", _("Current")  # Урсгал
    MAJOR = "major", _("Major")  # Их


class EmployeeRole(models.TextChoices):
    INSPECTOR = "inspector", _("Inspector")  # Дефектоскопист
    MASTER = "master", _("Master")  # Мастер
    ENGINEER = "engineer", _("Engineer")  # Инженер
    MANAGER = "manager", _("Manager")  # Менежер
