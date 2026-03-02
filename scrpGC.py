import undetected_chromedriver as uc
import pandas as pd
import time
import sys
import os
import datetime
from selenium.webdriver.common.by import By

# --- CONFIGURAÇÃO DOS PARTICIPANTES ---
PARTICIPANTES = [
    {"nome": "gfelicio", "id": "325002"},
    {"nome": "wEs", "id": "1718975"},
    {"nome": "BioAlarcon", "id": "1823210"},
    {"nome": "JOGod", "id": "1480613"},
    {"nome": "ManoShaco", "id": "2053668"},
    {"nome": "Anjoz", "id": "2153414"},
    {"nome": "TioZo", "id": "515855"},
    {"nome": "MARMOT", "id": "1116597"},
    {"nome": "Baludinho", "id": "1571977"},
]

def iniciar_driver():
    print("🔄 Iniciando Google Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    
    try:
        driver = uc.Chrome(version_main=145, options=options, use_subprocess=True)
        return driver
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        sys.exit(1)

def extrair_dados_dashboard(driver, player):
    nome = player['nome']
    player_id = player['id']
    
    print(f"\n--- 👤 Analisando: {nome} ---")
    driver.get(f"https://cs.gamersclub.gg/player/{player_id}")
    
    print(f"📍 Aguardando você carregar o dashboard de {nome}...")
    input(f"👉 Escolha o mês no navegador e, quando os números aparecerem, aperte ENTER aqui...")

    # Forçamos a criação da coluna 'partidas' aqui com um valor padrão (N/D)
    dados = {"player": nome, "id": player_id, "partidas": "N/D"} 
    
    try:
        items = driver.find_elements(By.CLASS_NAME, "StatsBoxPlayerInfoItem__Content")
        
        if not items:
            print(f"⚠️ Dados não encontrados para {nome}.")
            return dados # Retorna pelo menos o nome e a coluna de partidas vazia

        for item in items:
            try:
                label_raw = item.find_element(By.CLASS_NAME, "StatsBoxPlayerInfoItem__name").text.lower()
                valor = item.find_element(By.CLASS_NAME, "StatsBoxPlayerInfoItem__value").text
                
                if any(x in label_raw for x in ["win rate", "vitória", "winrate"]):
                    dados["winrate"] = valor
                elif any(x in label_raw for x in ["partidas", "matches", "jogos"]):
                    dados["partidas"] = valor # Se achar o valor real, ele substitui o "N/D"
                else:
                    label = label_raw.replace(" ", "_").replace("%", "_pct")
                    dados[label] = valor
            except:
                continue
        
        return dados
    except Exception as e:
        print(f"❌ Erro em {nome}: {e}")
        return dados # Mesmo com erro, retorna o que tem para não quebrar o CSV
    
if __name__ == "__main__":
    driver = iniciar_driver()
    todos_os_stats = []

    try:
        print("\n🔑 PASSO 1: Faça login no Chrome que abriu.")
        input("✅ Após logar, pressione ENTER aqui para iniciar a rodada com os participantes...")

        for p in PARTICIPANTES:
            resultado = extrair_dados_dashboard(driver, p)
            if resultado:
                todos_os_stats.append(resultado)
            time.sleep(1)

    finally:
        print("\n🏁 Coleta finalizada. Processando arquivos...")
        driver.quit()

    if todos_os_stats:
        df_novo = pd.DataFrame(todos_os_stats)
        
        # 1. Carimbo de Data para o Histórico
        mes_atual = datetime.datetime.now().strftime("%Y-%m")
        df_novo['mes'] = mes_atual

        # 2. Salva o arquivo do mês atual (Dashboard Principal)
        df_novo.to_csv("ranking_bagre_do_mes.csv", index=False, encoding="utf-8-sig")

        # 3. Lógica de Histórico Acumulado
        ARQUIVO_HIST = "historico_gc_geral.csv"
        
        if os.path.exists(ARQUIVO_HIST):
            df_antigo = pd.read_csv(ARQUIVO_HIST)
            # Une o antigo com o novo e remove duplicatas (mesmo player no mesmo mês)
            df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=['player', 'mes'], keep='last')
        else:
            df_final = df_novo

        df_final.to_csv(ARQUIVO_HIST, index=False, encoding="utf-8-sig")
        
        print(f"\n✨ SUCESSO, GUSTAVO!")
        print(f"📂 Arquivo do Mês: ranking_bagre_do_mes.csv")
        print(f"📈 Arquivo Histórico: {ARQUIVO_HIST}")
        print("-" * 60)
        
        # Preview do Ranking
        if 'kdr' in df_novo.columns:
            df_novo['kdr_n'] = pd.to_numeric(df_novo['kdr'].str.replace(',', '.'), errors='coerce')
            print("🏆 PREVIEW DO RANKING (Ordenado por KDR):")
            print(df_novo.sort_values(by='kdr_n')[['player', 'kdr', 'partidas']].to_string(index=False))
    else:
        print("\n🛑 Erro: Nenhum dado coletado.")