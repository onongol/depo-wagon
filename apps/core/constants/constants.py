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
    WORKER = "worker", _("Worker")
    INSPECTOR = "inspector", _("Inspector")  # Дефектоскопист
    MASTER = "master", _("Master")
    ENGINEER = "engineer", _("Engineer")
    MANAGER = "manager", _("Manager")


class Department(models.TextChoices):
    COUPLER_BRAKE = "coupler_brake", _("Coupler and Brake")  # Автомат холбоос, тоормос
    REPAIR_1 = "repair_1", _("Repair-1")  # Засвар-1
    REPAIR_2 = "repair_2", _("Repair-2")  # Засвар-2
    PREPARATION = "preparation", _("Preparation for Repair")  # Засварын бэлтгэл
    MECHANIC = "mechanic", _("Mechanic")  # Механик
    BOGIE = "bogie", _("Bogie")  # Тэрэгцэр
    WHEELSET = "wheelset", _("Wheelset")  # Хос дугуй
    WHEEL_SHOP = "wheel_shop", _("Wheel Shop")  # Дугуйн цех (ВКМ)
    OTHER = "other", _("Other")
