def revenue_summary(c):
    return [{'currency':r[0],'total':r[1],'payments':r[2]} for r in c.execute('select currency,sum(amount),count(*) from revenue group by currency')]
