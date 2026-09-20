from __future__ import annotations

import re

from .analysis import classify
from .taxonomy import get_task, BUNDLED_WORKFLOWS

TOOL_MAP = {
    'web_scraping': ('Web Data Collector', 'collect, normalize and validate permitted public web data'),
    'data_cleaning': ('Data Quality Tool', 'clean, validate, deduplicate and report structured data'),
    'excel_automation': ('Spreadsheet Automation Tool', 'validate workbook inputs, transform data and export results'),
    'python_debugging': ('Python Diagnostic Tool', 'capture failure evidence, reproduce, diagnose and verify a patch'),
    'api_integration': ('API Integration Tool', 'authenticate through an authorized API, normalize responses and handle retries'),
    'telegram_automation': ('Telegram Workflow Tool', 'process messages/channels through authorized Telegram access'),
    'business_automation': ('Business Workflow Tool', 'turn a repeated manual workflow into a validated pipeline'),
    'data_pipeline': ('Data Pipeline Tool', 'collect, normalize, aggregate, store and report data'),
    'android': ('Android Utility', 'implement a focused Android client around a defined core capability'),
    'security': ('Security Engineering Tool', 'analyze, validate, log and report security-relevant data'),
    'general_software': ('Custom Software Component', 'analyze requirements and propose the smallest reusable component'),
}


def _has(text: str, *terms: str) -> bool:
    low = text.lower()
    return any(term.lower() in low for term in terms)


def _unique(values):
    out = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _formats(text: str) -> list[str]:
    rules = [
        ('pdf', ('pdf',)), ('word', ('word', 'doc', 'docx')),
        ('excel', ('excel', 'xlsx', 'xls', 'spreadsheet')),
        ('powerpoint', ('powerpoint', 'ppt', 'pptx', 'presentation')),
        ('image', ('image', 'images', 'photo', 'scan', 'scanned')),
        ('audio', ('audio', 'voice', 'recording')),
        ('video', ('video', 'mp4', 'mov')), ('csv', ('csv',)),
        ('json', ('json',)), ('txt', ('txt', 'text file')),
    ]
    return [name for name, terms in rules if _has(text, *terms)]


def _conversion(text: str):
    t = re.sub(r'\s+', ' ', text.lower())
    rules = [
        ('pdf_to_word', ('pdf to word', 'pdf into word', 'pdf 2 word', 'pdf2word', 'pdf to doc', 'pdf to docx'), 'document_processing', ['extract', 'convert', 'layout_preservation'], ['pdf'], ['word'], ['content_preservation', 'structure_preservation', 'layout_preservation'], ['text_completeness', 'page_count', 'layout_check']),
        ('pdf_to_excel', ('pdf to excel', 'pdf into excel', 'pdf 2 excel', 'pdf2excel', 'pdf to xls', 'pdf to xlsx'), 'data_processing', ['extract', 'convert', 'table_extraction', 'normalize'], ['pdf'], ['excel'], ['table_structure', 'row_integrity', 'column_integrity'], ['row_count', 'column_integrity', 'sample_value_check']),
        ('image_to_word', ('image to word', 'image into word', 'image 2 word', 'image2word', 'scan to word', 'scanned image to word'), 'document_processing', ['ocr', 'extract', 'convert', 'document_generation'], ['image'], ['word'], ['ocr_accuracy', 'document_structure', 'layout_preservation'], ['text_completeness', 'ocr_sample_check', 'layout_check']),
        ('image_to_text', ('image to text', 'image into text', 'image 2 text', 'image2text', 'scan to text', 'scanned image to text'), 'document_processing', ['ocr', 'text_extraction'], ['image'], ['text'], ['ocr_accuracy', 'character_preservation'], ['text_completeness', 'confidence_check']),
        ('word_to_powerpoint', ('word to powerpoint', 'word into powerpoint', 'word 2 powerpoint', 'word2powerpoint', 'docx to powerpoint', 'word to ppt', 'word to pptx'), 'presentation', ['extract_content', 'content_structuring', 'slide_generation', 'layout_formatting'], ['word'], ['powerpoint'], ['source_fidelity', 'slide_structure', 'readability'], ['slide_count', 'text_overflow', 'visual_consistency', 'source_completeness']),
        ('pdf_to_powerpoint', ('pdf to powerpoint', 'pdf into powerpoint', 'pdf 2 powerpoint', 'pdf2powerpoint', 'pdf to ppt', 'pdf to pptx'), 'presentation', ['extract_content', 'content_structuring', 'slide_generation', 'layout_formatting'], ['pdf'], ['powerpoint'], ['source_fidelity', 'slide_structure', 'readability'], ['slide_count', 'text_overflow', 'visual_consistency', 'source_completeness']),
    ]
    for name, phrases, domain, ops, inputs, outputs, req, qa in rules:
        if any(phrase in t for phrase in phrases):
            return {'task_type': name, 'work_domain': domain, 'operations': ops, 'input_formats': inputs, 'output_formats': outputs, 'requirements': req, 'qa_requirements': qa}
    return None


def _taxonomy_task(text: str) -> dict | None:
    low = re.sub(r'\s+', ' ', text.lower())
    bundle_phrases = {
        'pdf_to_word_formatted': ('pdf to word' in low and ('format' in low or 'صفحه' in low)),
        'translation_to_word_layout': ('translation' in low and 'word' in low and ('layout' in low or 'format' in low or 'ترجمه' in low)),
        'translation_to_powerpoint': ('translation' in low and ('powerpoint' in low or 'ppt' in low)),
        'excel_merge_clean_analyze_dashboard': ('excel' in low and ('merge' in low or 'ادغام' in low) and ('clean' in low or 'پاک' in low) and ('dashboard' in low or 'داشبورد' in low)),
    }
    for bundle, parts in bundle_phrases.items():
        if parts:
            specs=[get_task(x) for x in BUNDLED_WORKFLOWS[bundle]]
            if specs and all(specs):
                return {'task_type': bundle, 'work_domain': specs[0].work_domain, 'operations': [op for spec in specs for op in spec.operations], 'input_formats': list(dict.fromkeys(x for spec in specs for x in spec.input_formats)), 'output_formats': list(dict.fromkeys(x for spec in specs for x in spec.output_formats)), 'requirements': list(dict.fromkeys(x for spec in specs for x in spec.requirements)), 'qa_requirements': list(dict.fromkeys(x for spec in specs for x in spec.qa_requirements))}
    exact_map = {
        'pdf to word':'pdf_to_word','pdf to excel':'pdf_to_excel','pdf to powerpoint':'pdf_to_powerpoint','image to word':'image_to_word','image to text':'image_to_text','audio to text':'audio_to_text','transcription':'audio_to_text','typing':'typing_retyping','retyping':'typing_retyping','translation + word':'translation_word','translation + powerpoint':'translation_powerpoint','word formatting':'word_formatting','word to powerpoint':'word_to_powerpoint','word to pdf':'word_to_pdf','powerpoint creation':'powerpoint_creation','powerpoint formatting':'powerpoint_formatting','excel cleaning':'excel_cleaning','excel merge':'excel_merge','excel transformation':'excel_transformation','excel automation':'excel_automation','excel analysis':'excel_analysis','excel dashboard':'excel_dashboard'}
    for phrase,task_name in exact_map.items():
        if phrase in low:
            spec=get_task(task_name)
            if spec:
                return {'task_type': spec.task_type, 'work_domain': spec.work_domain, 'operations': list(spec.operations), 'input_formats': list(spec.input_formats), 'output_formats': list(spec.output_formats), 'requirements': list(spec.requirements), 'qa_requirements': list(spec.qa_requirements)}
    return None


def _task_rules(text: str, category: str) -> dict:
    exact = _conversion(text)
    if exact:
        return exact
    taxonomy = _taxonomy_task(text)
    if taxonomy:
        return taxonomy
    low = text.lower()

    if _has(low, 'audio to text', 'audio transcription', 'speech to text', 'transcribe audio', 'transcription'):
        return {'task_type': 'audio_to_text', 'work_domain': 'media_processing', 'operations': ['audio_transcription', 'speech_to_text', 'text_cleanup'], 'input_formats': ['audio'], 'output_formats': ['text'], 'requirements': ['transcription_accuracy', 'speaker_or_segment_preservation'], 'qa_requirements': ['text_completeness', 'confidence_review', 'timestamp_check']}
    if _has(low, 'ocr', 'optical character recognition', 'scan to text'):
        return {'task_type': 'ocr', 'work_domain': 'document_processing', 'operations': ['ocr', 'text_extraction'], 'input_formats': ['image', 'pdf'], 'output_formats': ['text'], 'requirements': ['ocr_accuracy', 'language_support'], 'qa_requirements': ['text_completeness', 'confidence_check', 'sample_visual_check']}
    if _has(low, 'translation', 'translate', 'ترجمه', 'ترجمه انگلیسی', 'ترجمه فارسی'):
        return {'task_type': 'translation', 'work_domain': 'language_services', 'operations': ['translate', 'language_normalization', 'format_preservation'], 'input_formats': ['text', 'document'], 'output_formats': ['text', 'document'], 'requirements': ['source_language', 'target_language', 'meaning_preservation'], 'qa_requirements': ['completeness', 'terminology_check', 'format_check']}
    if _has(low, 'word formatting', 'format word', 'document formatting', 'format document', 'صفحه آرایی', 'فرمت ورد'):
        return {'task_type': 'word_formatting', 'work_domain': 'document_processing', 'operations': ['format', 'normalize', 'layout_cleanup'], 'input_formats': ['word'], 'output_formats': ['word'], 'requirements': ['style_consistency', 'layout_preservation'], 'qa_requirements': ['page_layout', 'headings', 'tables', 'spacing']}
    if _has(low, 'powerpoint', 'power point', 'presentation design', 'presentation creation', 'ساخت پاورپوینت', 'پاورپوینت'):
        return {'task_type': 'powerpoint', 'work_domain': 'presentation', 'operations': ['content_structuring', 'slide_generation', 'layout_formatting'], 'input_formats': ['text', 'document'], 'output_formats': ['powerpoint'], 'requirements': ['slide_structure', 'readability', 'source_fidelity'], 'qa_requirements': ['slide_count', 'text_overflow', 'visual_consistency']}
    if _has(low, 'excel automation', 'automate excel', 'spreadsheet automation', 'excel report', 'اتوماسیون اکسل'):
        return {'task_type': 'excel_automation', 'work_domain': 'data_processing', 'operations': ['read', 'transform', 'calculate', 'generate_report'], 'input_formats': ['excel', 'csv', 'spreadsheet'], 'output_formats': ['excel', 'report'], 'requirements': ['formula_integrity', 'repeatability', 'output_consistency'], 'qa_requirements': ['row_count', 'formula_check', 'output_open_check']}
    if _has(low, 'excel cleaning', 'clean excel', 'spreadsheet cleaning', 'merge excel', 'excel merge', 'اکسل', 'پاکسازی اکسل'):
        return {'task_type': 'excel_cleaning', 'work_domain': 'data_processing', 'operations': ['clean', 'normalize', 'deduplicate', 'validate'], 'input_formats': ['excel', 'csv', 'spreadsheet'], 'output_formats': ['excel', 'csv'], 'requirements': ['row_integrity', 'column_integrity', 'duplicate_policy'], 'qa_requirements': ['row_count', 'duplicate_check', 'sample_value_check']}
    if _has(low, 'typing', 'data entry', 'type data', 'type scanned', 'type scan', 'تایپ', 'ورود اطلاعات', 'تایپ فایل'):
        return {'task_type': 'data_entry', 'work_domain': 'data_processing', 'operations': ['extract', 'enter', 'normalize', 'validate'], 'input_formats': ['text', 'image', 'pdf', 'document'], 'output_formats': ['structured_data', 'excel', 'csv'], 'requirements': ['field_mapping', 'completeness', 'normalization'], 'qa_requirements': ['record_count', 'required_field_check', 'sample_accuracy']}
    if _has(low, 'web scraping', 'scraping', 'crawler', 'data extraction'):
        return {'task_type': 'web_scraping', 'work_domain': 'data_acquisition', 'operations': ['collect', 'extract', 'normalize', 'validate'], 'input_formats': ['web'], 'output_formats': ['csv', 'json', 'structured_data'], 'requirements': ['source_scope', 'rate_limits', 'deduplication'], 'qa_requirements': ['record_count', 'schema_validation', 'source_evidence']}
    if _has(low, 'bug bounty', 'vulnerability disclosure', 'security program', 'responsible disclosure'):
        if _has(low, 'android', 'apk', 'mobile application', 'mobile app'):
            return {'task_type': 'android_bug_bounty', 'work_domain': 'security_engineering', 'operations': ['recon', 'analyze', 'validate', 'report'], 'input_formats': ['android_target', 'apk', 'scope'], 'output_formats': ['finding_report', 'evidence'], 'requirements': ['authorization', 'scope_compliance', 'evidence_integrity'], 'qa_requirements': ['authorization_check', 'finding_validation', 'evidence_integrity']}
        return {'task_type': 'web_bug_bounty', 'work_domain': 'security_engineering', 'operations': ['recon', 'validate', 'report'], 'input_formats': ['web_target', 'scope'], 'output_formats': ['finding_report', 'evidence'], 'requirements': ['authorization', 'scope_compliance', 'evidence_integrity'], 'qa_requirements': ['authorization_check', 'finding_validation', 'evidence_integrity']}
    if _has(low, 'android', 'kotlin', 'apk', 'android app', 'android development'):
        return {'task_type': 'android_development', 'work_domain': 'android', 'operations': ['design', 'implement', 'build', 'test', 'package'], 'input_formats': ['requirements', 'source_code'], 'output_formats': ['apk', 'aab', 'source_code'], 'requirements': ['build_integrity', 'installability', 'functional_correctness'], 'qa_requirements': ['build_check', 'install_check', 'functional_check']}
    if _has(low, 'python automation', 'python script', 'python development', 'python developer'):
        return {'task_type': 'python_automation', 'work_domain': 'software_automation', 'operations': ['analyze', 'implement', 'validate', 'automate'], 'input_formats': ['requirements', 'structured_data'], 'output_formats': ['software_output', 'report'], 'requirements': ['requirement_clarity', 'reliability', 'validation'], 'qa_requirements': ['functional_check', 'output_validation', 'error_path_test']}
    if category == 'python_debugging' or _has(low, 'python bug', 'debug python', 'traceback'):
        return {'task_type': 'python_debugging', 'work_domain': 'software_engineering', 'operations': ['reproduce', 'diagnose', 'patch', 'verify'], 'input_formats': ['source_code', 'logs'], 'output_formats': ['patched_source', 'verification_report'], 'requirements': ['reproducibility', 'regression_safety'], 'qa_requirements': ['reproduction_test', 'regression_test', 'failure_evidence']}
    if category in {'api_integration', 'business_automation', 'data_pipeline'}:
        return {'task_type': category, 'work_domain': 'software_automation', 'operations': ['integrate', 'validate', 'transform', 'automate'], 'input_formats': _formats(low) or ['structured_data'], 'output_formats': ['structured_data', 'automation_result'], 'requirements': ['validation', 'repeatability', 'failure_recovery'], 'qa_requirements': ['input_validation', 'output_validation', 'error_path_test']}
    if category == 'security':
        return {'task_type': 'security_task', 'work_domain': 'security_engineering', 'operations': ['analyze', 'validate', 'report'], 'input_formats': ['security_data'], 'output_formats': ['report'], 'requirements': ['authorization', 'evidence_integrity'], 'qa_requirements': ['evidence_check', 'finding_validation', 'report_check']}

    return {'task_type': 'general_software_task', 'work_domain': 'software_engineering', 'operations': ['analyze', 'implement', 'validate'], 'input_formats': _formats(low) or ['unspecified'], 'output_formats': ['software_output'], 'requirements': ['requirement_clarity', 'validation'], 'qa_requirements': ['functional_check', 'output_validation']}


def analyze_need(item):
    text = ' '.join(str(item.get(k, '')) for k in ('title', 'description', 'category'))
    category = classify(text)
    tool, purpose = TOOL_MAP.get(category, TOOL_MAP['general_software'])
    desc = str(item.get('description', '')).lower()
    complexity = 'low'
    terms = ('multiple', 'integration', 'database', 'dashboard', 'large', 'complex', 'production')
    if any(x in desc for x in terms):
        complexity = 'medium'
    if sum(x in desc for x in terms) >= 4:
        complexity = 'high'
    components = ['input', 'validation', 'processing', 'output', 'reliability']
    if category in {'web_scraping', 'api_integration', 'telegram_automation'}:
        components = ['acquisition', 'validation', 'normalization', 'storage', 'reliability', 'presentation']
    task = _task_rules(text, category)
    return {
        'category': category,
        'tool_name': tool,
        'purpose': purpose,
        'complexity': complexity,
        'components': components,
        'build_recommendation': f'Build {tool} as a reusable component; keep source-specific acquisition separate from processing and enforce validation/retry/logging.',
        'task_understanding': task,
        'work_domain': task['work_domain'],
        'task_type': task['task_type'],
        'operations': task['operations'],
        'input_formats': task['input_formats'],
        'output_formats': task['output_formats'],
        'requirements': task['requirements'],
        'qa_requirements': task['qa_requirements'],
    }
