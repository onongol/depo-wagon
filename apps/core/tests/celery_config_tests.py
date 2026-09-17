from kombu.transport.redis import Transport

from apps.ai_service.tasks.document import process_document_task
from config.settings import base


class TestBrokerTimeouts:
    def test_the_socket_timeout_outlasts_the_workers_blocking_pop(self):
        socket_timeout = base.CELERY_BROKER_TRANSPORT_OPTIONS["socket_timeout"]
        assert socket_timeout > Transport.brpop_timeout


class TestTaskTimeLimits:
    def test_the_hard_limit_leaves_room_for_the_soft_one_to_fire(self):
        assert base.CELERY_TASK_SOFT_TIME_LIMIT < base.CELERY_TASK_TIME_LIMIT

    def test_document_processing_is_allowed_to_outlive_the_global_limit(self):
        assert process_document_task.soft_time_limit > base.CELERY_TASK_SOFT_TIME_LIMIT
        assert process_document_task.time_limit > process_document_task.soft_time_limit
