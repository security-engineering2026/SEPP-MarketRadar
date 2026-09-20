from .pipeline import Pipeline
SOURCES=[{'name':'Verified-USDT','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'},{'name':'Verified-IRR','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'IRR/local','terms_status':'allowed'},{'name':'KYC-Unknown','iran_status':'ALLOW','kyc_status':'UNKNOWN','payment_status':'USDT','terms_status':'allowed'}]
ITEMS=[('CSV cleaning','$50 USDT','simple small CSV data cleaning'),('Python bug fix','$100 USDT','minor bug quick fix'),('Excel automation','$150 USDT','small spreadsheet automation'),('Web scraping','$300 USDT','data extraction several pages'),('API integration','$500 USDT','REST API integration'),('Business automation','$1000 USDT','workflow automation database'),('Data pipeline','$1500 USDT','ETL data pipeline'),('Android security audit','$800 USDT','Android security audit APK'),('Python automation','$250 USDT','Python automation')]
def seed(c):
 p=Pipeline(c)
 for i,(title,budget,desc) in enumerate(ITEMS):
  s=SOURCES[i%3];u=f'https://example.test/opportunity/{i+1}';p.ingest(s,{'title':title,'url':u,'description':desc+' budget '+budget,'evidence':[{'kind':'listing','url':u,'finding':'project-specific listing','confidence':.92,'provenance_root':s['name']}]})
 c.commit();return p
