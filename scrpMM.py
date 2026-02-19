import undetected_chromedriver as uc
import pandas as pd
import time
import sys
from selenium.webdriver.common.by import By

# --- CONFIGURAÇÃO DOS PARTICIPANTES (IDs de 17 dígitos ATUALIZADOS) ---
PARTICIPANTES = [
    {"nome": "gfelicio", "id": "765611980325002"},
    {"nome": "wEs", "id": "76561199581556353"},
    {"nome": "BioAlarcon", "id": "76561198195671534"},
    {"nome": "JOGod", "id": "76561198331541703"},
    {"nome": "ManoShaco", "id": "76561198383635477"},
    {"nome": "Anjoz", "id": "76561198144917009"},
    {"nome": "TioZo", "id": "76561198137236044"},
    {"nome": "MARMOT", "id": "76561198126457221"},
]

def iniciar_driver():
    print("🔄 Iniciando Google Chrome...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--start-maximized')
    
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        time.sleep(2)
        if len(driver.window_handles) > 0:
            driver.switch_to.window(driver.window_handles[0])
        return driver
    except Exception as e:
        print(f"\n❌ ERRO AO ABRIR O NAVEGADOR: {e}")
        sys.exit(1)

def extrair_dados_mm(driver, player):
    nome = player['nome']
    steam_id = player['id']
    url_stats = f"https://csgostats.gg/player/{steam_id}"
    
    print(f"\n--- 🌍 Acessando perfil de: {nome} ---")
    
    try:
        driver.get(url_stats)
        time.sleep(1)
        if "about:blank" in driver.current_url:
            driver.execute_script(f"window.location.href = '{url_stats}';")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None
    
    print(f"📍 Página carregada. Escolha os filtros no Chrome (Ex: Premier / Mês).")
    input(f"✅ Quando os dados aparecerem na tela, pressione ENTER aqui...")

    dados = {"player": nome, "steam_id": steam_id}
    
    # Lista de campos para buscar via XPATH por texto (Mais robusto)
    campos_busca = {
        "kdr": "KDR",
        "adr": "ADR",
        "hs_pct": "HS",
        "rating": "Rating",
        "winrate": "Win Rate"
    }

    for chave, texto in campos_busca.items():
        try:
            # Busca o elemento que contém o nome da estatística e pega o valor seguinte
            xpath = f"//*[contains(text(), '{texto}')]/following-sibling::*"
            valor = driver.find_element(By.XPATH, xpath).text
            dados[chave] = valor
        except:
            # Tentativa secundária caso o site use um formato diferente
            try:
                xpath_alt = f"//*[contains(text(), '{texto}')]/..//div"
                dados[chave] = driver.find_element(By.XPATH, xpath_alt).text
            except:
                dados[chave] = "N/D"

    # Captura de Kills/Deaths que já estava funcionando
    try:
        dados["kills"] = driver.find_element(By.XPATH, "//div[contains(text(), 'Kills')]/following-sibling::div").text
        dados["deaths"] = driver.find_element(By.XPATH, "//div[contains(text(), 'Deaths')]/following-sibling::div").text
    except:
        pass

    print(f"✅ Dados de {nome} coletados!")
    return dados

if __name__ == "__main__":
    driver = iniciar_driver()
    ranking_final = []

    try:
        print("\n🚀 Navegador pronto! Faça login se necessário.")
        input("✅ Após o login, pressione ENTER para iniciar o loop...")

        for p in PARTICIPANTES:
            res = extrair_dados_mm(driver, p)
            if res:
                ranking_final.append(res)
            time.sleep(1)

    finally:
        print("\n🏁 Processo concluído. Fechando navegador...")
        driver.quit()

    if ranking_final:
        df = pd.DataFrame(ranking_final)
        df.to_csv("ranking_mm_bagre.csv", index=False, encoding="utf-8-sig")
        
        print(f"\n✨ SUCESSO, GUSTAVO!")
        print("-" * 60)
        
        # Converte Rating para número para ordenar
        df['rating_num'] = pd.to_numeric(df['rating'].str.replace(',', '.'), errors='coerce')
        print("🏆 RANKING MM (Menor Rating = Mais Bagre):")
        print(df.sort_values(by='rating_num', ascending=True)[['player', 'rating', 'kdr', 'adr']].to_string(index=False))
    else:
        print("\n🛑 Nenhuma informação coletada.")