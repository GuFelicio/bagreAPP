import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuração da Página
st.set_page_config(page_title="App Bagre do Mês", layout="wide", page_icon="🐟")

# --- LINKS DO GITHUB (COLE OS SEUS LINKS "RAW" AQUI) ---
# Lembre-se: O link deve começar com https://raw.githubusercontent.com/...
URL_MM = "https://raw.githubusercontent.com/GuFelicio/bagreAPP/refs/heads/main/ranking_mm_bagre.csv"
URL_GC = "https://raw.githubusercontent.com/GuFelicio/bagreAPP/refs/heads/main/ranking_bagre_do_mes.csv"

# --- ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 App Bagre do Mês - Caçapava Edition")
st.markdown("Análise automática de performance integrada (GitHub -> Streamlit).")

# --- FUNÇÕES DE LIMPEZA E PROCESSAMENTO ---
def clean_val(val):
    if pd.isna(val) or val == 'N/D' or val == '': return 0.0
    if isinstance(val, str):
        # Pega o primeiro número antes de quebras de linha ou textos extras
        match = re.search(r"(\d+[.,]\d+|\d+)", val.split('\n')[0])
        if match:
            return float(match.group(1).replace(',', '.'))
    return float(val) if isinstance(val, (int, float)) else 0.0

def get_stats_mm(text, pattern):
    m = re.search(pattern, str(text))
    return int(m.group(1)) if m else 0

@st.cache_data
def load_and_process_data(url_mm, url_gc):
    data_list = []
    
    # Processar Matchmaking (MM)
    try:
        df_mm = pd.read_csv(url_mm)
        df_mm.columns = [c.lower().strip() for c in df_mm.columns]
        res_mm = pd.DataFrame({'player': df_mm['player']})
        res_mm['adr'] = df_mm.get('adr', 0).apply(clean_val)
        res_mm['hs'] = df_mm.get('hs_pct', 0).apply(clean_val)
        res_mm['rating'] = df_mm.get('rating', 0).apply(clean_val)
        res_mm['winrate'] = df_mm.get('winrate', 0).apply(clean_val)
        res_mm['fk'] = df_mm.get('first_kills', 0).apply(clean_val)
        
        # K/D Extraído da string complexa do MM
        df_mm['k'] = df_mm['hs_pct'].apply(lambda x: get_stats_mm(x, r"KILLS\n(\d+)"))
        df_mm['d'] = df_mm['hs_pct'].apply(lambda x: get_stats_mm(x, r"DEATHS\n(\d+)"))
        res_mm['kdr'] = (df_mm['k'] / df_mm['d'].replace(0, 1)).round(2)
        data_list.append(res_mm)
    except:
        st.sidebar.warning("Arquivo MM não encontrado no link fornecido.")

    # Processar GamersClub (GC)
    try:
        df_gc = pd.read_csv(url_gc)
        df_gc.columns = [c.lower().strip() for c in df_gc.columns]
        res_gc = pd.DataFrame({'player': df_gc['player']})
        res_gc['adr'] = df_gc.get('adr', 0).apply(clean_val)
        res_gc['hs'] = df_gc.get('hs_pct', 0).apply(clean_val)
        res_gc['rating'] = df_gc.get('rating', 0).apply(clean_val)
        res_gc['winrate'] = df_gc.get('winrate', 0).apply(clean_val)
        res_gc['fk'] = df_gc.get('first_kills', 0).apply(clean_val)
        res_gc['kdr'] = df_gc.get('kdr', 0).apply(clean_val)
        data_list.append(res_gc)
    except:
        st.sidebar.warning("Arquivo GC não encontrado no link fornecido.")

    if not data_list: return None
    
    # Unifica e tira a média dos jogadores presentes em ambas
    df_combined = pd.concat(data_list).groupby('player').mean().reset_index()
    
    # --- CÁLCULO DO SCORE FINAL ---
    def norm(s): return (s - s.min()) / (s.max() - s.min()) if (s.max() - s.min()) != 0 else 0
    
    pesos = {'kdr': 0.30, 'adr': 0.25, 'rating': 0.20, 'hs': 0.10, 'fk': 0.10, 'winrate': 0.05}
    
    score_final = pd.Series([0.0] * len(df_combined))
    peso_total_efetivo = 0
    
    for metric, weight in pesos.items():
        if df_combined[metric].sum() > 0:
            score_final += norm(df_combined[metric]) * weight
            peso_total_efetivo += weight
            
    df_combined['score'] = (score_final / peso_total_efetivo) * 100
    return df_combined.sort_values('score', ascending=True).reset_index(drop=True)

# Carregamento Automático
df = load_and_process_data(URL_MM, URL_GC)

if df is not None:
    tab1, tab2, tab3 = st.tabs(["📊 Performance Geral", "🔍 Ficha Individual", "📝 Relatório WhatsApp"])

    with tab1:
        st.subheader("O Veredito do Mês")
        try:
            st.dataframe(df[['player', 'score', 'kdr', 'adr', 'rating', 'hs']].style.background_gradient(cmap='RdYlGn'), use_container_width=True)
        except:
            st.dataframe(df[['player', 'score', 'kdr', 'adr', 'rating', 'hs']], use_container_width=True)
        
        st.plotly_chart(px.bar(df, x='player', y='score', color='score', color_continuous_scale='RdYlGn', title="Ranking de Pontuação (Menor = Bagre)"))

    with tab2:
        p_select = st.selectbox("Selecione o Player:", df['player'].unique())
        p_data = df[df['player'] == p_select].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score Total", f"{p_data['score']:.1f}")
        c2.metric("KDR", f"{p_data['kdr']:.2f}")
        c3.metric("ADR", f"{p_data['adr']:.1f}")
        c4.metric("HS%", f"{p_data['hs']:.1f}%")

    with tab3:
        bagre = df.iloc[0]['player']
        mvp = df.iloc[-1]['player']
        melhor_hs = df.loc[df['hs'].idxmax(), 'player']
        pior_adr = df.loc[df['adr'].idxmin(), 'player']
        
        relatorio = f"""*🐟 RELATÓRIO OFICIAL: BAGRE DO MÊS* 🐟

🏆 *O VEREDITO:* O grande Bagre é o *{bagre.upper()}*! (Score: {df.iloc[0]['score']:.1f})
⭐ *O CARREGADOR:* {mvp.upper()} jogou o fino! (Score: {df.iloc[-1]['score']:.1f})

---
🎯 *Destaques Técnicos:*
• 💀 *Pior ADR:* {pior_adr} (Dando menos dano que bot)
• 🎯 *Mira de Laser:* {melhor_hs} ({df['hs'].max():.1f}% HS)
• 📉 *K/D de Centavos:* {bagre} ({df.iloc[0]['kdr']:.2f})

*Resumo do Ranking (Melhor -> Pior):*
"""
        ranking_texto = df.sort_values('score', ascending=False).reset_index(drop=True)
        for i, row in ranking_texto.iterrows():
            relatorio += f"{i+1}. {row['player']} - {row['score']:.1f} pts\n"
        
        relatorio += "\n_Gerado pelo App Bagre do Mês v2.0_"
        st.text_area("Copie o texto para o grupo:", relatorio, height=350)

else:
    st.error("⚠️ Erro ao carregar dados. Verifique se os links Raw no código estão corretos.")