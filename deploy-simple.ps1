# Deploy Simples R7_V3 para AWS EC2

$PublicIP = "18.231.247.124"
$KeyPath = "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem"

Write-Host "🚀 Deploy Simples R7_V3" -ForegroundColor Green

# Testar conexão SSH
Write-Host "🔗 Testando SSH..." -ForegroundColor Yellow
$test = ssh -i $KeyPath -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$PublicIP "echo 'OK'" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ SSH falhou. Verifique a chave e IP." -ForegroundColor Red
    exit 1
}

Write-Host "✅ SSH OK" -ForegroundColor Green

# Instalar Docker se necessário
Write-Host "🐳 Instalando Docker..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$PublicIP "sudo yum update -y; sudo yum install -y docker; sudo systemctl start docker; sudo systemctl enable docker; sudo usermod -a -G docker ec2-user"

# Instalar Docker Compose
Write-Host "🐙 Instalando Docker Compose..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$PublicIP "sudo curl -L 'https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)' -o /usr/local/bin/docker-compose; sudo chmod +x /usr/local/bin/docker-compose"

# Clonar projeto
Write-Host "📥 Baixando projeto..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$PublicIP "cd /home/ec2-user; rm -rf R7_V3; git clone https://github.com/mlisboa17/R7_V3.git; sudo chown -R ec2-user:ec2-user R7_V3"

# Configurar permissões
Write-Host "🔧 Configurando..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$PublicIP "cd /home/ec2-user/R7_V3; chmod +x *.sh"

Write-Host "⚠️  IMPORTANTE: Configure suas chaves da Binance!" -ForegroundColor Yellow
Write-Host "Execute: ssh -i '$KeyPath' ec2-user@$PublicIP" -ForegroundColor Yellow
Write-Host "Depois: nano /home/ec2-user/R7_V3/.env" -ForegroundColor Yellow
Write-Host "Depois: cd /home/ec2-user/R7_V3; ./deploy-aws.sh deploy" -ForegroundColor Yellow

Write-Host "Deploy preparado!" -ForegroundColor Green