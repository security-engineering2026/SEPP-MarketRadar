from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping
from .taxonomy import get_task, required_task_capabilities as taxonomy_required

MATCH_FULL = "FULL_MATCH"
MATCH_PARTIAL = "PARTIAL_MATCH"
MATCH_NONE = "NO_MATCH"
MATCH_DISABLED = "PROVIDER_DISABLED"
MATCH_NO_PROVIDER = "REGISTERED_NO_PROVIDER"

STATUS_LABELS_FA = {
    MATCH_FULL: "اجرای خودکار آماده",
    MATCH_PARTIAL: "پشتیبانی ناقص",
    MATCH_NONE: "قابلیت لازم پشتیبانی نمی‌شود",
    MATCH_DISABLED: "نرم‌افزار مجری غیرفعال است",
    MATCH_NO_PROVIDER: "مجری خودکار متصل نیست؛ انجام دستی همچنان ممکن است",
}


@dataclass(frozen=True)
class Capability:
    name: str
    work_domain: str
    task_types: frozenset[str]
    operations: frozenset[str]
    input_formats: frozenset[str]
    output_formats: frozenset[str]
    qa_requirements: frozenset[str]
    automation_level: str
    qa_mode: str


@dataclass(frozen=True)
class ProviderManifest:
    provider_id: str
    name: str
    version: str
    standalone: bool
    capabilities: frozenset[str]
    enabled: bool = True
    health: str = "UNKNOWN"
    installed: bool = False
    connected: bool = False
    execution_mode: str = "LOCAL"
    endpoint: str | None = None
    connectable: bool = True
    input_contract: str = 'job.v1'
    output_contract: str = 'result.v1'
    qa_contract: str = 'qa.v1'
    authorization_scope: str = 'user_approval_required'


CAPABILITIES: dict[str, Capability] = {}
PROVIDERS: dict[str, ProviderManifest] = {}


def _cap(name, domain, tasks, ops, ins, outs, qa, automation, qa_mode):
    CAPABILITIES[name] = Capability(
        name=name,
        work_domain=domain,
        task_types=frozenset(tasks),
        operations=frozenset(ops),
        input_formats=frozenset(ins),
        output_formats=frozenset(outs),
        qa_requirements=frozenset(qa),
        automation_level=automation,
        qa_mode=qa_mode,
    )


_cap("pdf_to_word", "document_processing", ["pdf_to_word"], ["extract", "convert", "layout_preservation"], ["pdf"], ["word"], ["text_completeness", "page_count", "layout_check"], "full", "automated")
_cap("pdf_to_excel", "data_processing", ["pdf_to_excel"], ["extract", "convert", "table_extraction", "normalize"], ["pdf"], ["excel"], ["row_count", "column_integrity", "sample_value_check"], "full", "automated")
_cap("image_to_word", "document_processing", ["image_to_word"], ["ocr", "extract", "convert", "document_generation"], ["image"], ["word"], ["text_completeness", "ocr_sample_check", "layout_check"], "high", "confidence_based")
_cap("image_to_text", "document_processing", ["image_to_text"], ["ocr", "text_extraction"], ["image"], ["text"], ["text_completeness", "confidence_check"], "high", "confidence_based")
_cap("audio_to_text", "media_processing", ["audio_to_text"], ["audio_transcription", "speech_to_text", "text_cleanup"], ["audio"], ["text"], ["text_completeness", "confidence_review", "timestamp_check"], "high", "confidence_based")
_cap("translation_general", "language_services", ["translation"], ["translate", "language_normalization", "format_preservation"], ["text", "document"], ["text", "document"], ["completeness", "terminology_check", "format_check"], "high", "automated")
_cap("word_formatting", "document_processing", ["word_formatting"], ["format", "normalize", "layout_cleanup"], ["word", "doc", "docx"], ["word", "docx"], ["page_layout", "headings", "tables", "spacing"], "high", "automated")
_cap("word_to_powerpoint", "presentation", ["word_to_powerpoint"], ["extract_content", "content_structuring", "slide_generation", "layout_formatting"], ["word"], ["powerpoint"], ["slide_count", "text_overflow", "visual_consistency", "source_completeness"], "high", "automated")
_cap("pdf_to_powerpoint", "presentation", ["pdf_to_powerpoint"], ["extract_content", "content_structuring", "slide_generation", "layout_formatting"], ["pdf"], ["powerpoint"], ["slide_count", "text_overflow", "visual_consistency", "source_completeness"], "high", "automated")
_cap("excel_cleaning", "data_processing", ["excel_cleaning"], ["clean", "normalize", "deduplicate", "validate"], ["excel", "csv", "spreadsheet"], ["excel", "csv"], ["row_count", "duplicate_check", "sample_value_check"], "full", "automated")
_cap("excel_automation", "data_processing", ["excel_automation"], ["read", "transform", "calculate", "generate_report"], ["excel", "csv", "spreadsheet"], ["excel", "report"], ["row_count", "formula_check", "output_open_check"], "full", "automated")
_cap("data_entry", "data_processing", ["data_entry"], ["extract", "enter", "normalize", "validate"], ["text", "image", "pdf", "document"], ["structured_data", "excel", "csv"], ["record_count", "required_field_check", "sample_accuracy"], "high", "automated")
_cap("python_automation", "software_automation", ["python_automation", "business_automation", "data_pipeline", "api_integration"], ["analyze", "implement", "validate", "automate", "integrate", "transform"], ["source_code", "structured_data", "api", "document"], ["software_output", "report", "structured_data"], ["functional_check", "output_validation", "error_path_test"], "high", "automated")
_cap("python_debugging", "software_engineering", ["python_debugging"], ["reproduce", "diagnose", "patch", "verify"], ["source_code", "logs"], ["patched_source", "verification_report"], ["reproduction_test", "regression_test", "failure_evidence"], "high", "automated")
_cap("web_bug_bounty", "security_engineering", ["web_bug_bounty"], ["recon", "validate", "report"], ["web_target", "scope"], ["finding_report", "evidence"], ["authorization_check", "finding_validation", "evidence_integrity"], "high", "automated_plus_review")
_cap("android_bug_bounty", "security_engineering", ["android_bug_bounty"], ["recon", "analyze", "validate", "report"], ["android_target", "apk", "scope"], ["finding_report", "evidence"], ["authorization_check", "finding_validation", "evidence_integrity"], "high", "automated_plus_review")
_cap("android_development", "android", ["android_development"], ["design", "implement", "build", "test", "package"], ["requirements", "source_code"], ["apk", "aab", "source_code"], ["build_check", "install_check", "functional_check"], "high", "automated")
_cap("typing_retyping", "general_services", ["typing_retyping"], ["retype", "normalize", "format"], ["image", "pdf", "scan", "document"], ["text", "word", "structured_data"], ["sample_accuracy", "completeness"], "high", "automated")
_cap("translation_word", "language_services", ["translation_word"], ["translate", "format", "layout"], ["document", "word"], ["word"], ["completeness", "format_check", "layout_check"], "high", "automated")
_cap("translation_powerpoint", "language_services", ["translation_powerpoint"], ["translate", "slide_layout", "qa"], ["presentation", "powerpoint"], ["powerpoint"], ["completeness", "overflow_check", "visual_consistency"], "high", "automated")
_cap("word_to_pdf", "document_processing", ["word_to_pdf"], ["convert", "render", "qa"], ["word", "doc", "docx"], ["pdf"], ["page_count", "render_check"], "full", "automated")
_cap("pdf_office_conversion", "document_processing", ["pdf_office_conversion"], ["extract", "convert", "normalize"], ["pdf", "word", "excel", "powerpoint"], ["pdf", "word", "excel", "powerpoint"], ["file_open_check", "content_sample_check"], "high", "automated")
_cap("powerpoint_creation", "presentation", ["powerpoint_creation"], ["structure", "slide_generation", "layout_formatting"], ["text", "word", "pdf", "data"], ["powerpoint"], ["slide_count", "overflow_check"], "high", "automated")
_cap("powerpoint_formatting", "presentation", ["powerpoint_formatting"], ["format", "layout", "cleanup"], ["powerpoint"], ["powerpoint"], ["overflow_check", "layout_check"], "high", "automated")
_cap("excel_merge", "data_processing", ["excel_merge"], ["load", "align", "merge", "validate"], ["excel", "csv", "spreadsheet"], ["excel"], ["row_count", "column_integrity"], "full", "automated")
_cap("excel_transformation", "data_processing", ["excel_transformation"], ["transform", "normalize", "validate"], ["excel", "csv", "spreadsheet"], ["excel", "csv"], ["schema_validation", "sample_value_check"], "full", "automated")
_cap("excel_analysis", "data_processing", ["excel_analysis"], ["analyze", "calculate", "summarize"], ["excel", "csv", "spreadsheet"], ["report", "analysis"], ["sample_calculation_check", "consistency_check"], "high", "automated")
_cap("excel_dashboard", "data_presentation", ["excel_dashboard"], ["aggregate", "visualize", "report"], ["excel", "csv", "spreadsheet"], ["dashboard", "report"], ["source_to_metric_check", "render_check"], "high", "automated")
_cap("audio_to_subtitle", "media_processing", ["audio_to_subtitle"], ["transcribe", "timestamp", "format"], ["audio", "video"], ["subtitle", "text"], ["timestamp_check", "text_completeness"], "high", "confidence_based")


def get_capability(name: str) -> Capability | None:
    return CAPABILITIES.get(str(name).strip().lower())


def list_capabilities() -> list[Capability]:
    return sorted(CAPABILITIES.values(), key=lambda item: item.name)


def register_provider(provider: ProviderManifest) -> None:
    if not provider.provider_id.strip():
        raise ValueError("INVALID_PROVIDER_ID")
    unknown = set(provider.capabilities) - set(CAPABILITIES)
    if unknown:
        raise ValueError("UNKNOWN_CAPABILITIES:" + ",".join(sorted(unknown)))
    PROVIDERS[provider.provider_id] = provider


def sync_provider_registry(connection) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for provider in PROVIDERS.values():
        connection.execute(
            "INSERT INTO provider_registry(provider_id,name,version,standalone,capabilities_json,enabled,health,installed,connected,execution_mode,endpoint,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(provider_id) DO UPDATE SET name=excluded.name,version=excluded.version,standalone=excluded.standalone,capabilities_json=excluded.capabilities_json,enabled=excluded.enabled,health=excluded.health,installed=excluded.installed,connected=excluded.connected,execution_mode=excluded.execution_mode,endpoint=excluded.endpoint,updated_at=excluded.updated_at",
            (provider.provider_id, provider.name, provider.version, int(provider.standalone), json.dumps(sorted(provider.capabilities), ensure_ascii=False), int(provider.enabled), provider.health, int(provider.installed), int(provider.connected), provider.execution_mode, provider.endpoint, now),
        )
        connection.execute("INSERT INTO engine_manifests(engine_id,name,version,standalone,connectable,capabilities_json,execution_mode,health,endpoint,input_contract,output_contract,qa_contract,authorization_scope,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(engine_id) DO UPDATE SET name=excluded.name,version=excluded.version,standalone=excluded.standalone,connectable=excluded.connectable,capabilities_json=excluded.capabilities_json,execution_mode=excluded.execution_mode,health=excluded.health,endpoint=excluded.endpoint,input_contract=excluded.input_contract,output_contract=excluded.output_contract,qa_contract=excluded.qa_contract,authorization_scope=excluded.authorization_scope,updated_at=excluded.updated_at", (provider.provider_id,provider.name,provider.version,int(provider.standalone),int(provider.connectable),json.dumps(sorted(provider.capabilities),ensure_ascii=False),provider.execution_mode,provider.health,provider.endpoint,provider.input_contract,provider.output_contract,provider.qa_contract,provider.authorization_scope,now))
    connection.commit()


def clear_providers() -> None:
    PROVIDERS.clear()


def load_provider_config(path: str | Path | None) -> list[ProviderManifest]:
    clear_providers()
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("providers", [])
    else:
        items = data
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        manifest = ProviderManifest(
            provider_id=str(item["provider_id"]),
            name=str(item.get("name", item["provider_id"])),
            version=str(item.get("version", "0.0.0")),
            standalone=bool(item.get("standalone", True)),
            capabilities=frozenset(item.get("capabilities", [])),
            enabled=bool(item.get("enabled", True)),
            health=str(item.get("health", "UNKNOWN")),
            installed=bool(item.get("installed", False)),
            connected=bool(item.get("connected", False)),
            execution_mode=str(item.get("execution_mode", "ENGINE_UNCONNECTED")),
            endpoint=item.get("endpoint"),
            connectable=bool(item.get('connectable', True)),
            input_contract=str(item.get('input_contract','job.v1')),
            output_contract=str(item.get('output_contract','result.v1')),
            qa_contract=str(item.get('qa_contract','qa.v1')),
            authorization_scope=str(item.get('authorization_scope','user_approval_required')),
        )
        register_provider(manifest)
        result.append(manifest)
    return result


def required_capabilities(task: Mapping) -> set[str]:
    task_type = str(task.get("task_type", "")).strip().lower()
    direct = {
        "pdf_to_word": {"pdf_to_word"},
        "pdf_to_excel": {"pdf_to_excel"},
        "image_to_word": {"image_to_word"},
        "image_to_text": {"image_to_text"},
        "audio_to_text": {"audio_to_text"},
        "translation": {"translation_general"},
        "word_formatting": {"word_formatting"},
        "word_to_powerpoint": {"word_to_powerpoint"},
        "pdf_to_powerpoint": {"pdf_to_powerpoint"},
        "excel_cleaning": {"excel_cleaning"},
        "excel_automation": {"excel_automation"},
        "data_entry": {"data_entry"},
        "python_automation": {"python_automation"},
        "python_debugging": {"python_debugging"},
        "web_bug_bounty": {"web_bug_bounty"},
        "android_bug_bounty": {"android_bug_bounty"},
        "android_development": {"android_development"},
    }
    return set(direct.get(task_type, set())) or set(taxonomy_required(task_type))


def _coverage(required: Iterable[str], supported: Iterable[str]) -> float:
    req, sup = set(required), set(supported)
    return 1.0 if not req else len(req & sup) / len(req)


def _provider_ready(p: ProviderManifest) -> bool:
    return p.enabled and p.connected and p.health in {"HEALTHY", "UNKNOWN"}


def _providers_for(capability_name: str) -> list[ProviderManifest]:
    return [p for p in PROVIDERS.values() if capability_name in p.capabilities]


def match_capability(capability: Capability, task: Mapping) -> dict:
    required_ops = set(task.get("operations", []))
    required_inputs = set(task.get("input_formats", []))
    required_outputs = set(task.get("output_formats", []))
    required_qa = set(task.get("qa_requirements", []))
    task_type = str(task.get("task_type", "")).strip().lower()
    task_type_match = task_type in capability.task_types
    work_domain_match = str(task.get("work_domain", "")).strip().lower() == capability.work_domain
    coverage = {
        "operations": _coverage(required_ops, capability.operations),
        "inputs": _coverage(required_inputs, capability.input_formats),
        "outputs": _coverage(required_outputs, capability.output_formats),
        "qa": _coverage(required_qa, capability.qa_requirements),
    }
    providers = _providers_for(capability.name)
    connected = [p for p in providers if _provider_ready(p)]
    installed_unconnected = [p for p in providers if p.installed and not p.connected]
    if not providers:
        status = MATCH_NO_PROVIDER
    elif not any(p.enabled for p in providers):
        status = MATCH_DISABLED
    elif not connected:
        status = MATCH_NO_PROVIDER
    elif task_type_match and work_domain_match and all(v == 1.0 for v in coverage.values()):
        status = MATCH_FULL
    else:
        status = MATCH_PARTIAL
    score = round((float(task_type_match) + float(work_domain_match) + sum(coverage.values())) / 6, 3)
    return {
        "capability": capability.name,
        "status": status,
        "status_label_fa": STATUS_LABELS_FA[status],
        "coverage": score,
        "manual_possible": True,
        "connected_provider_ids": [p.provider_id for p in connected],
        "installed_not_connected_provider_ids": [p.provider_id for p in installed_unconnected],
        "providers": [
            {"provider_id": p.provider_id, "name": p.name, "version": p.version, "connected": p.connected, "installed": p.installed, "health": p.health}
            for p in providers
        ],
        "automation_level": capability.automation_level,
        "qa_mode": capability.qa_mode,
    }


def match_task(task: Mapping) -> dict:
    required = required_capabilities(task)
    if not required:
        return {
            "status": MATCH_NONE,
            "status_label_fa": STATUS_LABELS_FA[MATCH_NONE],
            "required_capabilities": [],
            "matches": [],
            "manual_possible": True,
            "productization_candidate": False,
        }
    matches = [match_capability(get_capability(name), task) for name in sorted(required) if get_capability(name)]
    statuses = {m["status"] for m in matches}
    if statuses == {MATCH_FULL}:
        status = MATCH_FULL
    elif MATCH_FULL in statuses or MATCH_PARTIAL in statuses:
        status = MATCH_PARTIAL
    elif MATCH_DISABLED in statuses:
        status = MATCH_DISABLED
    else:
        status = MATCH_NO_PROVIDER
    return {
        "status": status,
        "status_label_fa": STATUS_LABELS_FA[status],
        "required_capabilities": sorted(required),
        "matches": matches,
        "manual_possible": True,
        "productization_candidate": status in {MATCH_NO_PROVIDER, MATCH_DISABLED},
    }
