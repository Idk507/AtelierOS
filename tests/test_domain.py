"""Deterministic design invariants, independent of HTTP and database."""

import pytest

from packages.domain.design import Component, Design, DomainError, Patch, apply_patch, content_hash


def design() -> Design:
    return Design(
        components=[
            Component(id="bodice", kind="bodice"),
            Component(id="neckline", parent_id="bodice", kind="neckline", locked=True),
            Component(id="sleeve", kind="sleeve", geometry=[0, 0, 100, 140]),
        ]
    )


def test_selected_edit_preserves_locked_component_and_input() -> None:
    source = design()
    changed = apply_patch(
        source,
        [Patch(op="update", target_component_id="sleeve", payload={"geometry": [0, 0, 80, 140]})],
    )
    assert changed.components[1] == source.components[1]
    assert changed.components[2].geometry == [0, 0, 80, 140]
    assert source.components[2].geometry == [0, 0, 100, 140]
    assert content_hash(changed) != content_hash(source)


@pytest.mark.parametrize(
    "target,payload",
    [
        ("neckline", {"geometry": [9]}),
        ("bodice", {"geometry": [9]}),
        ("sleeve", {"parent_id": "neckline"}),
        ("neckline", {"locked": False}),
    ],
)
def test_direct_indirect_and_unlock_edits_rejected(target: str, payload: dict) -> None:
    with pytest.raises(DomainError):
        apply_patch(design(), [Patch(op="update", target_component_id=target, payload=payload)])


def test_ancestor_delete_and_parent_cycle_rejected() -> None:
    with pytest.raises(DomainError):
        apply_patch(design(), [Patch(op="delete", target_component_id="bodice", payload={})])
    with pytest.raises(DomainError):
        apply_patch(
            design(),
            [Patch(op="update", target_component_id="bodice", payload={"parent_id": "bodice"})],
        )


def test_hash_is_key_order_independent() -> None:
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})
    assert content_hash({"a": 1, "b": 2}) == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


def test_grouping_reparent_and_layer_order_are_reversible() -> None:
    source = Design(
        components=[Component(id="one", kind="sleeve"), Component(id="two", kind="sleeve")]
    )
    assert source.components[0].layer_order == "a0"
    grouped = apply_patch(
        source,
        [
            Patch(
                op="create",
                target_component_id="group",
                payload={"kind": "group", "layer_order": "a0"},
            ),
            Patch(op="update", target_component_id="one", payload={"parent_id": "group"}),
            Patch(op="update", target_component_id="two", payload={"parent_id": "group"}),
        ],
    )
    assert grouped.components[0].parent_id == "group"
    restored = apply_patch(
        grouped,
        [
            Patch(op="update", target_component_id="one", payload={"parent_id": None}),
            Patch(op="update", target_component_id="two", payload={"parent_id": None}),
            Patch(op="delete", target_component_id="group", payload={}),
        ],
    )
    assert restored == source
