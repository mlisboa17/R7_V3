# R7_V3 - Sistema de Trading Automatizado

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![AWS](https://img.shields.io/badge/AWS-Ready-orange.svg)](https://aws.amazon.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Sistema avançado de trading automatizado para criptomoedas utilizando inteligência artificial e análise técnica.

## 🚀 Funcionalidades

- 🤖 **Trading Automatizado**: Execução automática de ordens baseada em sinais de IA
- 📊 **Dashboard Interativo**: Interface Streamlit para monitoramento em tempo real
- 🔄 **WebSocket Resiliente**: Conexão estável com a Binance com retry automático
- 💰 **Gestão de Risco**: Controle automático de exposição e stop-loss
- 📱 **Notificações Telegram**: Alertas em tempo real via bot do Telegram
- 🐳 **Containerização**: Deploy simplificado com Docker
- ☁️ **AWS Ready**: Infraestrutura como código com CloudFormation

## 📋 Pré-requisitos

- Python 3.11+
- Docker & Docker Compose
- Conta Binance com API habilitada
- Conta AWS (opcional para deploy na nuvem)

## 🛠️ Instalação Local

### 1. Clone o repositório
```bash
git clone https://github.com/mlisboa17/R7_V3.git
cd R7_V3
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas chaves da Binance
```

### 4. Execute o sistema
```bash
# Modo desenvolvimento
python main.py

# Com Docker
docker-compose up --build
```

## ☁️ Deploy na AWS

### Opção 1: CloudFormation (Recomendado)

1. **Faça upload do template**:
   ```bash
   aws s3 cp cloudformation.yml s3://your-bucket/
   ```

2. **Crie a stack**:
   ```bash
   aws cloudformation create-stack \
     --stack-name r7v3-trading-bot \
     --template-url https://your-bucket.s3.amazonaws.com/cloudformation.yml \
     --parameters ParameterKey=KeyName,ParameterValue=your-keypair \
     --capabilities CAPABILITY_IAM
   ```

3. **Configure as chaves da API**:
   - Conecte via SSH na instância EC2
   - Edite o arquivo `/home/ec2-user/R7_V3/.env`
   - Reinicie os containers: `cd R7_V3 && ./deploy-aws.sh restart`

### Opção 2: Deploy Manual

1. **Crie uma instância EC2**:
   - AMI: Amazon Linux 2
   - Tipo: t3.medium ou superior
   - Configure Security Group (ports: 22, 8501, 8080)

2. **Conecte via SSH e execute**:
   ```bash
   # Na instância EC2
   sudo yum update -y
   sudo yum install -y git docker
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -a -G docker ec2-user

   # Instalar Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose

   # Clonar e configurar
   git clone https://github.com/mlisboa17/R7_V3.git
   cd R7_V3
   cp .env.example .env
   # Edite .env com suas chaves

   # Deploy
   chmod +x deploy-aws.sh
   ./deploy-aws.sh deploy
   ```

## 📊 Acessando as Interfaces

Após o deploy, acesse:

- **Dashboard Streamlit**: `http://SEU_IP_AWS:8501`
- **Interface Web**: `http://SEU_IP_AWS:8080`

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```env
# Binance API (obrigatório)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# AWS (opcional)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1

# Aplicação
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Configurações do Bot

Edite `config/settings.json` para ajustar:

- **Banca de referência**: Valor inicial da carteira
- **Meta diária**: Objetivo de lucro por dia
- **Símbolos monitorados**: Lista de criptos para trading
- **Estratégias**: Configuração de TP/SL por estratégia

## 📈 Estratégias Implementadas

1. **Scalping V6**: Trades rápidos com alvo de 1.2% e stop de 0.8%
2. **Momentum Boost**: Trades de médio prazo com alvo de 2.0%
3. **Swing RWA**: Trades de longo prazo com alvo de 4.5%

## 🔧 Comandos Úteis

```bash
# Desenvolvimento
python main.py --test          # Teste do sistema
python main.py --status        # Status atual

# Docker
docker-compose up -d           # Iniciar
docker-compose down            # Parar
docker-compose logs -f         # Ver logs

# AWS Deploy
./deploy-aws.sh deploy         # Deploy completo
./deploy-aws.sh restart        # Reiniciar
./deploy-aws.sh logs           # Ver logs
./deploy-aws.sh stop           # Parar aplicação
```

## 📊 Monitoramento

### Logs
- **Local**: `logs/r7_v3.log`
- **Docker**: `docker-compose logs r7v3-bot`
- **AWS**: CloudWatch Logs

### Métricas
- **Dashboard**: Interface visual em tempo real
- **Telegram**: Notificações automáticas
- **Logs**: Análise detalhada de operações

## 🚨 Segurança

- ✅ **Chaves API**: Armazenadas em variáveis de ambiente
- ✅ **Containerização**: Isolamento de processos
- ✅ **IAM Roles**: Permissões mínimas na AWS
- ✅ **Security Groups**: Acesso restrito por IP/porta
- ✅ **Logs**: Auditoria completa de operações

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## ⚠️ Aviso Legal

Este software é para fins educacionais e de pesquisa. O trading de criptomoedas envolve riscos significativos. Use por sua própria conta e risco. Os autores não se responsabilizam por perdas financeiras.

## 📞 Suporte

- **Issues**: [GitHub Issues](https://github.com/mlisboa17/R7_V3/issues)
- **Telegram**: Configure notificações automáticas
- **Logs**: Verifique `logs/r7_v3.log` para debugging

---

**Desenvolvido com ❤️ para a comunidade de traders**