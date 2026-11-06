"""The template is generated from the distribution list, so it has to hold
up for a recall with more consignees than anyone would type by hand."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML is only needed by the generator")

REPO = Path(__file__).resolve().parent.parent
GENERATOR = REPO / "scripts" / "generate_template.py"


def generate(tmp_path: Path, consignees: dict[str, int]) -> dict:
    state = tmp_path / "state"
    out = tmp_path / "generated.template.yaml"

    for name, units in consignees.items():
        subprocess.run(
            [
                sys.executable, "-m", "closeout.cli", "--root", str(state),
                "ship", "--recall", "F-TEST-1",
                "--consignee", name, "--units", str(units),
            ],
            cwd=REPO, check=True, capture_output=True,
        )

    subprocess.run(
        [
            sys.executable, str(GENERATOR),
            "--recall", "F-TEST-1", "--product", "a product, a hazard",
            "--root", str(state), "--out", str(out),
            "--project-dir", "/somewhere/closeout",
        ],
        cwd=REPO, check=True, capture_output=True,
    )
    return yaml.safe_load(out.read_text())


def test_one_room_and_one_liaison_per_consignee(tmp_path):
    doc = generate(tmp_path, {f"Consignee {i}": 100 + i for i in range(12)})

    # 12 consignee rooms plus the master room.
    assert len(doc["rooms"]) == 13
    # 12 liaisons plus the registrar.
    assert len(doc["agents"]) == 13
    assert len(doc["links"]) == 12


def test_every_link_points_inward_to_the_master_room(tmp_path):
    """A link outward would disclose the consignee list to every consignee."""
    doc = generate(tmp_path, {"Alpha Foods": 10, "Beta Stores": 20})

    for link in doc["links"]:
        assert link["to"] == "recall-{recall}"
        assert link["from"] != "recall-{recall}"


def test_the_registrar_is_in_the_master_room_and_no_other(tmp_path):
    """Its isolation is the whole security claim, so it is worth asserting."""
    doc = generate(tmp_path, {"Alpha Foods": 10, "Beta Stores": 20})

    rooms = {r["name"]: r.get("agents", []) for r in doc["rooms"]}
    registrar = "{recall}-registrar"

    assert registrar in rooms["recall-{recall}"]
    for name, agents in rooms.items():
        if name != "recall-{recall}":
            assert registrar not in agents


def test_each_liaison_is_in_exactly_one_consignee_room(tmp_path):
    doc = generate(tmp_path, {"Alpha Foods": 10, "Beta Stores": 20})

    consignee_rooms = [
        r for r in doc["rooms"] if r["name"] != "recall-{recall}"
    ]
    for room in consignee_rooms:
        assert len(room["agents"]) == 1

    seen = [room["agents"][0] for room in consignee_rooms]
    assert len(seen) == len(set(seen))


def test_the_regulatory_role_is_exclusive(tmp_path):
    doc = generate(tmp_path, {"Alpha Foods": 10})

    roles = {r["name"]: r for r in doc["rooms"][0]["roles"]}
    assert roles["regulatory"]["exclusive"] is True
    assert roles["comms"]["exclusive"] is False


def test_the_shipment_total_in_the_room_doc_matches_the_list(tmp_path):
    doc = generate(tmp_path, {"Alpha Foods": 1234, "Beta Stores": 766})

    content = doc["rooms"][0]["docs"][0]["content"]
    assert "2000 units went out, to 2 consignees" in content
    assert "Alpha Foods: 1234 units" in content


def test_colliding_slugs_are_refused_rather_than_silently_merged(tmp_path):
    """"Alpha Foods" and "alpha-foods" would share a room otherwise."""
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        generate(tmp_path, {"Alpha Foods": 10, "alpha foods": 20})

    assert b"share the slug" in excinfo.value.stderr


def test_generating_with_no_shipments_refuses(tmp_path):
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        generate(tmp_path, {})

    assert b"No shipments on record" in excinfo.value.stderr
