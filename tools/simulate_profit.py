import json
p='data/daily_state.json'
with open(p,'r',encoding='utf-8') as f:
    d=json.load(f)
print('Before:', d.get('usdt_operacional'), d.get('saldo_inicial_usdt'))
# simulate profit +20
d['usdt_operacional']=round(d.get('usdt_operacional',0)+20,6)
saldo_inicial=d.get('saldo_inicial_usdt', d.get('usdt_operacional'))
d['lucro_acumulado_usdt']=round(d['usdt_operacional']-saldo_inicial,6)
with open(p,'w',encoding='utf-8') as f:
    json.dump(d,f,indent=2,ensure_ascii=False)
print('After write:', d['usdt_operacional'], d['lucro_acumulado_usdt'])
