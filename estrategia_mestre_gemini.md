# 🛡️ Estratégia de Trading Algorítmico - High Performance

## 1. Filosofia de Execução
- **Ativos Tier 1 (BTC/ETH):** Foco em acumulação e proteção de capital.
- **Ativos Tier 2 (Alts/Utility):** Foco em arbitragem e reversão à média.
- **Ativos Tier 3 (Memes/Degen):** Foco em momentum, monitoramento on-chain e saídas rápidas.

## 2. Pilares do Bot
1. **Dados em Tempo Real:** Uso híbrido de REST (Snapshot) + WebSockets (Update).
2. **Gestão de Risco:** Nunca expor mais de 2% do capital por trade.
3. **Saída Dinâmica:** Trailing Stop e realização de lucro parcial (Take Profit escalonado).
4. **Fator Psicológico:** O bot executa onde o humano hesita.

## 3. Checklist de Operação
- [ ] Verificar Funding Rates (Se muito alto, evitar longs).
- [ ] Checar Liquidez do par (Evitar slippage alto em Memes).
- [ ] Validar conexão com a API (Keep-alive do ListenKey).