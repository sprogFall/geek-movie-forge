from celery import Celery

app = Celery(
    "worker_text",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
)
