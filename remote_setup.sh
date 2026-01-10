#!/bin/bash
sudo yum update -y
sudo yum install -y python3 python3-pip
pip3 install --user python-binance pandas numpy scikit-learn streamlit asyncio websockets requests
mkdir -p ~/r7_trading
cd ~/r7_trading
echo "Pronto para upload manual dos arquivos"
