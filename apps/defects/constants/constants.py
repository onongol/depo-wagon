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

    WHEEL = "wheel", _("Wheel")  # Дугуй
    AXLE = "axle", _("Axle")  # Гол
    BEARING = "bearing", _("Bearing")  # Гүүшин

    BOGIE = "bogie", _("Bogie")  # Тэргэнцэр
    WHEELSET = "wheelset", _("Wheelset")  # Хос дугуй
    SIDE_FRAMES = "side_frames", _("Side Frames")  # Боковые рамы
    BOLSTER = "bolster", _("Bolster")  # Надрессорная балка
    SPRING_NEST = "spring_nest", _("Spring Nest")  # Рессорное подвешивание
    BRAKE_RIGGING = "brake_rigging", _("Brake Rigging")  # Тормозная рычажная передача

    BRAKE = "brake", _("Brake System")  # Тоормосны систем
    BRAKE_PIPE = "brake_pipe", _("Brake Pipe")  # Тормозная магистраль
    CONTROL_VALVE = "control_valve", _("Control Valve")  # Управляющий клапан
    AUXILIARY_RESERVOIR = (
        "auxiliary_reservoir",
        _("Auxiliary Reservoir"),
    )  # Вспомогательный резервуар
    EMPTY_LOAD_DEVICE = (
        "empty_load_device",
        _("Empty-Load Device"),
    )  # Устройство для регулирования нагрузки
    BRAKE_CYLINDER = "brake_cylinder", _("Brake Cylinder")  # Тормозной цилиндр
    PARKING_BRAKE = "parking_brake", _("Parking Brake")  # Стояночный тормоз

    COUPLER = "coupler", _("Coupler")  # Корпус автосцепки
    COUPLER_BODY = "coupler_body", _("Coupler Body")  # Механизм сцепления
    COUPLER_MECHANISM = (
        "coupler_mechanism",
        _("Coupler Mechanism"),
    )  # Упряжное устройство
    DRAFT_GEAR_ASSEMBLY = (
        "draft_gear_assembly",
        _("Draft Gear Assembly"),
    )  # Ударно-центрирующий прибор
    UNCOUPLING_LEVER = "uncoupling_lever", _("Uncoupling Lever")  # Расцепной привод

    STANDARD = "standard", _("Standard")  # Стандарт
    CUSTOM = "custom", _("Custom")  # Захиалгат

    OTHER = "other", _("Other")  # Бусад


_REPAIR_NODES = [DefectNode.BODY, DefectNode.FRAME, DefectNode.BRAKE, DefectNode.OTHER]

DEPARTMENT_NODES = {
    "repair_1": _REPAIR_NODES,
    "repair_2": _REPAIR_NODES,
    "preparation": [DefectNode.BODY, DefectNode.FRAME, DefectNode.OTHER],
    "mechanic": [DefectNode.STANDARD, DefectNode.CUSTOM, DefectNode.OTHER],
    "coupler_brake": [
        DefectNode.COUPLER,
        DefectNode.COUPLER_BODY,
        DefectNode.COUPLER_MECHANISM,
        DefectNode.DRAFT_GEAR_ASSEMBLY,
        DefectNode.UNCOUPLING_LEVER,
        DefectNode.OTHER,
        DefectNode.BRAKE,
        DefectNode.BRAKE_PIPE,
        DefectNode.CONTROL_VALVE,
        DefectNode.AUXILIARY_RESERVOIR,
        DefectNode.EMPTY_LOAD_DEVICE,
        DefectNode.BRAKE_CYLINDER,
        DefectNode.BRAKE_RIGGING,
        DefectNode.PARKING_BRAKE,
        DefectNode.OTHER,
    ],
    "bogie": [
        DefectNode.BOGIE,
        DefectNode.WHEELSET,
        DefectNode.BEARING,
        DefectNode.SIDE_FRAMES,
        DefectNode.BOLSTER,
        DefectNode.SPRING_NEST,
        DefectNode.BRAKE_RIGGING,
        DefectNode.OTHER,
    ],
    "wheelset": [
        DefectNode.WHEEL,
        DefectNode.AXLE,
        DefectNode.BEARING,
        DefectNode.OTHER,
    ],
    "wheel_shop": [DefectNode.WHEEL, DefectNode.AXLE, DefectNode.OTHER],
    "other": [DefectNode.OTHER],
}


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
    HUMAN_FACTOR = "human_factor", _("Human Factor")  # Хүний хүчин зүйл
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


DIMENSION_UNITS = {
    MeasurementDimension.LENGTH: "mm",
    MeasurementDimension.WIDTH: "mm",
    MeasurementDimension.DEPTH: "mm",
    MeasurementDimension.DIAMETER: "mm",
    MeasurementDimension.THICKNESS: "mm",
    MeasurementDimension.GAP: "mm",
    MeasurementDimension.ANGLE: "deg",
    MeasurementDimension.OTHER: "",
}
