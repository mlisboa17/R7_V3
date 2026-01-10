#!/bin/bash

# R7_V3 AWS Deployment Script
# Este script configura e implanta o bot R7_V3 na AWS

set -e

echo "🚀 Iniciando deployment do R7_V3 para AWS..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se as variáveis de ambiente estão configuradas
check_env_vars() {
    echo -e "${YELLOW}Verificando variáveis de ambiente...${NC}"

    if [ -z "$BINANCE_API_KEY" ]; then
        echo -e "${RED}Erro: BINANCE_API_KEY não configurada${NC}"
        exit 1
    fi

    if [ -z "$BINANCE_SECRET_KEY" ]; then
        echo -e "${RED}Erro: BINANCE_SECRET_KEY não configurada${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Variáveis de ambiente OK${NC}"
}

# Instalar Docker e Docker Compose
install_docker() {
    echo -e "${YELLOW}Instalando Docker...${NC}"

    # Update system
    sudo apt-get update

    # Install required packages
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo \
        "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker

    # Add user to docker group
    sudo usermod -aG docker $USER

    echo -e "${GREEN}✓ Docker instalado com sucesso${NC}"
}

# Configurar firewall
configure_firewall() {
    echo -e "${YELLOW}Configurando firewall...${NC}"

    # Allow SSH
    sudo ufw allow ssh

    # Allow web ports
    sudo ufw allow 8501
    sudo ufw allow 8080

    # Enable firewall
    echo "y" | sudo ufw enable

    echo -e "${GREEN}✓ Firewall configurado${NC}"
}

# Configurar aplicação
setup_application() {
    echo -e "${YELLOW}Configurando aplicação...${NC}"

    # Criar arquivo .env
    cat > .env << EOF
BINANCE_API_KEY=$BINANCE_API_KEY
BINANCE_SECRET_KEY=$BINANCE_SECRET_KEY
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
LOG_LEVEL=INFO
ENVIRONMENT=production
EOF

    echo -e "${GREEN}✓ Arquivo .env criado${NC}"
}

# Iniciar aplicação
start_application() {
    echo -e "${YELLOW}Iniciando aplicação...${NC}"

    # Parar containers existentes
    docker-compose down || true

    # Construir e iniciar containers
    docker-compose up -d --build

    echo -e "${GREEN}✓ Aplicação iniciada${NC}"
}

# Verificar status
check_status() {
    echo -e "${YELLOW}Verificando status...${NC}"

    # Aguardar containers iniciarem
    sleep 10

    # Verificar containers
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Containers estão rodando${NC}"

        # Mostrar status
        docker-compose ps

        # Mostrar logs iniciais
        echo -e "${YELLOW}Logs iniciais:${NC}"
        docker-compose logs --tail=20 r7v3-bot

    else
        echo -e "${RED}✗ Erro: Containers não iniciaram corretamente${NC}"
        docker-compose logs
        exit 1
    fi
}

# Menu principal
main() {
    echo -e "${GREEN}=== R7_V3 AWS Deployment ===${NC}"

    case "${1:-deploy}" in
        "install")
            check_env_vars
            install_docker
            configure_firewall
            ;;
        "deploy")
            check_env_vars
            setup_application
            start_application
            check_status
            ;;
        "restart")
            docker-compose restart
            check_status
            ;;
        "stop")
            docker-compose down
            echo -e "${GREEN}✓ Aplicação parada${NC}"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            ;;
        *)
            echo "Uso: $0 {install|deploy|restart|stop|logs|status}"
            echo ""
            echo "Comandos:"
            echo "  install  - Instala Docker e configura o sistema"
            echo "  deploy   - Implanta a aplicação (padrão)"
            echo "  restart  - Reinicia a aplicação"
            echo "  stop     - Para a aplicação"
            echo "  logs     - Mostra logs em tempo real"
            echo "  status   - Mostra status dos containers"
            exit 1
            ;;
    esac
}

# Executar menu principal
main "$@"