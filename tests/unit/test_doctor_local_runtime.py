from scripts.doctor_local_runtime import build_doctor_report


def test_doctor_report_adds_frontend_to_backend_readiness(monkeypatch) -> None:
    payloads = {
        "http://api.test/health": {
            "readiness": {
                "state": "ready",
                "components": [
                    {
                        "name": "postgresql",
                        "state": "ready",
                        "reason_code": "configured",
                    }
                ],
                "config": {"app_env": "local"},
            }
        }
    }

    monkeypatch.setattr(
        "scripts.doctor_local_runtime.fetch_json",
        lambda url, timeout_seconds: payloads[url],
    )
    monkeypatch.setattr(
        "scripts.doctor_local_runtime.check_http_reachable",
        lambda url, timeout_seconds: None,
    )

    report = build_doctor_report(
        api_base_url="http://api.test",
        frontend_url="http://frontend.test",
        require_frontend=True,
    )

    assert report["state"] == "ready"
    assert [item["name"] for item in report["components"]] == [
        "postgresql",
        "frontend",
    ]
    assert report["config"] == {"app_env": "local"}
    assert report["targets"] == {
        "backend_health": "http://api.test/health",
        "frontend": "http://frontend.test/",
    }


def test_doctor_report_marks_backend_failure_and_optional_frontend_as_degraded(
    monkeypatch,
) -> None:
    def fail_backend(url, timeout_seconds):
        if url == "http://api.test/health":
            raise OSError("backend offline")
        raise OSError("frontend offline")

    monkeypatch.setattr("scripts.doctor_local_runtime.fetch_json", fail_backend)

    report = build_doctor_report(
        api_base_url="http://api.test",
        frontend_url="http://frontend.test",
    )

    assert report["state"] == "unavailable"
    assert report["components"][0]["reason_code"] == "dependency_unavailable"
    assert report["components"][1]["name"] == "frontend"
