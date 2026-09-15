"""Diagrammauswahl: Versionstreue, Speichergrenze und bestehender Mandantenschutz."""

import os

import pytest
from platform_app.data.visualization import spread_indices
from test_data_integration import finish as finish_legacy
from test_data_integration import upload as upload_legacy
from test_database_integration import client_for
from test_database_integration import stack as database_stack  # noqa: F401
from test_large_data_integration import finish, upload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("database_stack"),
    pytest.mark.skipif(
        os.environ.get("RUN_DB_TESTS") != "1", reason="Echte PostgreSQL-Testdatenbank erforderlich"
    ),
]


@pytest.mark.parametrize("stream", [False, True])
def test_chart_sample_bounds_values_version_and_tenant(stream):
    source = ("X;Y\n" + "".join(f"{i};{i * 2}\n" for i in range(1000))).encode()
    with client_for("analyst") as client:
        if stream:
            _, job = upload(client, source)
            result = finish(client, job)
        else:
            job = upload_legacy(client, source)
            result = finish_legacy(client, job)
        assert result["status"] == "SUCCEEDED", result
        path = f"/api/v1/datasets/{job['dataset_id']}/versions/1/chart-sample"
        response = client.get(path + "?x=0&y=1")
        assert response.status_code == 200, response.text
        sample = response.json()
        assert sample["method"] == "systematic-chunks-v1"
        assert sample["total_rows"] == 1000 and len(sample["rows"]) == 300
        assert sample["rows"][0] == {"row_number": 1, "values": ["0", "0"]}
        assert sample["rows"][-1] == {"row_number": 1000, "values": ["999", "1998"]}
        assert sample["content_hash"] == result["result_hash"]
        assert sample == client.get(path + "?x=0&y=1").json()
        assert all(int(row["values"][1]) == 2 * int(row["values"][0]) for row in sample["rows"])
        assert client.get(path + "?x=2").status_code == 422
        assert client.get(path + "?x=-1").status_code == 422
        with client_for("viewer") as reader:
            assert reader.get(path).status_code == 200
        with client_for("mandant-b") as other:
            assert other.get(path).status_code == 404


def test_small_chart_sample_complete_and_bounded_text():
    with client_for("analyst") as client:
        _, job = upload(client, ("A;B\n" + "a" * 600 + ";2\n").encode())
        assert finish(client, job)["status"] == "SUCCEEDED"
        sample = client.get(
            f"/api/v1/datasets/{job['dataset_id']}/versions/1/chart-sample?x=0&y=1"
        ).json()
        assert sample["method"] == "complete"
        assert sample["rows"] == [{"row_number": 1, "values": ["a" * 512, "2"]}]
        assert sample["truncated_cells"] == 1


def test_selection_covers_file_without_exceeding_budget():
    assert spread_indices(0, 12) == []
    assert spread_indices(1, 12) == [0]
    assert spread_indices(3, 12) == [0, 1, 2]
    positions = spread_indices(4096, 12)
    assert len(positions) == len(set(positions)) == 12
    assert positions[0] == 0 and positions[-1] == 4095


def test_detail_holds_parent_until_versions_and_jobs_are_read(monkeypatch):
    from uuid import UUID

    from platform_app.data import router
    from platform_app.data.models import Dataset
    from platform_app.shared.db import tenant_session
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    original = router.dataset_for
    attempted = []

    def concurrent_publication(db, dataset_id, **kwargs):
        dataset = original(db, dataset_id, **kwargs)
        # Eine zweite echte Transaktion kann den Kopf nicht mitten im Abruf
        # veröffentlichen; normale parallele Leser bleiben möglich.
        with (
            pytest.raises(DBAPIError),
            tenant_session(UUID("10000000-0000-4000-8000-000000000001")) as other,
        ):
            other.scalar(
                select(Dataset).where(Dataset.id == dataset_id).with_for_update(nowait=True)
            )
        attempted.append(True)
        return dataset

    with client_for("analyst") as client:
        _, job = upload(client, b"X;Y\n1;2\n")
        assert finish(client, job)["status"] == "SUCCEEDED"
        monkeypatch.setattr(router, "dataset_for", concurrent_publication)
        detail = client.get(f"/api/v1/datasets/{job['dataset_id']}")
        assert detail.status_code == 200 and attempted == [True]
        data = detail.json()
        assert data["current_version"] == data["versions"][0]["version_no"] == 1
