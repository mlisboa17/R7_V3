# 🛡️ RELATÓRIO DE PROTEÇÕES DO SISTEMA R7_V3

## ✅ STATUS ATUAL (04/01/2026)

### 1. **EXECUTOR.PY** - Gestão de Carteira
**Localização:** `bots/executor.py` linha ~99

**Proteção Ativa:**
```python
# Proteção apenas para USDT (banca principal)
if asset == 'USDT' or quantidade <= 0:
    continue
```

**Moedas Protegidas:**
- ✅ **USDT** - Banca principal (CORRETO - não deve ser vendido)

**Moedas SEM Proteção (podem ser vendidas):**
- ✅ ADA - REMOVIDA a proteção
- ✅ MAGIC - Pode ser vendida
- ✅ Todas as outras altcoins

---

### 2. **SINCRONIZADOR.PY** - Sincronização de Posições
**Localização:** `sincronizador.py` linha ~24

**Proteção Ativa:**
```python
if asset in ['USDT', 'BNB', 'FDUSD']: continue  # Ignora moedas de taxa/estáveis
```

**Moedas Protegidas:**
- ✅ **USDT** - Stablecoin principal
- ✅ **BNB** - Taxa de transação da Binance
- ✅ **FDUSD** - Outra stablecoin

**Motivo:** Essas moedas não devem ser sincronizadas como "posições de trading" porque são:
- USDT: Banca operacional
- BNB: Reserva para pagar taxas
- FDUSD: Reserva stablecoin alternativa

---

### 3. **IA_SYNC_TOTAL.PY** - Sincronização com IA
**Localização:** `ia_sync_total.py` linha ~25

**Proteção Ativa:**
```python
if asset in ['USDT', 'BNB', 'FDUSD']: continue  # Moedas de taxa e reserva
```

**Moedas Protegidas:**
- ✅ **USDT** - Banca
- ✅ **BNB** - Taxa
- ✅ **FDUSD** - Reserva

---

### 4. **UPDATE_COMPOSITION.PY** - Atualização de Composição
**Localização:** `update_composition.py` linha ~77

**Proteção Ativa:**
```python
if asset in ['USDT', 'LDUSDT', 'FDUSD']:
    earn_usdt += total_amount
```

**Moedas Tratadas Especialmente:**
- ✅ **USDT** - Contabilizada como EARN
- ✅ **LDUSDT** - Contabilizada como EARN (Flexible Staking)
- ✅ **FDUSD** - Contabilizada como EARN

**Motivo:** Essas stablecoins no EARN não devem ser vendidas, apenas contabilizadas.

---

### 5. **LOCK_NOTIFIER.PY** - Notificador de Bloqueio
**Localização:** `tools/lock_notifier.py` linha ~66

**Proteção Ativa:**
```python
if asset.startswith("_") or asset in getattr(self.guardiao, 'ativos_ignorar', []):
    continue
```

**Moedas Protegidas:**
- Referencia a lista `ativos_ignorar` do Guardião (atualmente VAZIA)
- Ignora ativos que começam com "_" (metadados)

---

## 📊 RESUMO DE PROTEÇÕES ATIVAS

### 🚫 Moedas que NUNCA devem ser vendidas:
1. **USDT** - Banca operacional principal
2. **BNB** - Reserva para taxas de transação
3. **FDUSD** - Stablecoin alternativa
4. **LDUSDT** - USDT em Flexible Earn (Staking)

### ✅ Moedas que PODEM ser vendidas (SEM proteção):
1. **ADA** - Proteção removida em 04/01/2026
2. **MAGIC** - Sem proteção
3. **OG** - Sem proteção
4. **Todas as outras altcoins** - Sem proteção

---

## ⚙️ CONFIGURAÇÕES RECOMENDADAS

### Para manter moedas em HOLDING (não vender):
Você pode criar uma lista de holding no `config/settings.json`:

```json
{
  "holding_permanente": ["BTC", "ETH"],
  "holding_temporario": [],
  "stablecoins": ["USDT", "FDUSD", "LDUSDT"]
}
```

### Para adicionar proteção temporária:
Edite `bots/executor.py` linha ~99:
```python
# Exemplo: proteger BTC e ETH temporariamente
if asset in ['USDT', 'BTC', 'ETH'] or quantidade <= 0:
    continue
```

---

## 🔧 HISTÓRICO DE ALTERAÇÕES

- **04/01/2026 23:00** - Removida proteção da ADA em `executor.py`
- **04/01/2026 22:30** - Adicionado título "R7_V3" na janela do PowerShell

---

## ⚠️ IMPORTANTE

As proteções de **USDT, BNB e FDUSD** são **ESSENCIAIS** e **NÃO devem ser removidas**, pois:

- **USDT**: É sua banca. Vender USDT = não ter capital para operar
- **BNB**: Pagar taxas na Binance. Sem BNB = taxas mais altas
- **FDUSD**: Reserva de segurança em stablecoin

---

**Última Atualização:** 04/01/2026 23:15
**Status do Sistema:** ✅ Operacional
**Proteções Críticas:** ✅ Ativas e Funcionando
