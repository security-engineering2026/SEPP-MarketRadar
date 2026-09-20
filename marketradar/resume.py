from __future__ import annotations
from .opportunity_intelligence import analyze_need

def tailored_resume(profile, opportunity, language=None):
    p=dict(profile or {}); need=analyze_need(opportunity); lang=(language or opportunity.get("language") or "en").lower().split("-")[0]
    skills=list(dict.fromkeys((p.get("skills") or []) + [need.get("category","").replace("_"," ")]))
    name=p.get("name","Candidate"); headline=p.get("headline","Software / Automation Engineer")
    if lang=='fa':
        lines=[name,headline,'','خلاصه',p.get('summary','مهندس نرم‌افزار با تمرکز بر توسعه، اتوماسیون و اجرای قابل‌اعتماد.'),'','مهارت‌های متناسب',', '.join(skills)]
        labels={'experience':'تجربه','projects':'پروژه‌ها','certifications':'گواهی‌ها','portfolio':'نمونه‌کارها','services':'خدمات'}
        for section,label in labels.items():
            values=p.get(section) or []
            if values:
                lines += ['',label]
                for v in values: lines.append(f"- {v if isinstance(v,str) else v.get('title','Project')}: {v if isinstance(v,str) else v.get('description','')}")
        return '\n'.join(lines).strip()
    lines=[name,headline,'','SUMMARY',p.get('summary','Builds reliable software components with validation, logging, failure handling and evidence-first workflows.'),'','TARGETED SKILLS',', '.join(skills)]
    for section in ('experience','projects','certifications','portfolio','services'):
        values=p.get(section) or []
        if values:
            lines += ['',section.upper()]
            for v in values: lines.append(f"- {v if isinstance(v,str) else v.get('title','Project')}: {v if isinstance(v,str) else v.get('description','')}")
    return '\n'.join(lines).strip()
