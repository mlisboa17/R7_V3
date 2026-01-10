# R7_V3 Bot Deploy Script
echo "🚀 Configurando ambiente R7_V3..."

# Update system
sudo yum update -y
sudo yum install -y python3 python3-pip git htop

# Install Python packages
pip3 install --user python-binance pandas numpy scikit-learn streamlit asyncio websockets requests python-dotenv aiofiles

# Create directory
mkdir -p ~/r7_trading
cd ~/r7_trading

echo "✅ Ambiente preparado!"
echo "📁 Diretório: ~/r7_trading"
echo "📦 Agora faça upload dos arquivos:"
echo "   - main.py"
echo "   - .env"
echo "   - cerebro_ia.joblib"
echo "   - pasta bots/"
echo "   - pasta config/"
echo ""
echo "🚀 Para executar: python3 main.py"