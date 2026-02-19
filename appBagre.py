import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuração da Página
st.set_page_config(page_title="App Bagre do Mês", layout="wide", page_icon="🐟")

# --- ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 App Bagre do Mês - Paraguaio")
st.markdown("Analise de performance entre GC e MM com pesos científicos de bagre.")

# --- FUNÇÕES DE LIMPEZA E PROTEÇÃO ---
def clean_val(val):
    if pd.isna(val) or val == 'N/D' or val == '': return 0.0
    if isinstance(val, str):
        # Pega o primeiro número antes de quebras de linha ou textos
        match = re.search(r"(\d+[.,]\d+|\d+)", val.split('\n')[0])
        if match:
            return float(match.group(1).replace(',', '.'))
    return float(val) if isinstance(val, (int, float)) else 0.0

def get_stats_mm(text, pattern):
    m = re.search(pattern, str(text))
    return int(m.group(1)) if m else 0

def process_file(file, source_type):
    df = pd.read_csv(file)
    df.columns = [c.lower().strip() for c in df.columns]
    
    res = pd.DataFrame()
    res['player'] = df['player']
    
    # Mapeamento Seguro (Usa 0 se a coluna não existir)
    res['adr'] = df.get('adr', pd.Series([0]*len(df))).apply(clean_val)
    res['hs'] = df.get('hs_pct', pd.Series([0]*len(df))).apply(clean_val)
    res['rating'] = df.get('rating', pd.Series([0]*len(df))).apply(clean_val)
    res['winrate'] = df.get('winrate', pd.Series([0]*len(df))).apply(clean_val)
    res['fk'] = df.get('first_kills', pd.Series([0]*len(df))).apply(clean_val)
    
    if source_type == "MM":
        # No MM extraímos K/D do bloco de texto do HS%
        df['k'] = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"KILLS\n(\d+)"))
        df['d'] = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"DEATHS\n(\d+)"))
        res['kdr'] = (df['k'] / df['d']).fillna(0).round(2)
    else:
        # Na GC o KDR já vem pronto
        res['kdr'] = df.get('kdr', pd.Series([0]*len(df))).apply(clean_val)
    
    return res

# --- SIDEBAR ---
st.sidebar.header("📂 Importar Dados")
file_mm = st.sidebar.file_uploader("Upload ranking_mm_bagre.csv", type="csv")
file_gc = st.sidebar.file_uploader("Upload ranking_bagre_do_mes.csv", type="csv")

if file_mm or file_gc:
    data_list = []
    if file_mm: data_list.append(process_file(file_mm, "MM"))
    if file_gc: data_list.append(process_file(file_gc, "GC"))

    # Unifica MM e GC (tira a média se o player estiver nos dois)
    df = pd.concat(data_list).groupby('player').mean().reset_index()

    # --- CÁLCULO DO SCORE COM OS SEUS PESOS ---
    def norm(s): return (s - s.min()) / (s.max() - s.min()) if (s.max() - s.min()) != 0 else 0

    pesos = {'kdr': 0.30, 'adr': 0.25, 'rating': 0.20, 'hs': 0.10, 'fk': 0.10, 'winrate': 0.05}
    
    score_final = pd.Series([0.0] * len(df))
    peso_total_efetivo = 0
    
    for metric, weight in pesos.items():
        if df[metric].sum() > 0: # Só aplica o peso se houver dados na coluna
            score_final += norm(df[metric]) * weight
            peso_total_efetivo += weight
    
    # Ajusta o score final (0 a 100) baseado nos pesos que conseguimos usar
    df['score'] = (score_final / peso_total_efetivo) * 100 if peso_total_efetivo > 0 else 0
    df = df.sort_values('score', ascending=True).reset_index(drop=True)

    # --- LAYOUT PRINCIPAL EM ABAS ---
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard de Performance", "🔍 Estatísticas por Player", "📝 Relatório de Zoeira"])

    with tab1:
        col_bagre, col_mvp = st.columns(2)
        with col_bagre:
            st.error(f"🐟 **BAGRE DO MÊS:** {df.iloc[0]['player'].upper()}")
            st.metric("Pontuação de Bagre", f"{df.iloc[0]['score']:.1f}")
        
        with col_mvp:
            st.success(f"⭐ **MVP DA GALERA:** {df.iloc[-1]['player'].upper()}")
            st.metric("Pontuação de MVP", f"{df.iloc[-1]['score']:.1f}")

        st.markdown("### Ranking Geral")
        # Mostra a tabela com gradiente (Lembre-se de rodar pip install matplotlib)
        try:
            st.dataframe(df[['player', 'score', 'rating', 'kdr', 'adr', 'hs']].style.background_gradient(cmap='RdYlGn'), use_container_width=True)
        except:
            st.dataframe(df[['player', 'score', 'rating', 'kdr', 'adr', 'hs']], use_container_width=True)

        st.markdown("### Gráficos Comparativos")
        m_escolhida = st.selectbox("Selecione a Métrica:", ["score", "rating", "kdr", "adr", "hs", "winrate"])
        fig = px.bar(df, x='player', y=m_escolhida, color=m_escolhida, color_continuous_scale='RdYlGn', text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Ficha Técnica Individual")
        p_select = st.selectbox("Selecione um player:", df['player'].unique())
        p_data = df[df['player'] == p_select].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rating (MM)", f"{p_data['rating']:.2f}" if p_data['rating'] > 0 else "N/A")
        c2.metric("KDR", f"{p_data['kdr']:.2f}")
        c3.metric("ADR", f"{p_data['adr']:.1f}")
        c4.metric("HS%", f"{p_data['hs']:.1f}%")
        
        st.info(f"O player {p_select} está com score de **{p_data['score']:.1f}** no ranking geral.")

    with tab3:
        st.subheader("📢 Gerador de Relatório para WhatsApp")
        
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
• 📉 *K/D de Centavos:* {df.iloc[0]['player']} ({df.iloc[0]['kdr']:.2f})

*Resumo do Ranking (Melhor -> Pior):*
"""
        # Inverte a ordem para mostrar do MVP para o Bagre no texto
        ranking_texto = df.sort_values('score', ascending=False).reset_index(drop=True)
        for i, row in ranking_texto.iterrows():
            relatorio += f"{i+1}. {row['player']} - {row['score']:.1f} pts\n"

        relatorio += "\n_Gerado pelo App Bagre do Mês v2.0_"

        st.text_area("Copie o texto abaixo:", relatorio, height=350)
        st.button("Relatório Gerado com Sucesso! ✅")

else:
    st.warning("⚠️ Aguardando upload dos arquivos (MM ou GC) na barra lateral para começar.")