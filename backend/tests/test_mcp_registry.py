from app.mcp_tools.registry import registry


def test_registry_has_eighteen_tools() -> None:
    assert registry.count() == 18


def test_registry_tool_names_are_stable() -> None:
    assert registry.names() == [
        "extract_audio",
        "separate_sources",
        "transcribe_audio",
        "analyze_harmony",
        "generate_mask",
        "correct_midi",
        "validate_corrections",
        "prepare_lesson",
        "run_tracer_bullet",
        "run_audio_to_analysis",
        "list_pipeline_runs",
        "get_pipeline_run",
        "list_metrics",
        "get_metrics_for_run",
        "list_correction_runs",
        "get_correction_run",
        "separate_lass",
        "practice_coach",
    ]


def test_all_tools_have_valid_contracts() -> None:
    contracts = registry.list_contracts()

    for contract in contracts:
        assert contract.name
        assert contract.description
        assert contract.version == "0.1.0"
        assert contract.input_schema["type"] == "object"
        assert contract.output_schema["type"] == "object"


def test_gpu_tools_are_explicit() -> None:
    gpu_tools = {contract.name for contract in registry.list_contracts() if contract.uses_gpu}

    assert gpu_tools == {
        "separate_sources",
        "prepare_lesson",
        "run_audio_to_analysis",
        "separate_lass",
    }


def test_separate_lass_is_experimental() -> None:
    tool = registry.get("separate_lass")
    assert tool.contract.status == "experimental"
