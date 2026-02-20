import undetected_chromedriver as uc
import pandas as pd
import time
import sys
from selenium.webdriver.common.by import By

# --- CONFIGURAÇÃO DOS PARTICIPANTES ---
# Lista oficial mantida conforme o seu arquivo original
PARTICIPANTES = [
    {"nome": "gfelicio", "id": "325002"},
    {"nome": "wEs", "id": "1718975"},
    {"nome": "BioAlarcon", "id": "1823210"},
    {"nome": "JOGod", "id": "1480613"},
    {"nome": "ManoShaco", "id": "2053668"},
    {"nome": "Anjoz", "id": "2153414"},
    {"nome": "TioZo", "id": "515855"},
    {"nome": "MARMOT", "id": "1116597"},
]

def iniciar_driver():
    print("🔄 Iniciando Google Chrome indetectável no Mac...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    
    try:
        # use_subprocess é mantido para estabilidade no macOS
        driver = uc.Chrome(options=options, use_subprocess=True)
        return driver
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        print("Tente fechar todas as janelas do Chrome e rode 'pkill -f chrome' no terminal.")
        sys.exit(1)

def extrair_dados_dashboard(driver, player):
    nome = player['nome']
    player_id = player['id']
    
    print(f"\n--- 👤 Analisando: {nome} ---")
    driver.get(f"https://cs.gamersclub.gg/player/{player_id}/statistics")
    
    print(f"📍 Aguardando você carregar o dashboard de {nome}...")
    input(f"👉 Escolha o mês no navegador e, quando os números aparecerem, aperte ENTER aqui...")

    dados = {"player": nome, "id": player_id}
    
    try:
        # Busca os blocos de estatísticas
        items = driver.find_elements(By.CLASS_NAME, "StatsBoxPlayerInfoItem__Content")
        
        if not items:
            print(f"⚠️  Dados não encontrados para {nome}. A página está logada?")
            return None

        for item in items:
            try:
                # Captura o nome original da métrica
                label_raw = item.find_element(By.CLASS_NAME, "StatsBoxPlayerInfoItem__name").text.lower()
                valor = item.find_element(By.CLASS_NAME, "StatsBoxPlayerInfoItem__value").text
                
                # --- ALTERAÇÃO NECESSÁRIA PARA O WINRATE ---
                # Garante que variações como "Win Rate" ou "Vitórias" sejam salvas como "winrate" 
                if "win rate" in label_raw or "vitória" in label_raw or "winrate" in label_raw:
                    label = "winrate"
                else:
                    # Mantém a padronização original para as outras métricas
                    label = label_raw.replace(" ", "_").replace("%", "_pct")
                
                dados[label] = valor
            except:
                continue
        
        print(f"✅ {nome} processado!")
        return dados
    except Exception as e:
        print(f"❌ Erro em {nome}: {e}")
        return None

if __name__ == "__main__":
    driver = iniciar_driver()
    todos_os_stats = []

    try:
        print("\n🔑 PASSO 1: Faça login no Chrome que abriu.")
        input("✅ Após logar, pressione ENTER aqui para iniciar a rodada com os 8 amigos...")

        for p in PARTICIPANTES:
            resultado = extrair_dados_dashboard(driver, p)
            if resultado:
                todos_os_stats.append(resultado)
            time.sleep(1)

    finally:
        print("\n🏁 Coleta finalizada. Gerando arquivo...")
        driver.quit()

    if todos_os_stats:
        df = pd.DataFrame(todos_os_stats)
        # Gera o CSV que alimenta o seu App principal
        df.to_csv("ranking_bagre_do_mes.csv", index=False, encoding="utf-8-sig")
        
        print(f"\n✨ SUCESSO, GUSTAVO!")
        print(f"📂 Arquivo gerado: ranking_bagre_do_mes.csv")
        print("-" * 60)
        
        if 'kdr' in df.columns:
            df['kdr_n'] = pd.to_numeric(df['kdr'], errors='coerce')
            print("🏆 QUEM É O BAGRE? (Ordenado por KDR):")
            print(df.sort_values(by='kdr_n')[['player', 'kdr', 'adr']].to_string(index=False))
    else:
        print("\n🛑 Erro: Nenhum dado coletado.")