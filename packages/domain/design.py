"""Pure garment snapshot validation, hashing and lock-preserving edits."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]
Coordinate = Annotated[int, Field(strict=True, ge=-1_000_000, le=1_000_000)]


class DomainError(Exception):
    """A safe, machine-readable domain rejection."""

    def __init__(self, code: str, status: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class StrictModel(BaseModel):
    """Reject undeclared input so authorization fields cannot be smuggled in."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Component(StrictModel):
    """A stable semantic node in the canonical revision snapshot."""

    id: Identifier
    kind: Identifier
    parent_id: Identifier | None = None
    geometry: list[Coordinate] = Field(default_factory=list, max_length=20_000)
    locked: bool = False
    layer_order: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z][0-9A-Za-z]+$")


class Design(StrictModel):
    """Bounded semantic snapshot, separate from raster assets and approvals."""

    components: list[Component] = Field(min_length=1, max_length=500)
    material_id: Identifier | None = None

    @model_validator(mode="after")
    def valid_tree(self, info: ValidationInfo) -> Design:
        """Reject duplicate, dangling and cyclic parent references."""
        nodes = {c.id: c for c in self.components}
        if len(nodes) != len(self.components):
            raise ValueError("duplicate_component")
        pairs = [(c.parent_id, c.layer_order) for c in self.components if c.layer_order is not None]
        if not (info.context or {}).get("defer_layers") and len(set(pairs)) != len(pairs):
            raise ValueError("duplicate_layer_order")
        used = set(pairs)
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        for component in self.components:
            candidate = 0
            while component.layer_order is None:
                layer = (
                    "a" + alphabet[candidate]
                    if candidate < 62
                    else "b" + alphabet[(candidate - 62) // 62] + alphabet[(candidate - 62) % 62]
                )
                candidate += 1
                if (component.parent_id, layer) not in used:
                    component.layer_order = layer
                    used.add((component.parent_id, layer))
            key = component.layer_order
            length = ord(key[0]) - ord("a") + 2 if key[0].islower() else ord("Z") - ord(key[0]) + 2
            if len(key) < length or (len(key) > length and key.endswith("0")):
                raise ValueError("invalid_layer_order")
            if len(component.geometry) % 2:
                raise ValueError("geometry_requires_coordinate_pairs")
        for component in self.components:
            visited = {component.id}
            parent = component.parent_id
            while parent is not None:
                if parent not in nodes or parent in visited:
                    raise ValueError("invalid_component_tree")
                visited.add(parent)
                parent = nodes[parent].parent_id
        return self


class Patch(StrictModel):
    """P01 supports create/update/delete; broader geometry tools come in P02."""

    op: Literal["create", "update", "delete"]
    target_component_id: Identifier
    payload: dict[str, Any]


def content_hash(value: BaseModel | dict[str, Any]) -> str:
    """Hash canonical UTF-8 JSON; no timestamps, NaN or platform whitespace."""
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise DomainError("invalid_payload", 422) from exc
    return hashlib.sha256(encoded).hexdigest()


def protected_ids(design: Design) -> set[str]:
    """A locked child also protects its ancestors against indirect changes."""
    nodes = {c.id: c for c in design.components}
    protected: set[str] = set()
    for component in design.components:
        if component.locked:
            current: str | None = component.id
            while current:
                protected.add(current)
                current = nodes[current].parent_id
    return protected


def apply_patch(source: Design, operations: list[Patch]) -> Design:
    """Apply a bounded proposal to a copy; no operation can unlock components."""
    result = source.model_copy(deep=True)
    try:
        for operation in operations:
            target = operation.target_component_id
            nodes = {c.id: c for c in result.components}
            protected = protected_ids(result)
            if target in protected:
                raise DomainError("locked_component")
            if operation.op == "create":
                if target in nodes:
                    raise DomainError("duplicate_component", 422)
                component = Component.model_validate({**operation.payload, "id": target})
                if component.parent_id in protected:
                    raise DomainError("locked_component")
                result.components.append(component)
            elif target == "garment" and operation.op == "update":
                if set(operation.payload) != {"material_id"}:
                    raise DomainError("invalid_patch", 422)
                result.material_id = operation.payload["material_id"]
            elif target not in nodes:
                raise DomainError("unknown_component", 422)
            elif operation.op == "delete":
                if operation.payload:
                    raise DomainError("invalid_patch", 422)
                remove = {target}
                while True:
                    children = {c.id for c in result.components if c.parent_id in remove}
                    if children <= remove:
                        break
                    remove |= children
                result.components = [c for c in result.components if c.id not in remove]
            else:
                if not operation.payload or not set(operation.payload) <= {
                    "geometry",
                    "parent_id",
                    "kind",
                    "layer_order",
                }:
                    raise DomainError("invalid_patch", 422)
                if operation.payload.get("parent_id") in protected:
                    raise DomainError("locked_component")
                replacement = Component.model_validate(
                    {**nodes[target].model_dump(), **operation.payload}
                )
                result.components = [
                    replacement if c.id == target else c for c in result.components
                ]
            result = Design.model_validate(result.model_dump(), context={"defer_layers": True})
        result = Design.model_validate(result.model_dump())
    except ValidationError as exc:
        raise DomainError("invalid_patch", 422) from exc
    return result
