from pydantic import BaseModel
from typing import Optional, Dict, Any


class ProjectEstimateSummaryResponse(BaseModel):
    """
    Response schema for project estimate summary.
    
    Returns module totals and grand total for a project.
    Missing modules are represented as null or 0.
    """
    project_name: str
    modules: Dict[str, Optional[float]]  # {"hrs_estimator": 12500.0, "lab": 4300.0, "logistics": 2100.0}
    grand_total: float
    
    class Config:
        from_attributes = True

