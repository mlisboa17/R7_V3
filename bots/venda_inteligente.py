"""
🎯 SISTEMA DE VENDA INTELIGENTE V2 - Baseado em Previsões
Melhora significativamente as vendas usando:
1. Previsões de tempo para cada moeda
2. Venda dinâmica baseada no cenário atingido
3. Stop loss inteligente por categoria
4. Venda escalonada por cenário
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger('venda_inteligente')

class VendaInteligente:
    """Sistema avançado de venda baseado em previsões e cenários"""
    
    def __init__(self):
        # Configurações de venda por cenário
        self.config_vendas = {
            'conservador': {
                'percent_sell': 30,  # Vende 30% quando atinge cenário conservador
                'hold_for_realista': True,  # Aguarda cenário realista
                'description': 'Meta mínima atingida - venda parcial'
            },
            'realista': {
                'percent_sell': 70,  # Vende 70% quando atinge cenário realista  
                'hold_for_otimista': True,  # Aguarda cenário otimista se volume alto
                'description': 'Meta principal atingida - venda majoritária'
            },
            'otimista': {
                'percent_sell': 100,  # Vende tudo quando atinge cenário otimista
                'hold_for_otimista': False,
                'description': 'Meta máxima atingida - venda total'
            }
        }
        
        # Critérios para forçar venda por tempo (aumentado para dar mais chance ao realista)
        self.tempo_limits = {
            'MEME': 48,      # 48h máximo para memes (era 36h)
            'BLUE_CHIP': 96, # 96h para blue chips (era 72h)
            'DEFI': 72,      # 72h para DeFi (era 48h)
            'LAYER2': 72     # 72h para Layer2 (era 48h)
        }
    
    def analisar_situacao_venda(
        self, 
        symbol: str,
        preco_atual: float,
        preco_entrada: float,
        tempo_posicao_horas: float,
        previsao: Optional[Dict] = None,
        categoria: str = 'DEFI'
    ) -> Dict[str, Any]:
        """
        Analisa a situação atual e decide estratégia de venda
        """
        lucro_atual = ((preco_atual / preco_entrada) - 1) * 100
        tempo_decorrido = tempo_posicao_horas
        
        resultado = {
            'deve_vender': False,
            'percentual_venda': 0,
            'motivo': '',
            'cenario_atingido': None,
            'urgencia': 'BAIXA',
            'lucro_atual': lucro_atual,
            'tempo_decorrido_horas': tempo_decorrido,
            'recomendacao': '',
            'acao_recomendada': 'AGUARDAR'
        }
        
        # 1. VERIFICAÇÃO POR PREVISÃO (se disponível)
        if previsao and 'cenarios' in previsao:
            cenario_atingido = self._verificar_cenario_atingido(lucro_atual, previsao['cenarios'])
            
            if cenario_atingido:
                # CORREÇÃO CRÍTICA: Implementa paciência para cenários maiores
                tempo_conservador = previsao['cenarios'].get('conservador', {}).get('eta_horas', 2)
                tempo_realista = previsao['cenarios'].get('realista', {}).get('eta_horas', 4) 
                
                # REGRA 1: Conservador atingido muito cedo? Aguarda realista
                if cenario_atingido == 'conservador':
                    # Se ainda tem tempo para o realista (menos de 75% do tempo previsto)
                    if tempo_decorrido < (tempo_realista * 0.75):
                        resultado.update({
                            'deve_vender': False,
                            'acao_recomendada': 'AGUARDAR_REALISTA',
                            'motivo': f'Conservador({lucro_atual:.1f}%) OK, aguardando realista em {tempo_realista - tempo_decorrido:.1f}h',
                            'cenario_atingido': cenario_atingido,
                            'urgencia': 'BAIXA'
                        })
                        return resultado
                    else:
                        # Tempo quase esgotando, vende conservador
                        config_venda = self.config_vendas[cenario_atingido]
                
                # REGRA 2: Realista atingido cedo? Aguarda otimista se há tempo
                elif cenario_atingido == 'realista':
                    tempo_otimista = previsao['cenarios'].get('otimista', {}).get('eta_horas', 8)
                    # Se ainda tem tempo para otimista (menos de 60% do tempo)
                    if tempo_decorrido < (tempo_otimista * 0.60):
                        # Venda parcial (50%) e aguarda otimista
                        config_venda = {'percent_sell': 50, 'description': 'Venda parcial, aguardando otimista'}
                    else:
                        # Venda realista normal (70%)
                        config_venda = self.config_vendas[cenario_atingido]
                else:
                    # Cenário otimista - vende tudo
                    config_venda = self.config_vendas[cenario_atingido]
                
                # Se chegou até aqui, deve vender
                if 'config_venda' in locals():
                    resultado.update({
                        'deve_vender': True,
                        'acao_recomendada': f'VENDER {config_venda["percent_sell"]}%',
                        'percentual_venda': config_venda['percent_sell'],
                        'motivo': f"Cenário {cenario_atingido} atingido ({lucro_atual:.1f}%)",
                        'cenario_atingido': cenario_atingido,
                        'urgencia': self._calcular_urgencia(cenario_atingido, tempo_decorrido, previsao),
                        'recomendacao': config_venda['description']
                    })
                return resultado
        
        # 2. VERIFICAÇÃO POR TEMPO LIMITE - MAS RESPEITA PREVISÕES (NÃO VENDE COM PREJUÍZO)
        tempo_limite = self.tempo_limits.get(categoria, 48)
        if tempo_decorrido >= tempo_limite:
            # ✅ NÃO força venda no prejuízo - respeita as previsões!
            # Se tem previsão ativa, aguarda o resultado dela
            if previsao:
                resultado.update({
                    'deve_vender': False,
                    'acao_recomendada': 'AGUARDAR_PREVISAO',
                    'motivo': f"Tempo limite atingido ({tempo_decorrido:.1f}h), mas mantendo por previsão ativa",
                    'urgencia': 'ALTA',  # Urgência alta mas sem forçar venda
                    'recomendacao': 'Monitorando previsão - não vender com prejuízo'
                })
            else:
                # Sem previsão: só vende se lucro >= 0
                if lucro_atual >= 0:
                    resultado.update({
                        'deve_vender': True,
                        'percentual_venda': 100,
                        'motivo': f"Tempo limite esgotado ({tempo_decorrido:.1f}h >= {tempo_limite}h), com lucro",
                        'urgencia': 'ALTA',
                        'recomendacao': 'Saída por gestão de tempo (sem previsão ativa)'
                    })
                else:
                    # Sem previsão e no prejuízo: aguarda reversão
                    resultado.update({
                        'deve_vender': False,
                        'acao_recomendada': 'AGUARDAR_REVERSAO',
                        'motivo': f"Tempo limite atingido mas no prejuízo ({lucro_atual:.2f}%) - aguardando reversão",
                        'urgencia': 'CRITICA',
                        'recomendacao': 'Monitorar de perto mas não liquidar no prejuízo'
                    })
            return resultado
        
        # 3. VERIFICAÇÃO POR DETERIORAÇÃO (sem previsão)
        if not previsao:
            # Fallback: critérios tradicionais melhorados
            if lucro_atual >= 4.0:  # 4%+ lucro
                resultado.update({
                    'deve_vender': True,
                    'percentual_venda': 60,
                    'motivo': f"Lucro significativo sem previsão ({lucro_atual:.1f}%)",
                    'urgencia': 'MÉDIA',
                    'recomendacao': 'Venda parcial por precaução'
                })
            elif lucro_atual <= -3.0:  # -3% perda
                resultado.update({
                    'deve_vender': True,
                    'percentual_venda': 100,
                    'motivo': f"Stop loss acionado ({lucro_atual:.1f}%)",
                    'urgencia': 'CRÍTICA',
                    'recomendacao': 'Cortar perdas imediatamente'
                })
        
        return resultado
    
    def _verificar_cenario_atingido(self, lucro_atual: float, cenarios: Dict) -> Optional[str]:
        """Verifica qual cenário foi atingido baseado no lucro atual"""
        
        # Verifica do maior para o menor
        for nome in ['otimista', 'realista', 'conservador']:
            if nome in cenarios:
                lucro_meta = cenarios[nome]['lucro_pct']
                if lucro_atual >= lucro_meta:
                    return nome
        
        return None
    
    def _calcular_urgencia(self, cenario: str, tempo_decorrido: float, previsao: Dict) -> str:
        """Calcula urgência da venda baseada no cenário e tempo"""
        
        # Se atingiu otimista, urgência sempre alta
        if cenario == 'otimista':
            return 'CRÍTICA'
        
        # Se passou muito do tempo previsto, urgência sobe
        if 'cenarios' in previsao and cenario in previsao['cenarios']:
            tempo_previsto = previsao['cenarios'][cenario]['eta_horas']
            if tempo_decorrido > (tempo_previsto * 1.5):
                return 'ALTA'
            elif tempo_decorrido > tempo_previsto:
                return 'MÉDIA'
        
        return 'BAIXA'
    
    def calcular_stop_loss_dinamico(
        self, 
        symbol: str, 
        lucro_atual: float,
        tempo_decorrido: float,
        previsao: Optional[Dict] = None
    ) -> Tuple[bool, float, str]:
        """
        Calcula stop loss dinâmico baseado em previsão e tempo
        Retorna: (deve_parar, percentual_sl, motivo)
        """
        
        # Stop loss básico por categoria
        categoria = self._get_categoria(symbol)
        sl_basico = {
            'MEME': -4.0,      # -4% para memes
            'BLUE_CHIP': -2.0, # -2% para blue chips
            'DEFI': -3.0,      # -3% para DeFi
            'LAYER2': -2.5     # -2.5% para Layer2
        }.get(categoria, -3.0)
        
        # Se tem previsão, ajusta stop loss baseado no tempo esperado
        if previsao and 'cenarios' in previsao:
            tempo_conservador = previsao['cenarios'].get('conservador', {}).get('eta_horas', 12)
            
            # Se ainda está dentro do tempo esperado, é mais flexível
            if tempo_decorrido < tempo_conservador:
                sl_ajustado = sl_basico * 0.8  # 20% mais flexível
                motivo = f"Dentro do prazo ({tempo_decorrido:.1f}h < {tempo_conservador}h)"
            # Se passou do tempo, fica mais rigoroso  
            elif tempo_decorrido > tempo_conservador * 2:
                sl_ajustado = sl_basico * 1.5  # 50% mais rigoroso
                motivo = f"Muito atrasado ({tempo_decorrido:.1f}h > {tempo_conservador*2}h)"
            else:
                sl_ajustado = sl_basico
                motivo = "Padrão"
        else:
            sl_ajustado = sl_basico
            motivo = "Sem previsão"
        
        deve_parar = lucro_atual <= sl_ajustado
        
        return deve_parar, sl_ajustado, motivo
    
    def _get_categoria(self, symbol: str) -> str:
        """Determina categoria da moeda"""
        if not symbol:
            return 'DEFI'
            
        # Moedas MEME
        meme_coins = ['PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK', 'FLOKI']
        if any(meme in symbol.upper() for meme in meme_coins):
            return 'MEME'
            
        # Blue Chips  
        blue_chips = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP']
        if any(blue in symbol.upper() for blue in blue_chips):
            return 'BLUE_CHIP'
            
        # Layer 2
        layer2_coins = ['ARB', 'POL', 'MATIC', 'OP', 'METIS']
        if any(l2 in symbol.upper() for l2 in layer2_coins):
            return 'LAYER2'
            
        return 'DEFI'
    
    def gerar_relatorio_decisao(self, analise: Dict[str, Any]) -> str:
        """Gera relatório amigável da decisão de venda"""
        
        if not analise['deve_vender']:
            return f"🔒 MANTER posição | Lucro: {analise['lucro_atual']:+.2f}% | Tempo: {analise['tempo_decorrido_horas']:.1f}h"
        
        urgencia_emoji = {
            'BAIXA': '🟢',
            'MÉDIA': '🟡', 
            'ALTA': '🟠',
            'CRÍTICA': '🔴'
        }.get(analise['urgencia'], '⚪')
        
        return (
            f"{urgencia_emoji} VENDER {analise['percentual_venda']}% | "
            f"Lucro: {analise['lucro_atual']:+.2f}% | "
            f"Motivo: {analise['motivo']} | "
            f"Urgência: {analise['urgencia']}"
        )