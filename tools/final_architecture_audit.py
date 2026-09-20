from __future__ import annotations
import ast, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from marketradar.source_registry import load_source_records

def main():
    checks=[]
    required=['taxonomy.py','engine_contract.py','foreign_language.py','source_workflow.py','source_identity.py','policy_evidence.py']
    checks += [{'name':f'architecture_module:{x}','status':'PASS' if (ROOT/'marketradar'/x).exists() else 'OPEN'} for x in required]
    records=load_source_records(ROOT/'config'/'sources.json')
    checks.append({'name':'source_pool_500_benchmark','status':'PASS' if len(records)>=500 else 'OPEN','count':len(records)})
    cfg=json.loads((ROOT/'config'/'capability_providers.json').read_text(encoding='utf8'))
    engines=cfg.get('providers',[])
    ids={x.get('provider_id') for x in engines}
    required_engines={'python_engine','web_bug_bounty_engine','android_bug_bounty_engine','pdf_office_engine','translation_engine','student_services_engine'}
    checks.append({'name':'engine_registry','status':'PASS' if required_engines <= ids else 'OPEN','missing':sorted(required_engines-ids)})
    checks.append({'name':'engine_standalone_contract','status':'PASS' if all(x.get('standalone') and x.get('connectable') and x.get('input_contract') and x.get('output_contract') and x.get('qa_contract') for x in engines) else 'OPEN'})
    checks.append({'name':'windows_py_launcher','status':'PASS' if not any(re.search(r'(?<![\w.-])python(?:\.exe)?\s+-m\s+', re.sub(r'\.\\\.venv\\Scripts\\python(?:\.exe)?', 'PYTHON_VENV', p.read_text(encoding='utf8',errors='ignore'))) for p in (ROOT/'packaging').glob('*.ps1')) else 'OPEN'})
    bad=[]
    for p in (ROOT/'marketradar').glob('*.py'):
        try: tree=ast.parse(p.read_text(encoding='utf8'))
        except Exception: continue
        for n in ast.walk(tree):
            if isinstance(n,(ast.Call,)) and isinstance(n.func,ast.Name) and n.func.id in {'eval','exec'}: bad.append(str(p))
    checks.append({'name':'static_eval_exec_scan','status':'PASS' if not bad else 'OPEN','files':bad})
    report={'status':'PASS' if all(x['status']=='PASS' for x in checks) else 'OPEN','checks':checks}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports'/'FINAL_ARCHITECTURE_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
