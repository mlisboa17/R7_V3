#!/bin/bash
yum update -y
yum install -y git docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /home/ec2-user
git clone https://github.com/mlisboa17/R7_V3.git
cd R7_V3

# Create .env file with your keys
cat > .env << 'EOF'
BINANCE_API_KEY=mlLPDlgPTtQCGSzTDesQgwOedGztWONPNstvq6agcdQhzIMawArw8919OP1qjzwB
BINANCE_SECRET_KEY=8Ll5QUMxI0H6dMJIjOKa0mfOKw39jWHoTU0IToDhmfB2CfUgQGb6ZiOxFWnk0lZX
TELEGRAM_BOT_TOKEN=8552932858:AAHNYSLiT2kod2eNJNKzWzuQ1r56XPW9lfQ
TELEGRAM_CHAT_ID=8483312482
LOG_LEVEL=INFO
ENVIRONMENT=production
REAL_TRADING=1
GUARDIAO_ENABLED=1
EOF

# Make scripts executable
chmod +x deploy-aws.sh

# Change ownership
chown -R ec2-user:ec2-user /home/ec2-user/R7_V3

# Start the application as ec2-user
su - ec2-user -c "cd /home/ec2-user/R7_V3 && ./deploy-aws.sh deploy"