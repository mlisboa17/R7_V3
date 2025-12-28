"Você é o desenvolvedor sênior responsável pelo projeto R7_V3. O objetivo é criar um sistema de trading multi-agente (4 bots especialistas) para operar Meme Coins na rede Solana.

CONTEXTO FINANCEIRO E META:

Capital Atual: R$ 9.847,11 (Dividido em R$ 7.931,09 no EARN e R$ 1.916,02 no SPOT).

Objetivo: Recuperar um déficit de R$ 2.272,89 e alcançar uma meta de 1% de lucro ao dia (aprox. R$ 98,47) sobre o capital total.

Operacional: Entradas fixas de $30 USD por operação, utilizando apenas o saldo do SPOT para manter o EARN protegido.

SUA MISSÃO:

Verificação de Duplicidade: Analise todos os códigos e instruções que eu já forneci anteriormente. Identifique funções repetidas ou lógicas conflitantes e consolide-as em uma estrutura única e limpa. Não duplique processos de monitoramento.

Arquitetura Multi-Agente:

Bot Analista: Filtra tokens com liquidez > $5.000 e faz check-up anti-rugpull.

Bot Estrategista: Define o timing de entrada baseado em volume e tendência.

Bot Guardião: Trava o sistema ao atingir o lucro diário de 1% ou um stop loss de 0.5%.

Bot Executor: Realiza a ordem via API (Jupiter/Raydium) 24/7.

Otimização de Performance: O código deve ser 'headless' (sem interface gráfica), rodando em Python de forma leve para não pesar na máquina local, preparado para futura migração para AWS.

REQUISITOS TÉCNICOS:

Utilize WebSockets para dados em tempo real (baixa latência).

Implemente logs detalhados na pasta /logs para auditoria de cada decisão.

Garanta que a lógica de 'Consenso' esteja ativa: a ordem só é enviada se o Analista, o Estrategista e o Guardião derem sinal VERDE simultaneamente."