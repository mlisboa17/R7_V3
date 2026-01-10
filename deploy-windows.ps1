# R7_V3 - Deploy para AWS EC2 (Windows)
# Execute este script no PowerShell como Administrador

param(
    [string]$PublicIP = "18.231.247.124",
    [string]$KeyPath = "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem",
    [string]$ProjectPath = "C:\Users\mlisb\PROJETOS_Local\R7_V3"
)

Write-Host "🚀 R7_V3 - Deploy para AWS EC2 (Windows)" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# Verificar se o arquivo de chave existe
if (!(Test-Path $KeyPath)) {
    Write-Host "❌ Arquivo de chave não encontrado: $KeyPath" -ForegroundColor Red
    exit 1
}

# Verificar se o projeto existe
if (!(Test-Path $ProjectPath)) {
    Write-Host "❌ Diretório do projeto não encontrado: $ProjectPath" -ForegroundColor Red
    exit 1
}

# Ajustar permissões da chave (se necessário)
Write-Host "🔐 Ajustando permissões da chave SSH..." -ForegroundColor Yellow
icacls $KeyPath /inheritance:r /grant:r "$env:USERNAME`:F" | Out-Null

# Função para executar comandos SSH
function Invoke-SSHCommand {
    param([string]$Command)
    $sshCmd = "ssh -i `"$KeyPath`" -o StrictHostKeyChecking=no ec2-user@$PublicIP `"$Command`""
    Write-Host "Executando: $Command" -ForegroundColor Gray
    try {
        $result = Invoke-Expression $sshCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $result
        } else {
            Write-Host "Erro no comando SSH: $result" -ForegroundColor Red
            return $null
        }
    } catch {
        Write-Host "Falha na conexão SSH: $_" -ForegroundColor Red
        return $null
    }
}

# Testar conexão SSH
Write-Host "🔗 Testando conexão SSH..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "echo 'SSH OK'"
if ($null -eq $result) {
    Write-Host "❌ Falha na conexão SSH. Verifique:" -ForegroundColor Red
    Write-Host "   - IP correto: $PublicIP" -ForegroundColor Red
    Write-Host "   - Chave correta: $KeyPath" -ForegroundColor Red
    Write-Host "   - Instância EC2 rodando" -ForegroundColor Red
    Write-Host "   - Security Group permite SSH (porta 22)" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Conexão SSH estabelecida!" -ForegroundColor Green

# Verificar se Docker está instalado
Write-Host "🐳 Verificando Docker..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "docker --version"
if ($null -eq $result) {
    Write-Host "📦 Instalando Docker..." -ForegroundColor Yellow
    Invoke-SSHCommand "sudo yum update -y"
    Invoke-SSHCommand "sudo yum install -y docker"
    Invoke-SSHCommand "sudo systemctl start docker"
    Invoke-SSHCommand "sudo systemctl enable docker"
    Invoke-SSHCommand "sudo usermod -a -G docker ec2-user"
}

# Instalar Docker Compose
Write-Host "🐙 Verificando Docker Compose..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "docker-compose --version"
if ($null -eq $result) {
    Write-Host "📦 Instalando Docker Compose..." -ForegroundColor Yellow
    Invoke-SSHCommand "sudo curl -L 'https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)' -o /usr/local/bin/docker-compose"
    Invoke-SSHCommand "sudo chmod +x /usr/local/bin/docker-compose"
}

# Clonar/atualizar repositório
Write-Host "📥 Clonando repositório..." -ForegroundColor Yellow
Invoke-SSHCommand "cd /home/ec2-user; rm -rf R7_V3"  # Limpar versão anterior se existir
Invoke-SSHCommand "cd /home/ec2-user; git clone https://github.com/mlisboa17/R7_V3.git"

# Copiar arquivos de configuração
Write-Host "📋 Copiando arquivos de configuração..." -ForegroundColor Yellow

# Verificar se existe .env local
$envPath = Join-Path $ProjectPath ".env"
if (Test-Path $envPath) {
    Write-Host "📄 Copiando arquivo .env..." -ForegroundColor Yellow
    # Usar scp para copiar o arquivo .env
    $scpCmd = "scp -i `"$KeyPath`" -o StrictHostKeyChecking=no `"$envPath`" ec2-user@${PublicIP}:/home/ec2-user/R7_V3/"
    Invoke-Expression $scpCmd
} else {
    Write-Host "⚠️  Arquivo .env não encontrado. Você precisa criá-lo." -ForegroundColor Yellow
}

# Configurar permissões
Write-Host "🔧 Configurando permissões..." -ForegroundColor Yellow
Invoke-SSHCommand "sudo chown -R ec2-user:ec2-user /home/ec2-user/R7_V3"
Invoke-SSHCommand "cd /home/ec2-user/R7_V3; chmod +x *.sh"

# Verificar arquivo .env
Write-Host "🔍 Verificando configuração..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "cd /home/ec2-user/R7_V3; grep -c 'your_binance_api_key_here' .env"
if ($result -and $result.Trim() -ne "0") {
    Write-Host "⚠️  CHAVES DA BINANCE NÃO CONFIGURADAS!" -ForegroundColor Yellow
    Write-Host "Edite o arquivo .env na instância EC2:" -ForegroundColor Yellow
    Write-Host "ssh -i '$KeyPath' ec2-user@$PublicIP" -ForegroundColor Yellow
    Write-Host "nano /home/ec2-user/R7_V3/.env" -ForegroundColor Yellow
    Write-Host "" -ForegroundColor Yellow
    Write-Host "Depois execute o deploy manualmente:" -ForegroundColor Yellow
    Write-Host "cd /home/ec2-user/R7_V3 && ./deploy-aws.sh deploy" -ForegroundColor Yellow
    exit 1
}

# Executar deploy
Write-Host "🚀 Executando deploy..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "cd /home/ec2-user/R7_V3; ./deploy-aws.sh deploy"

if ($null -eq $result) {
    Write-Host "❌ Falha no deploy" -ForegroundColor Red
    exit 1
}

# Aguardar inicialização
Write-Host "⏳ Aguardando inicialização dos serviços..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Verificar status
Write-Host "📊 Verificando status..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "cd /home/ec2-user/R7_V3; docker-compose ps"

if ($result -and $result -match "Up") {
    Write-Host ""
    Write-Host "🎉 DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 URLs de Acesso:" -ForegroundColor Cyan
    Write-Host "   Dashboard Streamlit: http://$PublicIP`:8501" -ForegroundColor Cyan
    Write-Host "   Interface Web:       http://$PublicIP`:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🔧 Comandos de gerenciamento:" -ForegroundColor Yellow
    Write-Host "   Ver logs:     ssh -i '$KeyPath' ec2-user@$PublicIP 'cd R7_V3; docker-compose logs -f'" -ForegroundColor Yellow
    Write-Host "   Reiniciar:   ssh -i '$KeyPath' ec2-user@$PublicIP 'cd R7_V3; docker-compose restart'" -ForegroundColor Yellow
    Write-Host "   Parar:       ssh -i '$KeyPath' ec2-user@$PublicIP 'cd R7_V3; docker-compose down'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📁 Arquivos na EC2: /home/ec2-user/R7_V3" -ForegroundColor Green
}
else {
    Write-Host "❌ Serviços não iniciaram corretamente" -ForegroundColor Red
    Write-Host "Verifique os logs:" -ForegroundColor Red
    Write-Host "ssh -i '$KeyPath' ec2-user@$PublicIP 'cd R7_V3; docker-compose logs'" -ForegroundColor Red
    exit 1
}