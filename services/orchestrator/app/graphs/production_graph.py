from pydantic import BaseModel


class ProductionGraphState(BaseModel):
    task_id: str
    project_id: str
    stage: str = "planning"
