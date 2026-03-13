from celery import Celery

app = Celery(
    "worker_render",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
)
