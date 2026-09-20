from __future__ import annotations
import math, re
from datetime import datetime, timezone
from .learning import learning_settings
from .opportunity_signals import extract_signals

CATEGORY_TRACK = {
    'security': {'red_team','blue_team'},
    'web_scraping': {'software_engineering','data_automation'},
    'data_cleaning': {'data_automation','software_engineering'},
    'excel_automation': {'data_automation','software_engineering'},
    'python_debugging': {'software_engineering','blue_team'},
    'api_integration': {'software_engineering','data_automation'},
    'telegram_automation': {'software_engineering','data_automation'},
    'business_automation': {'software_engineering','data_automation'},
    'data_pipeline': {'software_engineering','data_automation','blue_team'},
    'android': {'software_engineering','red_team','blue_team'},
    'general_software': {'software_engineering'},
}


def _text(item): return ' '.join(str(item.get(k) or '') for k in ('title','description','category')).lower()


def estimate_difficulty(item) -> int:
    t = _text(item)
    points = 1
    groups = [
        (('simple','small','minor','quick','single script','one endpoint'), 0),
        (('api','integration','database','authentication','dashboard','multiple files','automation'), 1),
        (('production','scalable','real-time','distributed','microservice','multi-tenant','high volume'), 2),
        (('architecture','security audit','penetration test','incident response','zero downtime','migration'), 2),
    ]
    for terms, inc in groups:
        if any(x in t for x in terms): points += inc
    return max(1, min(5, points))


def skill_fit(item, profile) -> tuple[float, list[str]]:
    text = _text(item)
    skills = [str(x).lower() for x in (profile or {}).get('skills', [])]
    if not skills: return 0.45, []
    hits = [s for s in skills if s and (s in text or s.replace(' ','_') in text)]
    category = str(item.get('category') or '').lower()
    if category and any(category.replace('_',' ') in s or s in category.replace('_',' ') for s in skills):
        hits.append(category)
    hits = list(dict.fromkeys(hits))
    return min(1.0, 0.25 + 0.15 * len(hits)), hits[:8]


def competition_score(item) -> float:
    signals=item.get('_signals') or extract_signals(item)
    return float(signals.get('competition_score',0.55))

def application_speed(item) -> tuple[float, str]:
    t = _text(item)
    if any(x in t for x in ('one click apply','easy apply','quick apply')): return 0.98, 'FAST_FORM'
    if any(x in t for x in ('apply now','submit proposal','send proposal','application')): return 0.78, 'STANDARD_FORM'
    if any(x in t for x in ('email','send cv','send resume')): return 0.70, 'EMAIL_REVIEW'
    return 0.45, 'MANUAL_REVIEW'


def freshness_score(item) -> float:
    raw = item.get('last_seen') or item.get('first_seen')
    if not raw: return 0.45
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z','+00:00'))
        age = max(0, (datetime.now(timezone.utc)-dt).total_seconds()/86400)
        return max(0.05, min(1.0, math.exp(-age/7)))
    except ValueError: return 0.45


def rank_opportunity(item, profile=None) -> dict:
    profile = profile or {}
    ls = learning_settings(profile)
    category = str(item.get('category') or 'general_software')
    signals = item.get('_signals') or extract_signals(item)
    difficulty = estimate_difficulty(item)
    fit, skill_gap = skill_fit(item, profile)
    diff_delta = abs(difficulty-ls['level'])
    if difficulty > ls['max_complexity']:
        difficulty_fit = 0.18
    elif diff_delta == 0:
        difficulty_fit = 1.0
    elif diff_delta == 1:
        difficulty_fit = 0.78 if ls['stretch'] else 0.55
    else:
        difficulty_fit = 0.45
    tracks = CATEGORY_TRACK.get(category, {'software_engineering'})
    track = next((x for x in ls['tracks'] if x in tracks), 'software_engineering')
    learning_value = 0.55 + (0.20 if track in ls['tracks'] else 0) + (0.15 if difficulty in {ls['level'], ls['level']+1} else 0)
    learning_value = min(1.0, learning_value)
    competition = competition_score({**item,'_signals':signals})
    speed, path = application_speed(item)
    reputation = float(signals.get('client_reputation_score',0.45))
    acceptance = float(item.get('acceptance_probability',0.5))
    expected_value = float(item.get('expected_value',0) or 0)
    budget_value = float(item.get('budget') or 0)
    revenue_score = min(1.0, expected_value/1000) if expected_value > 0 else min(1.0, budget_value/1000) if budget_value > 0 else 0.35
    deadline_urgency = float(signals.get('deadline_urgency',0.45))
    evidence = float(item.get('evidence_confidence') or 0)
    quality = float(item.get('quality_score') or evidence)
    eligibility = str(item.get('eligibility') or 'UNKNOWN')
    policy = {'EXECUTE':1.0,'REVIEW':0.65,'UNKNOWN':0.25,'BLOCK':0.0}.get(eligibility,0.25)
    budget = item.get('budget')
    budget_score = 0.45 if budget is None else min(1.0, 0.45 + math.log10(max(float(budget),1))/4)
    freshness = freshness_score(item)
    security_bonus = 0.08 if category == 'security' else 0.0
    score = (100*(
        0.18*quality + 0.10*evidence + 0.20*fit + 0.12*difficulty_fit +
        0.09*learning_value + 0.08*competition + 0.07*speed + 0.05*freshness +
        0.07*reputation + 0.07*acceptance + 0.07*revenue_score + 0.04*deadline_urgency +
        0.04*budget_score + 0.02*policy
    ) / 1.20) + 100*security_bonus
    if eligibility == 'BLOCK': score = 0.0
    return {
        'rank_score': round(max(0,min(100,score)),2),
        'skill_fit': round(fit,3), 'difficulty_score': difficulty,
        'difficulty_fit': round(difficulty_fit,3), 'learning_value': round(learning_value,3),
        'competition_score': round(competition,3), 'application_speed_score': round(speed,3),
        'freshness_score': round(freshness,3), 'recommended_level': difficulty,
        'track': track, 'application_path': path, 'skill_gap': skill_gap,
        'client_reputation_score': round(reputation,3), 'acceptance_probability': round(acceptance,3),
        'deadline_urgency': round(deadline_urgency,3), 'expected_value': round(expected_value,2), 'revenue_score': round(revenue_score,3),
        'proposal_count': signals.get('proposal_count'), 'competition_pressure': signals.get('competition_pressure',0.45),
        'deadline_at': signals.get('deadline_at'), 'deadline_confidence': signals.get('deadline_confidence',0),
        'proposal_count_confidence': signals.get('proposal_count_confidence',0),
        'client_reputation_confidence': signals.get('client_reputation_confidence',0),
    }
