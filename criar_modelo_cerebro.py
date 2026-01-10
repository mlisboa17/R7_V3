"""
🏗️ CRIADOR DE MODELO CEREBRO STOP LOSS
Cria modelo de exemplo para testes (RandomForest treinado com dados sintéticos)
"""
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import os

print("🏗️ Criando modelo Cérebro Stop Loss...")

# Cria diretório se não existir
os.makedirs('models', exist_ok=True)

# Dados sintéticos de treino
# Features: [rsi, ema20, atr_pct, rel_vol]
np.random.seed(42)

# Situações que devem RENOVAR (label=1)
# - RSI < 30 (oversold)
# - ATR alto (volatilidade)
renovar_data = np.array([
    [25, 44500, 2.5, 1.2],  # RSI baixo
    [28, 44000, 3.0, 1.5],
    [22, 43500, 2.8, 1.3],
    [30, 44200, 2.6, 1.4],
    [27, 43800, 2.9, 1.1],
] * 20)  # Multiplica para ter mais exemplos

# Situações que devem VENDER (label=0)
# - RSI alto (overbought)
# - ATR baixo (sem volatilidade)
vender_data = np.array([
    [65, 45000, 1.0, 0.8],  # RSI alto
    [70, 45500, 0.9, 0.7],
    [75, 46000, 0.8, 0.6],
    [68, 45200, 1.1, 0.9],
    [72, 45800, 0.95, 0.75],
] * 20)

# Junta dados
X = np.vstack([renovar_data, vender_data])
y = np.array([1] * len(renovar_data) + [0] * len(vender_data))

# Treina modelo
print("🏋️  Treinando Random Forest...")
modelo = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
modelo.fit(X, y)

# Testa accuracy
accuracy = modelo.score(X, y)
print(f"✅ Modelo treinado com {accuracy:.1%} de accuracy")

# Salva modelo
model_path = 'models/cerebro_r7_v3.pkl'
joblib.dump(modelo, model_path)
print(f"💾 Modelo salvo em: {model_path}")

# Testa carregamento
print("\n🧪 Testando carregamento...")
modelo_carregado = joblib.load(model_path)
print("✅ Modelo carregado com sucesso!")

# Testa predição
print("\n🎯 Testando predições:")

# Caso 1: RSI baixo (deve RENOVAR)
teste_renovar = [[25, 44000, 2.8, 1.3]]
pred = modelo_carregado.predict(teste_renovar)[0]
print(f"   RSI=25 (baixo) → {'RENOVAR' if pred == 1 else 'VENDER'} {'✅' if pred == 1 else '❌'}")

# Caso 2: RSI alto (deve VENDER)
teste_vender = [[70, 45000, 1.0, 0.8]]
pred = modelo_carregado.predict(teste_vender)[0]
print(f"   RSI=70 (alto)  → {'RENOVAR' if pred == 1 else 'VENDER'} {'✅' if pred == 0 else '❌'}")

print("\n✅ Modelo pronto para uso!")
print("💡 Execute: python testar_cerebro_stop_loss.py")
