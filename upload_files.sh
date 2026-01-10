# Upload via SCP para Ubuntu
scp -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" -r *.py ubuntu@56.125.172.137:~/r7_trading/
scp -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" .env ubuntu@56.125.172.137:~/r7_trading/
scp -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" cerebro_ia.joblib ubuntu@56.125.172.137:~/r7_trading/
scp -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" -r bots ubuntu@56.125.172.137:~/r7_trading/
scp -i "C:\Users\mlisb\OneDrive\Desktop\r7_trade_key.pem" -r config ubuntu@56.125.172.137:~/r7_trading/