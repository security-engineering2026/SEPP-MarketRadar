from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class TaskSpec:
    task_type: str
    work_domain: str
    operations: tuple[str, ...]
    input_formats: tuple[str, ...]
    output_formats: tuple[str, ...]
    requirements: tuple[str, ...]
    qa_requirements: tuple[str, ...]
    aliases: tuple[str, ...] = ()


def _t(task_type, domain, ops, ins, outs, req, qa, aliases=()):
    return TaskSpec(task_type, domain, tuple(ops), tuple(ins), tuple(outs), tuple(req), tuple(qa), tuple(aliases))

TASKS = {
    'pdf_to_word': _t('pdf_to_word','document_processing',['extract','convert','layout_preservation'],['pdf'],['word'],['content_preservation','structure_preservation','layout_preservation'],['text_completeness','page_count','layout_check']),
    'pdf_to_excel': _t('pdf_to_excel','data_processing',['extract','convert','table_extraction','normalize'],['pdf'],['excel'],['table_integrity','structure_preservation'],['row_count','column_integrity','sample_value_check']),
    'pdf_to_powerpoint': _t('pdf_to_powerpoint','presentation',['extract_content','content_structuring','slide_generation','layout_formatting'],['pdf'],['powerpoint'],['content_preservation','slide_structure'],['slide_count','text_overflow','visual_consistency']),
    'image_to_word': _t('image_to_word','document_processing',['ocr','extract','convert','format'],['image','scan'],['word'],['ocr_quality','layout_preservation'],['text_completeness','ocr_sample_check','layout_check']),
    'image_to_text': _t('image_to_text','document_processing',['ocr','text_extraction'],['image','scan'],['text'],['ocr_quality'],['text_completeness','confidence_check']),
    'audio_to_text': _t('audio_to_text','media_processing',['transcribe','clean'],['audio'],['text'],['transcription_accuracy'],['text_completeness','confidence_review']),
    'audio_to_subtitle': _t('audio_to_subtitle','media_processing',['transcribe','timestamp','format'],['audio','video'],['subtitle','text'],['timestamp_integrity'],['timestamp_check','text_completeness']),
    'typing_retyping': _t('typing_retyping','general_services',['retype','normalize','format'],['image','pdf','scan','document'],['text','word','structured_data'],['accuracy'],['sample_accuracy','completeness']),
    'data_entry': _t('data_entry','data_processing',['extract','enter','normalize','validate'],['text','image','pdf','document','web'],['structured_data','excel','csv'],['field_mapping','completeness','normalization'],['record_count','required_field_check','sample_accuracy']),
    'translation_general': _t('translation_general','language_services',['translate','normalize','qa'],['text','document'],['text','document'],['meaning_preservation','terminology_consistency'],['completeness','terminology_check']),
    'translation_word': _t('translation_word','language_services',['translate','format','layout'],['document','word'],['word'],['meaning_preservation','layout_preservation'],['completeness','format_check','layout_check']),
    'translation_powerpoint': _t('translation_powerpoint','language_services',['translate','slide_layout','qa'],['presentation','powerpoint'],['powerpoint'],['meaning_preservation','visual_consistency'],['completeness','overflow_check','visual_consistency']),
    'word_formatting': _t('word_formatting','document_processing',['format','normalize','layout_cleanup'],['word','doc','docx'],['word','docx'],['layout_preservation'],['page_layout','headings','tables']),
    'word_to_powerpoint': _t('word_to_powerpoint','presentation',['extract_content','content_structuring','slide_generation','layout_formatting'],['word'],['powerpoint'],['content_preservation','presentation_structure'],['slide_count','text_overflow','visual_consistency']),
    'word_to_pdf': _t('word_to_pdf','document_processing',['convert','render','qa'],['word','doc','docx'],['pdf'],['layout_preservation'],['page_count','render_check']),
    'pdf_office_conversion': _t('pdf_office_conversion','document_processing',['extract','convert','normalize'],['pdf','word','excel','powerpoint'],['pdf','word','excel','powerpoint'],['content_preservation'],['file_open_check','content_sample_check']),
    'powerpoint_creation': _t('powerpoint_creation','presentation',['structure','slide_generation','layout_formatting'],['text','word','pdf','data'],['powerpoint'],['narrative_structure','visual_consistency'],['slide_count','overflow_check']),
    'powerpoint_formatting': _t('powerpoint_formatting','presentation',['format','layout','cleanup'],['powerpoint'],['powerpoint'],['visual_consistency'],['overflow_check','layout_check']),
    'excel_cleaning': _t('excel_cleaning','data_processing',['clean','normalize','deduplicate','validate'],['excel','csv','spreadsheet'],['excel','csv'],['data_integrity'],['row_count','duplicate_check','sample_value_check']),
    'excel_merge': _t('excel_merge','data_processing',['load','align','merge','validate'],['excel','csv','spreadsheet'],['excel'],['schema_alignment'],['row_count','column_integrity']),
    'excel_transformation': _t('excel_transformation','data_processing',['transform','normalize','validate'],['excel','csv','spreadsheet'],['excel','csv'],['transformation_correctness'],['schema_validation','sample_value_check']),
    'excel_automation': _t('excel_automation','data_processing',['read','transform','calculate','generate_report'],['excel','csv','spreadsheet'],['excel','report'],['repeatability','failure_recovery'],['row_count','formula_check','output_open_check']),
    'excel_analysis': _t('excel_analysis','data_processing',['analyze','calculate','summarize'],['excel','csv','spreadsheet'],['report','analysis'],['calculation_correctness'],['sample_calculation_check','consistency_check']),
    'excel_dashboard': _t('excel_dashboard','data_presentation',['aggregate','visualize','report'],['excel','csv','spreadsheet'],['dashboard','report'],['metric_correctness','traceability'],['source_to_metric_check','render_check']),
    'web_scraping': _t('web_scraping','data_acquisition',['acquire','extract','normalize','validate'],['web','html','api'],['csv','json','structured_data'],['scope_compliance','rate_limits','deduplication'],['record_count','schema_validation','source_evidence']),
    'python_automation': _t('python_automation','software_automation',['analyze','implement','validate','automate','integrate'],['requirements','source_code','structured_data','api'],['software_output','report','structured_data'],['requirement_clarity','reliability','validation'],['functional_check','output_validation','error_path_test']),
    'python_debugging': _t('python_debugging','software_engineering',['reproduce','diagnose','patch','verify'],['source_code','logs'],['patched_source','verification_report'],['reproducibility','regression_safety'],['reproduction_test','regression_test','failure_evidence']),
    'web_bug_bounty': _t('web_bug_bounty','security_engineering',['recon','validate','report'],['web_target','scope'],['finding_report','evidence'],['authorization','scope_compliance','evidence_integrity'],['authorization_check','finding_validation','evidence_integrity']),
    'android_bug_bounty': _t('android_bug_bounty','security_engineering',['recon','analyze','validate','report'],['android_target','apk','scope'],['finding_report','evidence'],['authorization','scope_compliance','evidence_integrity'],['authorization_check','finding_validation','evidence_integrity']),
    'android_development': _t('android_development','android',['design','implement','build','test','package'],['requirements','source_code'],['apk','aab','source_code'],['build_integrity','installability','functional_correctness'],['build_check','install_check','functional_check']),
}

BUNDLED_WORKFLOWS = {
    'pdf_to_word_formatted': ('pdf_to_word','word_formatting'),
    'ocr_to_word_formatted': ('image_to_text','word_formatting'),
    'translation_to_word_layout': ('translation_general','translation_word','word_formatting'),
    'translation_to_powerpoint': ('translation_general','translation_powerpoint'),
    'excel_merge_clean_analyze_dashboard': ('excel_merge','excel_cleaning','excel_analysis','excel_dashboard'),
    'pdf_to_powerpoint': ('pdf_to_powerpoint',),
    'word_to_powerpoint': ('word_to_powerpoint',),
    'pdf_office_bundle': ('pdf_to_word','pdf_to_excel','pdf_to_powerpoint'),
}

ALIASES = {a: name for name, spec in TASKS.items() for a in (spec.aliases + (name,))}

def canonicalize_task(value: str) -> str:
    key = str(value or '').strip().lower().replace(' ','_').replace('-','_')
    return ALIASES.get(key, key)

def get_task(task_type: str) -> TaskSpec | None:
    return TASKS.get(canonicalize_task(task_type))

def list_tasks(work_domain: str | None = None) -> list[TaskSpec]:
    return sorted((x for x in TASKS.values() if not work_domain or x.work_domain == work_domain), key=lambda x:x.task_type)

def resolve_workflow(workflow: str) -> tuple[TaskSpec, ...]:
    return tuple(TASKS[x] for x in BUNDLED_WORKFLOWS.get(str(workflow), (canonicalize_task(workflow),)) if x in TASKS)

def required_task_capabilities(task_type: str, operations: Iterable[str] = ()) -> set[str]:
    canonical = canonicalize_task(task_type)
    return {canonical} if canonical in TASKS else set()
