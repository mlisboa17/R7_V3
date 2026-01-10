## 🚀 DEPLOY NA NUVEM - INSTRUÇÕES DIRETAS

### 📋 PASSO 1: Conecte na instância EC2
1. Abra nova aba: https://sa-east-1.console.aws.amazon.com/ec2/home?region=sa-east-1#Instances:
2. Clique na instância `i-0754deeabc809cdea`
3. Clique em "Conectar"
4. Selecione "EC2 Instance Connect"
5. Clique "Conectar"

### 📦 PASSO 2: Preparar ambiente
Cole estes comandos no terminal que abrir:

```bash
# Atualizar sistema
sudo yum update -y

# Instalar Python e dependências
sudo yum install -y python3 python3-pip git

# Instalar bibliotecas Python
pip3 install --user python-binance pandas numpy scikit-learn streamlit asyncio websockets requests python-dotenv

# Criar diretório
mkdir -p ~/r7_trading
cd ~/r7_trading

# Download do código (você precisará fazer upload manual)
echo "Sistema preparado para receber arquivos R7_V3"
```

### 📁 PASSO 3: Upload de arquivos
Você terá que fazer upload manual dos arquivos:
- main.py
- .env (com suas credenciais Binance)
- cerebro_ia.joblib
- pasta bots/
- pasta config/

### 🔧 PASSO 4: Executar na nuvem
```bash
cd ~/r7_trading
nohup python3 main.py > bot.log 2>&1 &
```

### 📊 PASSO 5: Monitorar
```bash
tail -f bot.log
```

## 🎯 CONEXÃO:
**IP:** 56.125.172.137
**Instância:** i-0754deeabc809cdea
**Region:** sa-east-1