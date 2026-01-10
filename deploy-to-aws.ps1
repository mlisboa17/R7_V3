# R7_V3 AWS Deploy Script
param(
    [string]$InstanceIP = "18.231.247.124",
    [string]$KeyPath = "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem",
    [string]$ProjectPath = "C:\Users\mlisb\PROJETOS_Local\R7_V3"
)

Write-Host "R7_V3 - Deploy para AWS EC2" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green
Write-Host "IP: $InstanceIP" -ForegroundColor Yellow
Write-Host "Chave: $KeyPath" -ForegroundColor Yellow
Write-Host ""

# Verificar se arquivos existem
if (!(Test-Path $KeyPath)) {
    Write-Host "ERRO: Arquivo de chave nao encontrado: $KeyPath" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $ProjectPath)) {
    Write-Host "ERRO: Diretorio do projeto nao encontrado: $ProjectPath" -ForegroundColor Red
    exit 1
}

# Função para executar comandos SSH
function Invoke-SSHCommand {
    param([string]$Command)
    $sshCmd = "ssh -o StrictHostKeyChecking=no -i `"$KeyPath`" ec2-user@$InstanceIP `"$Command`""
    Write-Host "Executando: $Command" -ForegroundColor Cyan
    try {
        $result = Invoke-Expression $sshCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCESSO: Comando executado" -ForegroundColor Green
            return $result
        } else {
            Write-Host "ERRO no comando: $result" -ForegroundColor Red
            return $null
        }
    } catch {
        Write-Host "ERRO de conexao: $_" -ForegroundColor Red
        return $null
    }
}

# Testar conexão SSH
Write-Host "Testando conexao SSH..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "echo 'SSH funcionando - $(date)'"
if (!$result) {
    Write-Host "ERRO: Falha na conexao SSH. Verifique:" -ForegroundColor Red
    Write-Host "   - IP da instancia: $InstanceIP" -ForegroundColor Yellow
    Write-Host "   - Arquivo de chave: $KeyPath" -ForegroundColor Yellow
    Write-Host "   - Security Group permite SSH (porta 22)" -ForegroundColor Yellow
    exit 1
}

Write-Host "SUCESSO: Conexao SSH estabelecida" -ForegroundColor Green

# Instalar Docker e dependências
Write-Host "Instalando Docker na instancia..." -ForegroundColor Yellow
Invoke-SSHCommand "sudo yum update -y"
Invoke-SSHCommand "sudo yum install -y docker git"
Invoke-SSHCommand "sudo systemctl start docker"
Invoke-SSHCommand "sudo systemctl enable docker"
Invoke-SSHCommand "sudo usermod -a -G docker ec2-user"

# Instalar Docker Compose
Write-Host "Instalando Docker Compose..." -ForegroundColor Yellow
Invoke-SSHCommand "sudo curl -L 'https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)' -o /usr/local/bin/docker-compose"
Invoke-SSHCommand "sudo chmod +x /usr/local/bin/docker-compose"

# Criar diretório do projeto
Write-Host "Criando diretorio do projeto..." -ForegroundColor Yellow
Invoke-SSHCommand "mkdir -p ~/R7_V3"

# Copiar arquivos via SCP
Write-Host "Copiando arquivos do projeto..." -ForegroundColor Yellow
$scpCmd = "scp -i `"$KeyPath`" -r `"$ProjectPath\*`" ec2-user@${InstanceIP}:~/R7_V3/"
Write-Host "Executando copia: $scpCmd" -ForegroundColor Cyan

try {
    $result = Invoke-Expression $scpCmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCESSO: Arquivos copiados" -ForegroundColor Green
    } else {
        Write-Host "ERRO ao copiar arquivos: $result" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERRO ao copiar arquivos: $_" -ForegroundColor Red
    exit 1
}

# Configurar permissões
Write-Host "Configurando permissoes..." -ForegroundColor Yellow
Invoke-SSHCommand "chmod +x ~/R7_V3/deploy-aws.sh"
Invoke-SSHCommand "chmod +x ~/R7_V3/deploy-aws-quick.sh"

# Criar arquivo .env básico
Write-Host "Criando arquivo .env..." -ForegroundColor Yellow
$envContent = @"
# Configure suas chaves da Binance aqui
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Configuracoes da aplicacao
LOG_LEVEL=INFO
ENVIRONMENT=production
"@

$tempEnvFile = [System.IO.Path]::GetTempFileName()
$envContent | Out-File -FilePath $tempEnvFile -Encoding UTF8

# Copiar arquivo .env
Write-Host "Copiando arquivo .env..." -ForegroundColor Yellow
$scpEnvCmd = "scp -i '$KeyPath' '$tempEnvFile' ec2-user@${InstanceIP}:~/R7_V3/.env"
Write-Host "Executando: $scpEnvCmd" -ForegroundColor Cyan
$result = Invoke-Expression $scpEnvCmd 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCESSO: Arquivo .env copiado" -ForegroundColor Green
} else {
    Write-Host "ERRO ao copiar .env: $result" -ForegroundColor Red
}

# Limpar arquivo temporário
Remove-Item $tempEnvFile

# Executar deploy
Write-Host "Executando deploy da aplicacao..." -ForegroundColor Yellow
$result = Invoke-SSHCommand "~/R7_V3/deploy-aws.sh deploy"

if ($result) {
    Write-Host "" -ForegroundColor Green
    Write-Host "DEPLOY CONCLUIDO COM SUCESSO!" -ForegroundColor Green
    Write-Host "" -ForegroundColor Green
    Write-Host "URLs de Acesso:" -ForegroundColor Cyan
    Write-Host "   Dashboard Streamlit: http://$InstanceIP`:8501" -ForegroundColor White
    Write-Host "   Interface Web:       http://$InstanceIP`:8080" -ForegroundColor White
    Write-Host "" -ForegroundColor Green
    Write-Host "IMPORTANTE:" -ForegroundColor Yellow
    Write-Host "   1. Configure o arquivo .env com suas chaves da Binance" -ForegroundColor White
    Write-Host "   2. Execute: ssh -i '$KeyPath' ec2-user@$InstanceIP" -ForegroundColor White
    Write-Host "   3. Edite: nano ~/R7_V3/.env" -ForegroundColor White
    Write-Host "   4. Reinicie: cd ~/R7_V3 && ./deploy-aws.sh restart" -ForegroundColor White
    Write-Host "" -ForegroundColor Green
} else {
    Write-Host "ERRO durante o deploy. Verifique os logs acima." -ForegroundColor Red
    exit 1
}