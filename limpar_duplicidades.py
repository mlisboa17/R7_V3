import sqlite3

conn = sqlite3.connect('memoria_bot.db')
cursor = conn.cursor()

try:
    # 1. Limpa todas as movimentações de hoje para começar do zero
    cursor.execute("DELETE FROM movimentacoes WHERE date(timestamp) = date('now')")

    # 2. Insere apenas os dois movimentos REAIS
    movimentos = [
        ('APORTE', 325.0, 'Aporte inicial consolidado'),
        ('REALOCADA', 279.0, 'Retirada de ADA para holding/Earn')
    ]

    cursor.executemany("INSERT INTO movimentacoes (tipo, valor, descricao) VALUES (?, ?, ?)", movimentos)

    # 3. Reseta o estado diário para o bot recalcular o saldo limpo no próximo boot
    cursor.execute("DELETE FROM daily_states WHERE data = date('now')")

    conn.commit()
    print("✅ Banco de dados limpo e consolidado com sucesso!")
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    conn.close()