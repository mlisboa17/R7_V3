import logging
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools')))
from convert_to_stable import converter_lucro_para_stable
from .gestor_financeiro import GestorFinanceiro
import numpy as np
import sys
sys.path.append('..')
from utils.volatility import calculate_volatility

logger = logging.getLogger('estrategista')


class EstrategistaBot:
    def __init__(self, config):
        self.config = config
        self.open_positions = set()
        self.executor = None
        # Sabedoria: Meta fixa diária de 1% sobre os $2020
        # `GestorFinanceiro` aceita opcionalmente o saldo inicial do mês; usa meta interna fixa
        self.gestor = GestorFinanceiro()

    def set_executor(self, executor):
        self.executor = executor

    def iniciar_dia_trading(self):
        """Snapshot para o Dashboard e reset de metas diárias."""
        # Usa a banca de referência do config se disponível
        banca = self.config.get('banca_referencia_usdt', 2020.00) if isinstance(self.config, dict) else 2020.00
        self.gestor.registrar_inicio_dia(banca)
        logger.info(f"Dia iniciado. Meta: ${self.gestor.meta_diaria_fixa}")

    def analisar_tendencia(self, sinal):
        """
        Permite operar até 1,5% de lucro diário, mas para se recuar para 0,8% após ultrapassar 1%.
        """
        status = self.gestor.status_atual()
        saldo_inicial = status.get('saldo_inicial', 1710.36)
        lucro_dia = status.get('lucro_hoje', 0.0)
        meta_1pct = saldo_inicial * 0.01
        meta_1_5pct = saldo_inicial * 0.015
        meta_0_8pct = saldo_inicial * 0.008

        # Se já estiver posicionado na mesma moeda, ignora
        if sinal.get('symbol') in self.open_positions:
            return False


        # Se nunca atingiu 1% ainda, segue a meta padrão
        if lucro_dia < meta_1pct:
            return True

        # Se atingiu 1% mas não chegou a 1,5%, pergunta ao usuário se deseja vender
        if meta_1pct <= lucro_dia < meta_1_5pct:
            if not hasattr(self, '_perguntou_meta') or not self._perguntou_meta:
                from datetime import datetime
                if datetime.now().date().isoformat() == '2025-12-29':
                    self._perguntou_meta = True
                    if self.executor and hasattr(self.executor, 'comunicador') and self.executor.comunicador:
                        try:
                            from tools.analise_carteira import analisar_carteira_e_sugerir
                            api_key = os.getenv('BINANCE_API_KEY')
                            secret = os.getenv('BINANCE_SECRET_KEY')
                            total_usdt, total_lucro, sugestoes, acao = analisar_carteira_e_sugerir(api_key, secret)
                            sugestoes_str = '\n'.join(sugestoes)
                            # Identifica moedas com lucro relevante
                            moedas_vender = []
                            for s in sugestoes:
                                if 'lucro de $' in s and float(s.split('lucro de $')[1].split(' ')[0]) > 0:
                                    moedas_vender.append(s.split(':')[0])
                            if moedas_vender:
                                sugestao_criteriosa = f"Sugestão: vender as moedas {', '.join(moedas_vender)}."
                            else:
                                sugestao_criteriosa = "Nenhuma moeda com lucro relevante para venda imediata."
                        except Exception as e:
                            sugestoes_str = 'Não foi possível analisar a carteira.'
                            acao = ''
                            sugestao_criteriosa = ''
                        lucro_super_meta = meta_1_5pct
                        lucro_faltante = lucro_super_meta - lucro_dia
                        status_mercado = 'POSITIVO' if lucro_dia > 0 else 'NEGATIVO'
                        opcoes = (
                            "1️⃣ Vender apenas as moedas sugeridas",
                            "2️⃣ Vender toda a carteira",
                            "3️⃣ Esperar até a super meta de 1,5%",
                            "4️⃣ Não fazer nada hoje"
                        )
                        msg = (
                            f"Meta diária de 1% atingida!\n"
                            f"Lucro do dia: ${lucro_dia:.2f} USDT.\n"
                            f"Prefere tentar a super meta de 1,5%? Se atingir, o lucro será ${lucro_super_meta:.2f} USDT (faltam ${lucro_faltante:.2f}).\n"
                            f"Status do mercado hoje: {status_mercado}.\n"
                            f"\n{sugestao_criteriosa}\nResumo da carteira:\n{sugestoes_str}\n{acao}\n"
                            f"\nEscolha uma opção:\n" + '\n'.join(opcoes)
                        )
                        try:
                            import asyncio
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self.executor.comunicador._enviar(msg))
                            else:
                                loop.run_until_complete(self.executor.comunicador._enviar(msg))
                        except Exception as e:
                            logger.error(f'Erro ao enviar mensagem Telegram: {e}')
                else:
                    self._perguntou_meta = True
                    if self.executor and hasattr(self.executor, 'comunicador') and self.executor.comunicador:
                        # Comportamento padrão dos outros dias
                        try:
                            from tools.analise_carteira import analisar_carteira_e_sugerir
                            api_key = os.getenv('BINANCE_API_KEY')
                            secret = os.getenv('BINANCE_SECRET_KEY')
                            total_usdt, total_lucro, sugestoes, acao = analisar_carteira_e_sugerir(api_key, secret)
                            sugestoes_str = '\n'.join(sugestoes)
                        except Exception as e:
                            sugestoes_str = 'Não foi possível analisar a carteira.'
                            acao = ''
                        lucro_super_meta = meta_1_5pct
                        lucro_faltante = lucro_super_meta - lucro_dia
                        status_mercado = 'POSITIVO' if lucro_dia > 0 else 'NEGATIVO'
                        msg = (
                            f"Meta diária de 1% atingida!\n"
                            f"Lucro do dia: ${lucro_dia:.2f} USDT.\n"
                            f"Prefere tentar a super meta de 1,5%? Se atingir, o lucro será ${lucro_super_meta:.2f} USDT (faltam ${lucro_faltante:.2f}).\n"
                            f"Status do mercado hoje: {status_mercado}.\n"
                            f"\nResumo da carteira:\n{sugestoes_str}\n{acao}\n"
                            f"Deseja vender e encerrar o dia? Responda SIM para vender ou NÃO para continuar até a super meta."
                        )
                        try:
                            import asyncio
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self.executor.comunicador._enviar(msg))
                            else:
                                loop.run_until_complete(self.executor.comunicador._enviar(msg))
                        except Exception as e:
                            logger.error(f'Erro ao enviar mensagem Telegram: {e}')
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.executor.comunicador._enviar(msg))
                        else:
                            loop.run_until_complete(self.executor.comunicador._enviar(msg))
                    except Exception as e:
                        logger.error(f'Erro ao enviar mensagem Telegram: {e}')
            # Checa resposta do usuário
            if hasattr(self, '_resposta_meta'):
                if str(self._resposta_meta).strip().upper() == 'SIM':
                    try:
                        api_key = os.getenv('BINANCE_API_KEY')
                        secret = os.getenv('BINANCE_SECRET_KEY')
                        converter_lucro_para_stable(api_key, secret)
                        logger.info('Lucro convertido para USDT após resposta SIM na meta de 1%.')
                        if self.executor and hasattr(self.executor, 'comunicador') and self.executor.comunicador:
                            msg = 'Venda realizada e dia encerrado conforme solicitado.'
                            import asyncio
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self.executor.comunicador._enviar(msg))
                            else:
                                loop.run_until_complete(self.executor.comunicador._enviar(msg))
                    except Exception as e:
                        logger.error(f'Erro ao converter lucro para USDT: {e}')
                    return False
                elif str(self._resposta_meta).strip().upper() == 'NAO' or str(self._resposta_meta).strip().upper() == 'NÃO':
                    return True
            return False  # Aguarda resposta

        # Se já atingiu 1% e recuou para 0,8% ou menos, para tudo
        if lucro_dia <= meta_0_8pct:
            return False

        # Se já atingiu 1,5%, vende tudo automaticamente sem perguntar
        if lucro_dia >= meta_1_5pct:
            try:
                api_key = os.getenv('BINANCE_API_KEY')
                secret = os.getenv('BINANCE_SECRET_KEY')
                from tools.convert_to_stable import converter_lucro_para_stable
                converter_lucro_para_stable(api_key, secret)
                logger.info('Lucro convertido para USDT automaticamente ao bater 1,5% (super meta)')
                # Envia mensagem para o Telegram
                if self.executor and hasattr(self.executor, 'comunicador') and self.executor.comunicador:
                    msg = 'Meta diária de 1,5% (super meta) atingida! Todas as criptos foram vendidas automaticamente.'
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.executor.comunicador._enviar(msg))
                    else:
                        loop.run_until_complete(self.executor.comunicador._enviar(msg))
            except Exception as e:
                logger.error(f'Erro ao converter lucro para USDT: {e}')
                # Aviso no Telegram
                try:
                    if self.executor and hasattr(self.executor, 'comunicador') and self.executor.comunicador:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        msg = 'Falha na venda automática ao atingir a super meta. Favor realizar manualmente. As trades só serão retomadas amanhã.'
                        if loop.is_running():
                            asyncio.create_task(self.executor.comunicador._enviar(msg))
                        else:
                            loop.run_until_complete(self.executor.comunicador._enviar(msg))
                except Exception as e2:
                    logger.error(f'Erro ao enviar aviso Telegram: {e2}')
                return False
            return False

        return True

    def calcular_position_size(self, prices, saldo, risco_pct=0.01, window=14):
        """
        Calcula o tamanho da posição baseado na volatilidade (desvio padrão).
        - prices: lista de preços de fechamento recentes
        - saldo: saldo disponível
        - risco_pct: percentual do saldo a arriscar por trade
        - window: janela de volatilidade
        """
        vol = calculate_volatility(prices, window=window, method='std')
        if vol == 0:
            return 0
        valor_risco = saldo * risco_pct
        size = valor_risco / vol
        return max(0, int(size))

    def definir_stops(self, preco_entrada, prices, mult=2, window=14):
        """
        Define stop-loss e take-profit automáticos baseados na volatilidade.
        - mult: multiplicador da volatilidade para o stop
        """
        vol = calculate_volatility(prices, window=window, method='std')
        stop_loss = preco_entrada - mult * vol
        take_profit = preco_entrada + mult * vol
        return stop_loss, take_profit

    def mark_position_open(self, symbol):
        self.open_positions.add(symbol)

    def mark_position_closed(self, symbol, pnl):
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
            # Atualiza o lucro no gestor para controle de meta
            self.gestor.atualizar_lucro(pnl)