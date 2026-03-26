"""Celery app for async workflow execution (worker service)."""

from __future__ import annotations

from celery import Celery

from agentos.config import settings

celery_app = Celery(
    "agentos",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)


@celery_app.task(name="agentos.execute_workflow")
def execute_workflow(workflow_path: str) -> str:
    """Enqueue a workflow run on the worker."""
    from agentos.runtime.workflow_runner import WorkflowRunner

    return WorkflowRunner().start_run(workflow_path)
