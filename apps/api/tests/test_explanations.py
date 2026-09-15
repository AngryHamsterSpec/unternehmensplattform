import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from platform_app.decisions import demo_scenario, evaluate
from platform_app.decisions.schemas import AssessmentOptions, ScenarioInput
from platform_app.explanations.provider import (
    ExplanationText,
    OpenAIExplanationProvider,
    check_payload,
    minimized_payload,
    reservation,
    validate_output,
)
from platform_app.shared.config import AppSettings


def settings():
    return AppSettings(
        _env_file=None,
        oidc_client_secret="x" * 32,
        session_secret="y" * 40,
        oidc_encryption_key=Fernet.generate_key().decode(),
        openai_input_per_million="1.25",
        openai_output_per_million="10",
        openai_model="explicit-test-model",
        openai_api_key="unit-test-only",
    )


def payload():
    scenario = ScenarioInput.model_validate(demo_scenario())
    result = evaluate(scenario, AssessmentOptions()).model_dump(mode="json")
    return minimized_payload(result)


def test_projection_removes_names_and_free_text():
    data = payload()
    encoded = check_payload(data)
    assert "Musterwerk" not in encoded
    assert "office" not in encoded
    assert "company_profile" not in data
    assert data["synthetic_prices"]


def test_unknown_evidence_and_overlong_input_fail():
    data = payload()
    with pytest.raises(ValueError, match="unverified_evidence"):
        validate_output(ExplanationText(summary="Text", evidence_ids=["invented"]), data)
    with pytest.raises(ValueError, match="input_limit"):
        check_payload({"text": "x" * 8001})


def test_budget_reserves_full_input_and_output_cap():
    assert reservation(settings()) == Decimal("0.02200000")


def test_provider_has_no_tools_no_storage_and_no_retry():
    data = payload()
    evidence = data["candidates"][0]["evidence_ids"]
    output = ExplanationText(summary="Synthetische Modellrechnung.", evidence_ids=evidence)
    response = SimpleNamespace(status="completed", output_parsed=output)
    client = MagicMock()
    client.responses.parse = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    with patch("platform_app.explanations.provider.AsyncOpenAI", return_value=client) as factory:
        result = asyncio.run(OpenAIExplanationProvider(settings()).explain(data))
    assert result == output
    assert factory.call_args.kwargs["max_retries"] == 0
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["tools"] == []
    assert kwargs["store"] is False
    assert kwargs["max_output_tokens"] == 1200
    assert kwargs["model"] == "explicit-test-model"
    assert client.responses.parse.await_count == 1


def test_provider_refusal_does_not_become_success():
    client = MagicMock()
    client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(status="completed", output_parsed=None)
    )
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    with patch("platform_app.explanations.provider.AsyncOpenAI", return_value=client):
        with pytest.raises(ValueError, match="provider_incomplete"):
            asyncio.run(OpenAIExplanationProvider(settings()).explain(payload()))
