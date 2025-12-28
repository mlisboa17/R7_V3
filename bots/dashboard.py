import logging

class Dashboard:
    def __init__(self, executor, guardiao, config, estrategista=None):
        self.executor = executor
        self.guardiao = guardiao
        self.config = config
        self.estrategista = estrategista

    def gerar_resumo(self):
        # Consulta o saldo real na Binance via Estrategista (método completo)
        saldo_usdt = self.estrategista.get_account_balance_usdt() if self.estrategista else 0.0 
        lucro_hoje = self.guardiao.lucro_dia
        meta = self.config.get('config_geral', {}).get('meta_diaria_total_usdt', 20.20)
        
        # Calcula quanto USDT está em ordens abertas AGORA
        exposicao = len(self.executor.active_trades) * 100  # Aproximação: 4 trades max * $100

        # Monta a string do Dashboard
        dash = (
            f"📊 *DASHBOARD R7_V3 REAL-TIME*\n"
            f"--------------------------\n"
            f"💰 *USDT Líquido:* ${saldo_usdt:.2f}\n"
            f"📈 *Lucro do Dia:* ${lucro_hoje:.2f}\n"
            f"🎯 *Meta Diária:* ${meta:.2f}\n"
            f"⚔️ *Exposição:* ${exposicao:.2f}\n"
            f"--------------------------\n"
            f"🚀 *Status:* {'🔥 ATACANDO' if exposicao > 0 else '🔍 OBSERVANDO'}\n"
            f"🕒 *Atualizado:* Agora"
        )
        return dash