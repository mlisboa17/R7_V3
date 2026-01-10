# R7_V3 Deployment Package
# Este arquivo contém os passos para deploy manual

## 1. Criar arquivo ZIP com o projeto
Write-Host "Criando pacote de deploy..." -ForegroundColor Green
Compress-Archive -Path *.py, *.json, *.txt, *.md, bots\*, config\*, .env -DestinationPath R7_V3_Deploy.zip -Force

## 2. Preparar script de instalacao remota
$setupScript = @'
#!/bin/bash
sudo yum update -y
sudo yum install -y python3 python3-pip
pip3 install --user python-binance pandas numpy scikit-learn streamlit asyncio websockets requests
mkdir -p ~/r7_trading
cd ~/r7_trading
echo "Pronto para upload manual dos arquivos"
'@

$setupScript | Out-File -FilePath "remote_setup.sh" -Encoding utf8

Write-Host "Pacote criado: R7_V3_Deploy.zip" -ForegroundColor Green
Write-Host "Script remoto: remote_setup.sh" -ForegroundColor Green
Write-Host "IP da instancia: 56.125.172.137" -ForegroundColor Yellow