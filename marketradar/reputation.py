from collections import Counter,defaultdict
import hashlib,re
def norm(s): return re.sub(r'\W+',' ',(s or '').lower()).strip()
def review_intel(reviews):
 if not reviews:return {'state':'UNKNOWN','authoritative':False,'confidence':0,'independent_provenance_count':0,'flags':['NO_REVIEWS']}
 roots=Counter(r.get('provenance_root') or r.get('source') or 'UNKNOWN' for r in reviews); authors=Counter(r.get('author','UNKNOWN') for r in reviews); texts=defaultdict(list)
 for r in reviews:texts[hashlib.sha256(norm(r.get('text')).encode()).hexdigest()].append(r)
 flags=[]
 if len(reviews)>=4 and max(roots.values())/len(reviews)>=.75:flags.append('PROVENANCE_CONCENTRATION')
 if len(reviews)>=4 and len(authors)/len(reviews)<=.5:flags.append('LOW_AUTHOR_DIVERSITY')
 if any(len(v)>=2 for v in texts.values()):flags.append('COPY_CLUSTER')
 ts=[r.get('timestamp') for r in reviews if isinstance(r.get('timestamp'),(int,float))]
 if len(ts)>=4 and max(ts)-min(ts)<=86400:flags.append('BURST')
 if any(r.get('verified') is False for r in reviews):flags.append('UNVERIFIED_REVIEWS')
 pos=sum(str(r.get('sentiment','')).lower()=='positive' for r in reviews);neg=sum(str(r.get('sentiment','')).lower()=='negative' for r in reviews);ind=len(roots)
 if ind==1:state='UNKNOWN'
 elif neg>=2 and neg>pos:state='HIGH_RISK'
 elif pos>=2 and pos>neg and not flags:state='LOW_RISK'
 else:state='MIXED'
 conf=min(.95,.25+.12*ind+.05*min(10,len(reviews)))
 if 'PROVENANCE_CONCENTRATION' in flags:conf=min(conf,.55)
 return {'state':state,'authoritative':False,'confidence':round(conf,3),'independent_provenance_count':ind,'flags':flags,'positive':pos,'negative':neg}
