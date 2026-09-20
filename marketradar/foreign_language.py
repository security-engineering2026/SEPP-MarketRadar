from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class UIElement:
    element_id: str
    role: str
    label: str
    action: str | None = None
    selector: str | None = None
    visible: bool = True

@dataclass(frozen=True)
class GuidanceStep:
    order: int
    instruction: str
    action: str | None
    element_id: str | None
    requires_approval: bool = False

@dataclass(frozen=True)
class TranslationEvidence:
    source_text: str
    translated_text: str | None
    source_language: str
    target_language: str
    source_snapshot_id: str | None
    provider: str | None
    status: str

LANGUAGE_MARKERS = {
    'ru': re.compile(r'[А-Яа-яЁё]'),
    'tr': re.compile(r'\b(?:başvuru|giriş|kayıt|yükle|onayla|iş|ödeme)\b', re.I),
    'ar': re.compile(r'[\u0600-\u06ff]'),
    'fa': re.compile(r'[\u067e\u0686\u0698\u06af]'),
    'zh': re.compile(r'[\u4e00-\u9fff]'),
    'en': re.compile(r'\b(?:login|register|apply|upload|confirm|job|payment)\b', re.I),
}
ACTION_MARKERS = {
    'login': ('login','sign in','войти','вход','giriş','تسجيل الدخول','ورود'),
    'register': ('register','sign up','регистрация','регист','kayıt','зарегистр','التسجيل','ثبت نام'),
    'apply': ('apply','proposal','submit application','отклик','подать','заявк','başvur','التقديم','درخواست'),
    'upload': ('upload','attach','загруз','файл','yükle','إرفاق','آپلود'),
    'confirm': ('confirm','submit','отправ','подтверд','отсъ','onayla','إرسال','تأیید'),
}

def detect_language(text: str) -> str:
    text = str(text or '')
    scores = {lang: len(p.findall(text)) for lang,p in LANGUAGE_MARKERS.items()}
    return max(scores, key=scores.get) if max(scores.values(), default=0) else 'unknown'

def translate_with_evidence(text: str, source_language='unknown', target_language='en', snapshot_id=None, provider=None, translated_text=None) -> TranslationEvidence:
    return TranslationEvidence(str(text), translated_text, source_language if source_language != 'unknown' else detect_language(text), target_language, snapshot_id, provider, 'TRANSLATED' if translated_text is not None else 'TRANSLATION_PROVIDER_UNAVAILABLE')

def guide_page(text: str, elements: list[UIElement] | None = None) -> list[GuidanceStep]:
    elems = elements or []
    low = str(text or '').lower()
    found = []
    for action, markers in ACTION_MARKERS.items():
        hit = next((m for m in markers if m in low), None)
        if hit:
            element = next((e for e in elems if hit in e.label.lower()), None)
            found.append((action, element))
    steps=[]
    for i,(action,element) in enumerate(found,1):
        requires = action in {'apply','confirm'}
        instruction = {
            'login':'Sign in here.', 'register':'Registration is here.', 'apply':'This is the application/proposal action. Review before submitting.', 'upload':'This control is for attaching the required file.', 'confirm':'This is the final submission/confirmation step; approval is required.'
        }[action]
        steps.append(GuidanceStep(i,instruction,action,element.element_id if element else None,requires))
    return steps

def page_understanding(text: str, elements: list[UIElement] | None = None, snapshot_id=None) -> dict:
    lang = detect_language(text)
    return {'source_language':lang,'guidance':guide_page(text,elements),'translation_evidence':translate_with_evidence(text,lang,'en',snapshot_id),'autonomous_action':False,'approval_boundary':True}
