# 🚨 CORREÇÕES URGENTES - PROBLEMA DE OVERTRADING

## ❌ PROBLEMA IDENTIFICADO
O sistema R7_V3 estava executando trades muito rapidamente, comprando e vendendo sem tempo suficiente para o preço se desenvolver, resultando em perdas constantes.

## ✅ CORREÇÕES IMPLEMENTADAS

### 1. 🛡️ COOLDOWN ENTRE TRADES (Guardião)
**Arquivo:** `bots/guardiao.py`

- **Adicionado:** Sistema de cooldown de **2 minutos** entre trades da mesma moeda
- **Como funciona:** Registra timestamp de cada trade aprovado e bloqueia novas tentativas por 120 segundos
- **Benefício:** Evita ansiedade excessiva e trades impulsivos na mesma moeda

```python
self.cooldown_seconds = 120  # 2 minutos entre trades da mesma moeda
```

### 2. ⏱️ TEMPO MÍNIMO DE HOLDING (Executor)
**Arquivo:** `bots/executor.py` - Função `gerenciar_trailing_stop()`

- **Adicionado:** Proteção de **30 segundos** mínimos antes de permitir venda
- **Como funciona:** Bloqueia venda imediata após compra, exceto em caso de perda extrema (>5%)
- **Benefício:** Dá tempo para o trade se desenvolver e evita vendas precipitadas

```python
tempo_minimo_holding = 30  # segundos
```

### 3. 📊 REDUÇÃO DE FREQUÊNCIA DE ANÁLISE (Sniper Monitor)
**Arquivo:** `sniper_monitor.py`

- **Mudança:** Análise reduzida de **a cada 3 ticks** para **a cada 5 ticks** quando sem posição
- **Como funciona:** Sistema só verifica oportunidades de compra com menos frequência
- **Benefício:** Reduz decisões impulsivas e carga de processamento

```python
# Antes: if self.ciclos_contador[symbol] % 3 != 0
# Agora:  if self.ciclos_contador[symbol] % 5 != 0
```

### 4. 💰 STOP LOSS E TAKE PROFIT AJUSTADOS (Executor)
**Arquivo:** `bots/executor.py` - Função `calcular_alvos()`

#### ANTES (Muito apertado - causava saídas prematuras):
```python
"scalping_v6": {"tp": 1.018, "sl": 0.992}  # TP: +1.8% | SL: -0.8%
```

#### AGORA (Mais respiração para o trade):
```python
"scalping_v6": {"tp": 1.025, "sl": 0.985}  # TP: +2.5% | SL: -1.5%
"meme_sniper": {"tp": 1.040, "sl": 0.975}  # TP: +4.0% | SL: -2.5%
"momentum_boost": {"tp": 1.030, "sl": 0.982}  # TP: +3.0% | SL: -1.8%
"layer2_defi": {"tp": 1.028, "sl": 0.985}  # TP: +2.8% | SL: -1.5%
"swing_rwa": {"tp": 1.035, "sl": 0.980}  # TP: +3.5% | SL: -2.0%
```

**Benefício:** 
- Stop Loss mais largo evita saídas por volatilidade normal
- Take Profit mais alto permite capturar movimentos maiores

### 5. 🎯 AJUSTE DE CONFIGURAÇÕES (settings.json)
**Arquivo:** `config/settings.json`

- **max_trades_simultaneos:** 20 → **15** (reduz exposição simultânea)
- **tp_pct:** 1.5% → **2.5%** (take profit mais alto)
- **sl_pct:** 0.8% → **1.5%** (stop loss mais largo)

## 📈 IMPACTO ESPERADO

### ✅ Melhorias Esperadas:
1. **Menos trades por dia** - Apenas oportunidades realmente boas
2. **Maior tempo por trade** - Mínimo 30 segundos, permitindo desenvolvimento
3. **Stop Loss mais inteligente** - Evita saídas por ruído de mercado
4. **Take Profit realista** - Captura movimentos maiores (+2.5% em vez de +1.8%)
5. **Sem duplicação** - Cooldown garante 2 minutos entre trades da mesma moeda

### 📊 Comparação de Parâmetros:

| Parâmetro | ANTES | AGORA | Melhoria |
|-----------|-------|-------|----------|
| Cooldown entre trades | ❌ Nenhum | ✅ 2 minutos | Evita overtrading |
| Tempo mínimo holding | ❌ Nenhum | ✅ 30 segundos | Dá tempo ao trade |
| Frequência análise | A cada 3 ticks | A cada 5 ticks | -40% decisões |
| Take Profit padrão | +1.8% | +2.5% | +39% ganho |
| Stop Loss padrão | -0.8% | -1.5% | +88% respiro |
| Max trades simultâneos | 20 | 15 | -25% exposição |

## 🎯 RESUMO TÉCNICO

### Problema Raiz:
- Sistema muito ansioso, executando trades a cada pequeno sinal
- Stop Loss muito apertado causando saídas prematuras
- Sem proteção contra trades repetidos da mesma moeda
- Sem tempo mínimo de permanência na posição

### Solução Implementada:
- **Cooldown temporal:** 2 min entre trades (mesmo ativo)
- **Holding mínimo:** 30 seg antes de permitir venda
- **SL mais largo:** -1.5% (em vez de -0.8%)
- **TP mais alto:** +2.5% (em vez de +1.8%)
- **Análise menos frequente:** 1 a cada 5 ticks

## 🔄 PRÓXIMOS PASSOS

1. **Testar o sistema** com as novas configurações
2. **Monitorar os logs** para confirmar:
   - Mensagens de cooldown aparecendo
   - Tempo mínimo de holding sendo respeitado
   - Menos trades por hora
3. **Ajustar se necessário** baseado nos resultados:
   - Se ainda muito rápido: aumentar cooldown para 3-5 minutos
   - Se muito lento: reduzir para 90 segundos

## ⚙️ VARIÁVEIS DE AMBIENTE DISPONÍVEIS

Para ajustes finos sem modificar código:

```env
# Tempo máximo de permanência (padrão: 72 horas)
R7_MAX_HOLD_HOURS=72

# Perda máxima permitida (padrão: 8%)
R7_MAX_LOSS_PCT=8.0

# Lucro rápido para fechar em < 4h (padrão: desabilitado)
R7_QUICK_PROFIT_PCT=0

# Margem de segurança nos TPs (padrão: 0.5%)
R7_SAFE_MARGIN_PCT=0.5

# Treino de IA no startup (padrão: true)
R7_TRAIN_ON_STARTUP=true
```

---

## 📅 Data da Correção
**10 de Janeiro de 2026**

**Status:** ✅ IMPLEMENTADO E PRONTO PARA TESTE

---

**IMPORTANTE:** Reinicie o sistema para aplicar todas as mudanças:
```powershell
python .\main.py
```
