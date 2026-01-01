import json
import os

def check_travas_direto():
    # Caminhos dos arquivos de dados
    path_account = 'data/account_composition.json'
    
    if os.path.exists(path_account):
        with open(path_account, 'r', encoding='utf-8') as f:
            data = json.load(f)
            exposicao = data.get('_total_usdt', 0)
            print(f"📊 EXPOSIÇÃO ATUAL: ${exposicao:.2f}")
            
            # Se a exposição estiver acima de 600, o bot NUNCA vai comprar
            if exposicao >= 600:
                print("🚨 TRAVA ATIVA: Limite de exposição ($600) atingido!")
            else:
                print("✅ Exposição abaixo do limite de $600. Possível liberar compras.")
    else:
        print("❌ Arquivo de conta não encontrado.")

if __name__ == '__main__':
    check_travas_direto()
