#!/bin/bash

# R7_V3 AWS Quick Deploy Script
# Uso rápido para deploy na AWS

echo "🚀 R7_V3 - Deploy Rápido para AWS"
echo "================================="

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI não instalado. Instale em: https://aws.amazon.com/cli/"
    exit 1
fi

# Verificar se está logado
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Não autenticado na AWS. Execute: aws configure"
    exit 1
fi

# Parâmetros
STACK_NAME="r7v3-trading-bot"
TEMPLATE_FILE="cloudformation.yml"
KEY_PAIR_NAME=${1:-"r7v3-keypair"}

echo "📦 Criando stack CloudFormation: $STACK_NAME"
echo "🔑 Key Pair: $KEY_PAIR_NAME"
echo ""

# Verificar se key pair existe
if ! aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" &> /dev/null; then
    echo "❌ Key pair '$KEY_PAIR_NAME' não encontrada."
    echo "Crie uma key pair em: https://console.aws.amazon.com/ec2/"
    exit 1
fi

# Criar stack
echo "⏳ Criando infraestrutura na AWS..."
aws cloudformation create-stack \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation.yml \
    --parameters ParameterKey=KeyName,ParameterValue="$KEY_PAIR_NAME" \
    --capabilities CAPABILITY_IAM \
    --on-failure DELETE

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Stack criada com sucesso!"
    echo ""
    echo "⏳ Aguardando criação da instância EC2..."

    # Aguardar stack creation
    aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME"

    # Obter outputs
    PUBLIC_IP=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' --output text)

    echo ""
    echo "🎉 Deploy concluído!"
    echo ""
    echo "📊 URLs de Acesso:"
    echo "   Dashboard:    http://$PUBLIC_IP:8501"
    echo "   Web Interface: http://$PUBLIC_IP:8080"
    echo ""
    echo "🔧 Próximos passos:"
    echo "   1. SSH: ssh -i ~/.ssh/$KEY_PAIR_NAME.pem ec2-user@$PUBLIC_IP"
    echo "   2. Configure o arquivo .env com suas chaves da Binance"
    echo "   3. Execute: cd R7_V3 && ./deploy-aws.sh restart"
    echo ""
    echo "📖 Documentação completa: https://github.com/mlisboa17/R7_V3"

else
    echo "❌ Erro ao criar stack. Verifique os logs acima."
    exit 1
fi