"""Validated contracts shared by ReliefGrid AI orchestration workflows."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class SchemaModel(BaseModel):
    """Base model that rejects misspelled or unexpected operational fields."""

    model_config = ConfigDict(extra="forbid")


Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Priority = Annotated[StrictInt, Field(ge=1, le=5)]
Severity = Annotated[StrictInt, Field(ge=1, le=5)]
PositiveCapacity = Annotated[float, Field(gt=0)]


class ConvoyStatus(str, Enum):
    STAGING = "STAGING"
    EN_ROUTE = "EN_ROUTE"
    DELIVERING = "DELIVERING"
    EVACUATING = "EVACUATING"
    BLOCKED = "BLOCKED"


class RequestType(str, Enum):
    MEDICAL = "MEDICAL"
    EVACUATION = "EVACUATION"
    SUPPLY = "SUPPLY"


class RequestStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class HazardType(str, Enum):
    FLOOD = "FLOOD"
    COLLAPSE = "COLLAPSE"
    BLOCKED_ROAD = "BLOCKED_ROAD"


class ActionType(str, Enum):
    ASSIGN = "ASSIGN"
    REROUTE = "REROUTE"
    HOLD = "HOLD"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Coordinate(SchemaModel):
    lat: Latitude
    lon: Longitude


class Convoy(SchemaModel):
    convoy_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: Latitude
    lon: Longitude
    status: ConvoyStatus
    capacity: PositiveCapacity
    current_request_id: str | None = None


class ReliefRequest(SchemaModel):
    request_id: str = Field(min_length=1)
    type: RequestType
    lat: Latitude
    lon: Longitude
    priority: Priority
    status: RequestStatus
    population_affected: int = Field(ge=0)


class Hazard(SchemaModel):
    hazard_id: str = Field(min_length=1)
    edge_ids: list[str] = Field(min_length=1)
    type: HazardType
    severity: Severity


class OperationalState(SchemaModel):
    scenario_id: str = Field(min_length=1)
    timestamp: datetime
    convoys: list[Convoy] = Field(default_factory=list)
    requests: list[ReliefRequest] = Field(default_factory=list)
    hazards: list[Hazard] = Field(default_factory=list)


class ObjectiveAction(SchemaModel):
    target_convoy_id: str = Field(min_length=1)
    action_type: ActionType
    target_request_id: str | None = None
    priority_score: Priority
    rationale: str = Field(min_length=1)


class ObjectiveCommand(SchemaModel):
    command_id: str = Field(min_length=1)
    raw_input_text: str = Field(min_length=1)
    interpreted_actions: list[ObjectiveAction] = Field(default_factory=list)


class HighestRiskArea(Coordinate):
    description: str = Field(min_length=1)


class ConvoyAssignment(SchemaModel):
    convoy_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class PredictedBottleneck(SchemaModel):
    location: str = Field(min_length=1)
    description: str = Field(min_length=1)


class MissionBriefing(SchemaModel):
    briefing_id: str = Field(min_length=1)
    timestamp: datetime
    crisis_assessment: str = Field(min_length=1)
    highest_risk_areas: list[HighestRiskArea] = Field(default_factory=list)
    convoy_assignments: list[ConvoyAssignment] = Field(default_factory=list)
    predicted_bottlenecks: list[PredictedBottleneck] = Field(default_factory=list)
    confidence_level: ConfidenceLevel
    backup_plan: str = Field(min_length=1)


class RouteResponse(SchemaModel):
    convoy_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    origin_node: int
    destination_node: int
    node_ids: list[int] = Field(min_length=1)
    edge_ids: list[str] = Field(default_factory=list)
    geometry: list[Coordinate] = Field(min_length=1)
    distance_meters: float = Field(ge=0)
    estimated_seconds: float = Field(ge=0)


class ReasoningLogEntry(SchemaModel):
    timestamp: datetime
    message: str = Field(min_length=1)
    level: str = Field(default="INFO", min_length=1)


class ObjectivePlanRequest(SchemaModel):
    objective: str = Field(min_length=1, max_length=4_000)


class PlanningResponse(SchemaModel):
    command: ObjectiveCommand
    routes: list[RouteResponse] = Field(default_factory=list)
    briefing: MissionBriefing
    reasoning_log: list[ReasoningLogEntry] = Field(default_factory=list)
    state: OperationalState


class DisruptionReplan(SchemaModel):
    """Validated LLM output for a plan revised after an operational disruption."""

    command: ObjectiveCommand
    briefing: MissionBriefing
    change_summary: str = Field(min_length=1)


class OperationalQueryRequest(SchemaModel):
    """A coordinator's natural-language query about live state."""

    question: str = Field(min_length=1)


class OperationalQueryResponse(SchemaModel):
    """A state-grounded answer to a coordinator's operational question."""

    answer: str = Field(min_length=1)


class DisruptionEventRequest(SchemaModel):
    hazard_id: str = Field(min_length=1)
    edge_ids: list[str] = Field(min_length=1)
    type: HazardType
    severity: Severity
    description: str = Field(min_length=1)


class WeatherData(SchemaModel):
    """Real-time weather parameters for the demo region."""

    temperature: float
    weathercode: int
    windspeed: float
    description: str


class GDACSAlert(SchemaModel):
    """A live disaster alert fetched from GDACS RSS."""

    title: str
    description: str
    link: str | None = None
