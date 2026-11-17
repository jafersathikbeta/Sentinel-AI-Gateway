"""Pydantic models for agent actions validated by the Sentinel gateway."""

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"


class AgentAction(BaseModel):
    """Canonical action envelope submitted by agents for gateway validation."""

    agent_id: str = Field(..., min_length=1, description="Unique identifier of the requesting agent")
    action_type: ActionType = Field(..., description="Category of the requested operation")
    target: str = Field(..., min_length=1, description="Resource, path, command, or endpoint targeted")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Optional action parameters")
