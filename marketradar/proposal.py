from __future__ import annotations
from .opportunity_intelligence import analyze_need

def generate_proposal(profile, opportunity, language=None, target_amount=None, target_currency=None):
    p=dict(profile or {}); n=analyze_need(opportunity); title=opportunity.get('title','this project')
    lang=(language or opportunity.get('language') or 'en').lower().split('-')[0]
    amount=target_amount if target_amount is not None else opportunity.get('budget')
    currency=target_currency or opportunity.get('currency') or ''
    name=p.get('name','')
    if lang=='fa':
        price=f"\nبودجه پیشنهادی: {amount} {currency}" if amount is not None else ''
        return f"سلام،\n\nپروژه «{title}» را بررسی کردم. نیاز اصلی پروژه {n.get('purpose','')} است.\n\nراهکار من بر پایه {n.get('tool_name','راهکار نرم‌افزاری')} و با اعتبارسنجی ورودی، پردازش قابل‌اعتماد و معیارهای پذیرش مشخص خواهد بود. ابتدا ورودی‌ها، خروجی‌ها، محدودیت‌ها و شرایط تحویل را نهایی می‌کنم و سپس نسخه قابل‌آزمایش ارائه می‌دهم.{price}\n\nمهارت‌های مرتبط: {', '.join((p.get('skills') or [])[:8])}.\n\nبا احترام،\n{name}".strip()
    price=f"\nProposed budget: {amount} {currency}" if amount is not None else ''
    return f"Hello,\n\nI reviewed {title}. The core need appears to be {n.get('purpose','')}.\n\nI would approach it as a focused {n.get('tool_name','software solution')} with clear input validation, reliable processing, observable failure handling, and explicit acceptance criteria. I would confirm inputs, outputs and edge cases first, then deliver a tested implementation and iterate from evidence.{price}\n\nRelevant strengths: {', '.join((p.get('skills') or [])[:8])}.\n\nBest regards,\n{name}".strip()
