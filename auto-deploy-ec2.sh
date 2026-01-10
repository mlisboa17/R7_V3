#!/bin/bash

# R7_V3 - Deploy Automático na AWS EC2
# Script executado via AWS CLI

set -e

echo "🚀 R7_V3 - Deploy Automático na AWS EC2"
echo "======================================="

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função de log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Deploy via User Data
log "Iniciando setup do ambiente..."

# Atualizar sistema
sudo yum update -y

# Instalar dependências
sudo yum install -y python3 python3-pip git htop

# Instalar bibliotecas Python
log "Instalando bibliotecas Python..."
pip3 install --user python-binance pandas numpy scikit-learn streamlit asyncio websockets requests python-dotenv aiofiles

# Criar diretório do projeto
log "Configurando diretório do projeto..."
mkdir -p /home/ec2-user/r7_trading
cd /home/ec2-user/r7_trading

# Verificar se estamos no EC2
if [ -z "$EC2_INSTANCE" ]; then
    EC2_INSTANCE=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "")
fi

if [ -n "$EC2_INSTANCE" ]; then
    log "Executando na instância EC2: $EC2_INSTANCE"
else
    warning "Não detectado como EC2. Executando em modo local."
fi

# Atualizar sistema
log "Atualizando sistema..."
sudo yum update -y
sudo yum install -y git docker htop

# Instalar Docker Compose
log "Instalando Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Iniciar Docker
log "Configurando Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Criar diretório do projeto
log "Clonando repositório..."
cd /home/ec2-user
if [ -d "R7_V3" ]; then
    cd R7_V3
    git pull origin main
else
    git clone https://github.com/mlisboa17/R7_V3.git
    cd R7_V3
fi

# Configurar permissões
log "Configurando permissões..."
sudo chown -R ec2-user:ec2-user /home/ec2-user/R7_V3

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    log "Criando arquivo .env..."
    cat > .env << 'EOF'
# Configure suas chaves da Binance aqui
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Configurações da aplicação
LOG_LEVEL=INFO
ENVIRONMENT=production
EOF
    warning "Arquivo .env criado. Você precisa configurar suas chaves da Binance!"
else
    log "Arquivo .env já existe."
fi

# Tornar scripts executáveis
log "Configurando scripts..."
chmod +x deploy-aws.sh
chmod +x deploy-aws-quick.sh

# Verificar se as chaves estão configuradas
if grep -q "your_binance_api_key_here" .env; then
    warning "⚠️  CHAVES DA BINANCE NÃO CONFIGURADAS!"
    warning "Edite o arquivo .env com suas chaves antes de continuar:"
    warning "nano /home/ec2-user/R7_V3/.env"
    warning ""
    warning "Depois execute: ./deploy-aws.sh deploy"
    exit 1
fi

# Deploy da aplicação
log "Iniciando deploy da aplicação..."
./deploy-aws.sh deploy

# Verificar status
log "Verificando status..."
sleep 10

if docker-compose ps | grep -q "Up"; then
    log "✅ Aplicação implantada com sucesso!"

    # Obter IP público
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")

    echo ""
    echo "🎉 DEPLOY CONCLUÍDO!"
    echo ""
    echo "📊 URLs de Acesso:"
    if [ "$PUBLIC_IP" != "unknown" ]; then
        echo "   Dashboard Streamlit: http://$PUBLIC_IP:8501"
        echo "   Interface Web:       http://$PUBLIC_IP:8080"
    else
        echo "   Dashboard Streamlit: http://[IP_PUBLICO]:8501"
        echo "   Interface Web:       http://[IP_PUBLICO]:8080"
    fi
    echo ""
    echo "🔧 Comandos úteis:"
    echo "   Ver logs:           docker-compose logs -f"
    echo "   Reiniciar:          docker-compose restart"
    echo "   Parar:              docker-compose down"
    echo ""
    echo "📁 Diretório: /home/ec2-user/R7_V3"
    echo "📄 Config:    nano /home/ec2-user/R7_V3/.env"

else
    error "❌ Falha no deploy. Verificando logs..."
    docker-compose logs
    exit 1
fi