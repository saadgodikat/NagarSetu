from pydantic import BaseModel


class StatusMetric(BaseModel):
    status: str
    count: int


class DepartmentWorkloadMetric(BaseModel):
    department_id: int | None
    department_name: str
    total: int
    open: int
    overdue: int


class WardDistributionMetric(BaseModel):
    ward_id: int | None
    ward_name: str
    zone_id: int | None
    total: int


class EmergingIssueMetric(BaseModel):
    category: str
    count: int
    open_count: int


class AnalyticsSummaryOut(BaseModel):
    generated_at: str
    total_complaints: int
    open_complaints: int
    critical_complaints: int
    overdue_complaints: int
    unassigned_complaints: int
    resolution_rate: float
    average_resolution_hours: float | None
    status_breakdown: dict[str, int]
    department_workload: list[DepartmentWorkloadMetric]
    ward_distribution: list[WardDistributionMetric]
    emerging_issues: list[EmergingIssueMetric]
