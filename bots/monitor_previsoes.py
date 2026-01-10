"""
📡 MONITOR DE PREVISÕES - Sistema Assíncrono de Acompanhamento
Roda em background a cada 15 minutos, atualiza previsões e salva histórico
NÃO BLOQUEIA OS BOTS PRINCIPAIS
"""

import logging
import asyncio
import json
from datetime import datetime
from pathlib import Path
from bots.previsao_engine import PrevisaoEngine

logger = logging.getLogger('monitor_previsoes')

class MonitorPrevisoes:
    """Bot assíncrono que monitora e atualiza previsões"""
    
    def __init__(self, client, executor):
        self.client = client
        self.executor = executor
        self.previsao_engine = PrevisaoEngine(client)
        self.arquivo_historico = Path('previsoes_historico.json')
        self.intervalo_atualizacao = 15 * 60  # 15 minutos em segundos
        self.running = False
        self.task = None
        
        # Carrega histórico existente
        self.historico = self._carregar_historico()
    
    def _carregar_historico(self):
        """Carrega histórico de previsões do arquivo JSON"""
        if self.arquivo_historico.exists():
            try:
                with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"✅ Histórico carregado: {len(data)} posições")
                return data
            except Exception as e:
                logger.error(f"❌ Erro ao carregar histórico: {e}")
                return {}
        return {}
    
    def _salvar_historico(self):
        """Salva histórico atualizado no arquivo JSON"""
        try:
            with open(self.arquivo_historico, 'w', encoding='utf-8') as f:
                json.dump(self.historico, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Histórico salvo: {len(self.historico)} posições")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar histórico: {e}")
    
    def _gerar_chave_posicao(self, symbol, entry_time):
        """Gera chave única para identificar posição"""
        if isinstance(entry_time, str):
            dt = datetime.fromisoformat(entry_time)
        else:
            dt = entry_time
        return f"{symbol}_{dt.strftime('%Y%m%d_%H%M%S')}"
    
    async def registrar_nova_posicao(self, symbol, entry_price, entry_time=None):
        """
        🆕 REGISTRA NOVA POSIÇÃO - Chamado pelo Executor após compra
        Cria previsão inicial de forma assíncrona (não bloqueia)
        """
        if entry_time is None:
            entry_time = datetime.now()
        
        # Cria task assíncrona para não bloquear
        asyncio.create_task(self._criar_previsao_inicial(symbol, entry_price, entry_time))
        logger.info(f"📝 Nova posição registrada para previsão: {symbol}")
    
    async def _criar_previsao_inicial(self, symbol, entry_price, entry_time):
        """Cria previsão inicial (roda em background)"""
        try:
            # Gera previsão completa
            previsao = await self.previsao_engine.gerar_previsao(symbol, entry_price, entry_time)
            
            # Cria chave única
            chave = self._gerar_chave_posicao(symbol, entry_time)
            
            # Adiciona ao histórico
            self.historico[chave] = {
                'symbol': symbol,
                'entry_price': entry_price,
                'entry_time': entry_time.isoformat() if not isinstance(entry_time, str) else entry_time,
                'categoria': previsao['categoria'],
                'previsao_inicial': previsao,
                'atualizacoes': [],  # Lista de atualizações a cada 15min
                'status': 'ABERTA',
                'venda': None
            }
            
            # Salva no arquivo
            self._salvar_historico()
            
            logger.info(f"✅ Previsão inicial criada: {symbol} | {previsao['cenarios']['realista']['lucro_pct']:.1f}% em {previsao['cenarios']['realista']['eta_horas']:.1f}h")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar previsão inicial para {symbol}: {e}")
    
    async def atualizar_posicao(self, chave):
        """Atualiza uma posição específica com preço atual"""
        try:
            posicao = self.historico[chave]
            symbol = posicao['symbol']
            
            # Busca preço atual
            ticker = await self.client.get_symbol_ticker(symbol=symbol)
            preco_atual = float(ticker['price'])
            
            # Calcula divergência
            previsao_original = posicao['previsao_inicial']
            divergencia = self.previsao_engine.atualizar_divergencia(previsao_original, preco_atual)
            
            # Adiciona à lista de atualizações
            posicao['atualizacoes'].append(divergencia)
            
            # Log resumido
            logger.info(f"🔄 {symbol}: {divergencia['lucro_atual_pct']:+.2f}% | {divergencia['status']} | Vel: {divergencia['divergencia_velocidade_pct']:+.1f}%")
            
            return divergencia
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar {chave}: {e}")
            return None
    
    async def registrar_venda(self, symbol, preco_venda, lucro_pct, motivo):
        """
        ✅ REGISTRA VENDA - Chamado pelo Executor após venda
        Fecha posição no histórico e calcula acurácia
        """
        try:
            # Busca posição ativa correspondente
            chave_encontrada = None
            for chave, posicao in self.historico.items():
                if posicao['symbol'] == symbol and posicao['status'] == 'ABERTA':
                    chave_encontrada = chave
                    break
            
            if not chave_encontrada:
                logger.warning(f"⚠️ Posição não encontrada no histórico: {symbol}")
                return
            
            posicao = self.historico[chave_encontrada]
            entry_time = datetime.fromisoformat(posicao['entry_time'])
            tempo_real = (datetime.now() - entry_time).total_seconds() / 3600  # horas
            
            # Determina qual cenário foi atingido
            cenarios = posicao['previsao_inicial']['cenarios']
            if lucro_pct >= cenarios['otimista']['lucro_pct'] * 0.9:  # 90% do otimista
                cenario_atingido = 'otimista'
            elif lucro_pct >= cenarios['realista']['lucro_pct'] * 0.9:
                cenario_atingido = 'realista'
            elif lucro_pct >= cenarios['conservador']['lucro_pct'] * 0.9:
                cenario_atingido = 'conservador'
            else:
                cenario_atingido = 'nenhum'
            
            # Calcula acurácia temporal
            if cenario_atingido != 'nenhum':
                eta_previsto = cenarios[cenario_atingido]['eta_horas']
                divergencia_tempo = ((tempo_real - eta_previsto) / eta_previsto) * 100 if eta_previsto > 0 else 0
                
                if abs(divergencia_tempo) <= 20:
                    acuracia = "PRECISO"
                elif abs(divergencia_tempo) <= 50:
                    acuracia = "ACEITAVEL"
                else:
                    acuracia = "DIVERGENTE"
            else:
                acuracia = "FALHOU"
                divergencia_tempo = None
            
            # Registra venda
            posicao['venda'] = {
                'timestamp': datetime.now().isoformat(),
                'preco_venda': preco_venda,
                'lucro_pct': lucro_pct,
                'tempo_real_horas': round(tempo_real, 2),
                'cenario_atingido': cenario_atingido,
                'acuracia': acuracia,
                'divergencia_tempo_pct': round(divergencia_tempo, 1) if divergencia_tempo else None,
                'motivo': motivo
            }
            posicao['status'] = 'FECHADA'
            
            # Salva no arquivo
            self._salvar_historico()
            
            logger.info(f"✅ VENDA REGISTRADA: {symbol} | Lucro: {lucro_pct:.2f}% | Cenário: {cenario_atingido} | Acurácia: {acuracia}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao registrar venda de {symbol}: {e}")
    
    async def _loop_monitoramento(self):
        """Loop principal de monitoramento (roda a cada 15 min)"""
        logger.info("🚀 Monitor de Previsões iniciado (intervalo: 15 min)")
        
        while self.running:
            try:
                # Filtra apenas posições abertas
                posicoes_abertas = [
                    chave for chave, posicao in self.historico.items()
                    if posicao['status'] == 'ABERTA'
                ]
                
                if posicoes_abertas:
                    logger.info(f"🔄 Atualizando {len(posicoes_abertas)} posições abertas...")
                    
                    # Atualiza todas as posições
                    for chave in posicoes_abertas:
                        await self.atualizar_posicao(chave)
                        await asyncio.sleep(0.5)  # Evita rate limit
                    
                    # Salva histórico atualizado
                    self._salvar_historico()
                    logger.info("✅ Atualização concluída")
                else:
                    logger.debug("📭 Nenhuma posição aberta para atualizar")
                
                # Aguarda 15 minutos
                await asyncio.sleep(self.intervalo_atualizacao)
                
            except asyncio.CancelledError:
                logger.info("🛑 Monitor de Previsões cancelado")
                break
            except Exception as e:
                logger.error(f"❌ Erro no loop de monitoramento: {e}")
                await asyncio.sleep(60)  # Aguarda 1 min antes de tentar novamente
    
    async def iniciar(self):
        """Inicia o monitor em background"""
        if self.running:
            logger.warning("⚠️ Monitor já está rodando")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._loop_monitoramento())
        logger.info("✅ Monitor de Previsões iniciado em background")
    
    async def parar(self):
        """Para o monitor"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Salva histórico final
        self._salvar_historico()
        logger.info("🛑 Monitor de Previsões parado")
    
    def gerar_relatorio_acuracia(self):
        """
        📊 Gera relatório de acurácia das previsões
        Útil para avaliar performance do modelo
        """
        posicoes_fechadas = [
            p for p in self.historico.values()
            if p['status'] == 'FECHADA' and p['venda']
        ]
        
        if not posicoes_fechadas:
            return {"total": 0, "message": "Nenhuma posição fechada para análise"}
        
        total = len(posicoes_fechadas)
        precisos = sum(1 for p in posicoes_fechadas if p['venda']['acuracia'] == 'PRECISO')
        aceitaveis = sum(1 for p in posicoes_fechadas if p['venda']['acuracia'] == 'ACEITAVEL')
        
        cenarios_atingidos = {}
        for p in posicoes_fechadas:
            cenario = p['venda']['cenario_atingido']
            cenarios_atingidos[cenario] = cenarios_atingidos.get(cenario, 0) + 1
        
        return {
            'total_posicoes': total,
            'precisos': precisos,
            'aceitaveis': aceitaveis,
            'taxa_acerto': round((precisos + aceitaveis) / total * 100, 1),
            'cenarios_atingidos': cenarios_atingidos
        }
