import streamlit as st
import pandas as pd
import plotly.express as px
import re
import numpy as np
import google.generativeai as genai
import os
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"


st.set_page_config(page_title="App Bagre do Mês", layout="wide", page_icon="🐟")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 App Bagre do Mês - Paraguaio")
st.markdown("Analise de performance entre GC e MM com pesos científicos de bagre.")

URL_GC = "ranking_bagre_do_mes.csv"
URL_MM = "ranking_mm_bagre.csv"

# Configure sua chave (o ideal é usar st.secrets para segurança)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 API Key não encontrada nos Secrets do Streamlit!")

def gerar_analise_ia(player_nome, stats):
    try:
        # Usando a versão estável com cota garantida no plano gratuito
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        
        prompt = f"""
        Você é um Coach profissional de CS2, conhecido por ser técnico mas muito zoeiro. Você pode pesquisar bastante sobre CS2 e 
        explicar direitinho o que é preciso fazer para melhorar o desempenho desse jogador! Você faz críticas e elogios também!
        Analise os seguintes dados do jogador {player_nome} deste mês:
        - ADR: {stats['adr']:.1f}
        - KDR: {stats['kdr']:.2f}
        - WinRate: {stats['winrate']:.1f}%
        - HS%: {stats['hs']:.1f}%
        - Score de Bagre: {stats['score']:.1f}

        Escreva um parágrafo curto com elogio, puxão de orelha e dicas de treino. Não misture as falas, zoe ele primeiro e depois dê dicas
        com uma pitada de zoeira junto.
        Use gírias de CS (ex: "pinador", "carregador", "baixa o braço", "rusha B", "bagre", "baixa a bola") e seja engraçado.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(prompt)
            return response.text
        except:
            return f"⚠️ O Coach teve um piripaque técnico: {str(e)}"

def clean_val(val):
    # Retorna NaN para valores vazios ou N/D para não estragar a média
    if pd.isna(val) or val == 'N/D' or val == '':
        return np.nan
    if isinstance(val, str):
        # Captura números em formatos como 1.20, 1,20 ou 01.05
        match = re.search(r"(\d+[.,]\d+|\d+)", val.split('\n')[0])
        if match:
            return float(match.group(1).replace(',', '.'))
    return float(val) if isinstance(val, (int, float)) else np.nan

def get_stats_mm(text, pattern):
    # Procura o número após KILLS ou DEATHS no bloco de texto
    m = re.search(pattern, str(text))
    return int(m.group(1)) if m else np.nan

def process_df(df, source_type):
    df.columns = [c.lower().strip() for c in df.columns]
    res = pd.DataFrame()
    res['player'] = df['player']

    # Captura métricas básicas usando NaN como padrão para campos ausentes
    res['adr'] = df.get('adr', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['hs'] = df.get('hs_pct', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['rating'] = df.get('rating', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['winrate'] = df.get('winrate', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['fk'] = df.get('first_kills', pd.Series([np.nan]*len(df))).apply(clean_val)

    if source_type == "MM":
        # No MM, o KD costuma vir dentro do bloco de texto da coluna hs_pct
        if 'hs_pct' in df.columns:
            k = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"KILLS\s*[\n\s]*(\d+)"))
            d = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"DEATHS\s*[\n\s]*(\d+)"))
            # Cálculo de KD seguro (evita divisão por zero e mantém NaN se não houver dados)
            res['kdr'] = (k / d.replace(0, 1)).round(2)
        else:
            res['kdr'] = np.nan
            
        # Tenta usar a coluna 'kdr' como fallback se o cálculo falhar
        if 'kdr' in df.columns:
            fallback = df['kdr'].apply(clean_val)
            res['kdr'] = res['kdr'].fillna(fallback)
    else:
        # Na GC, o KD já vem em coluna própria
        res['kdr'] = df.get('kdr', pd.Series([np.nan]*len(df))).apply(clean_val)

    return res

@st.cache_data(show_spinner=False)
def load_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url)

st.sidebar.header("📂 Fonte de Dados (GitHub)")
use_mm = st.sidebar.checkbox("Usar MM (ranking_mm_bagre.csv)", value=True)
use_gc = st.sidebar.checkbox("Usar GC (ranking_bagre_do_mes.csv)", value=True)

st.sidebar.markdown("**Links carregados:**")
st.sidebar.write("MM:", URL_MM)
st.sidebar.write("GC:", URL_GC)

if st.sidebar.button("🔄 Recarregar dados"):
    st.cache_data.clear()

data_list = []
errors = []

if use_mm:
    try:
        df_mm_raw = load_csv(URL_MM)
        data_list.append(process_df(df_mm_raw, "MM"))
    except Exception as e:
        errors.append(f"MM: {e}")

if use_gc:
    try:
        df_gc_raw = load_csv(URL_GC)
        data_list.append(process_df(df_gc_raw, "GC"))
    except Exception as e:
        errors.append(f"GC: {e}")

if errors:
    for err in errors:
        st.sidebar.error(err)

if len(data_list) > 0:
    # Agrupa e tira a média (O Pandas ignora os NaNs, mantendo o valor real de quem tem dado)
    df = pd.concat(data_list).groupby('player').mean(numeric_only=True).reset_index()
    
    # Após a média correta, preenchemos o que restou de vazio com 0 para o Score Final
    df_calc = df.fillna(0)

    def norm(s):
        return (s - s.min()) / (s.max() - s.min()) if (s.max() - s.min()) != 0 else 0

    pesos = {'kdr': 0.30, 'adr': 0.25, 'rating': 0.20, 'hs': 0.10, 'fk': 0.10, 'winrate': 0.05}

    score_final = pd.Series([0.0] * len(df_calc))
    peso_total_efetivo = 0

    for metric, weight in pesos.items():
        if metric in df_calc.columns and df_calc[metric].sum() > 0:
            score_final += norm(df_calc[metric]) * weight
            peso_total_efetivo += weight

    df['score'] = (score_final / peso_total_efetivo) * 100 if peso_total_efetivo > 0 else 0
    df = df.sort_values('score', ascending=True).reset_index(drop=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard de Performance", "🔍 Estatísticas por Player", "📝 Relatório de Zoeira", "🧠 AI Scouting"])

    with tab1:
        col_bagre, col_mvp = st.columns(2)

        with col_bagre:
            st.error(f"🐟 **BAGRE DO MÊS:** {df.iloc[0]['player'].upper()}")
            st.metric("Pontuação de Bagre", f"{df.iloc[0]['score']:.1f}")

        with col_mvp:
            st.success(f"⭐ **MVP DA GALERA:** {df.iloc[-1]['player'].upper()}")
            st.metric("Pontuação de MVP", f"{df.iloc[-1]['score']:.1f}")

        st.markdown("### Ranking Geral")
        # Formatação para mostrar N/D visualmente se o dado for 0 ou NaN
        display_df = df[['player', 'score', 'rating', 'kdr', 'adr', 'hs']].copy()
        try:
            st.dataframe(display_df.style.background_gradient(cmap='RdYlGn', subset=['score', 'rating', 'kdr', 'adr', 'hs']), use_container_width=True)
        except Exception:
            st.dataframe(display_df, use_container_width=True)

        st.markdown("### Gráficos Comparativos")
        m_escolhida = st.selectbox("Selecione a Métrica:", ["score", "rating", "kdr", "adr", "hs", "winrate"])
        fig = px.bar(df, x='player', y=m_escolhida, color=m_escolhida, color_continuous_scale='RdYlGn', text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Ficha Técnica Individual")
        p_select = st.selectbox("Selecione um player:", df['player'].unique())
        p_data = df[df['player'] == p_select].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rating", f"{p_data['rating']:.2f}" if p_data['rating'] > 0 else "N/D")
        c2.metric("KDR", f"{p_data['kdr']:.2f}" if p_data['kdr'] > 0 else "N/D")
        c3.metric("ADR", f"{p_data['adr']:.1f}" if p_data['adr'] > 0 else "N/D")
        c4.metric("HS%", f"{p_data['hs']:.1f}%" if p_data['hs'] > 0 else "N/D")

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
        ranking_texto = df.sort_values('score', ascending=False).reset_index(drop=True)
        for i, row in ranking_texto.iterrows():
            relatorio += f"{i+1}. {row['player']} - {row['score']:.1f} pts\n"

        relatorio += "\n_Gerado pelo App Bagre do Mês v2.0_"

        st.text_area("Copie o texto abaixo:", relatorio, height=350)
        st.button("Relatório Gerado com Sucesso! ✅")

    with tab4:
        st.subheader("🧠 Scouting de Bagres By Gugu (Powered by Gemini)")
        p_select_ia = st.selectbox("Escolha o player para análise do Coach:", df['player'].unique())
        p_data_ia = df[df['player'] == p_select_ia].iloc[0]

        if st.button(f"Gerar Análise para {p_select_ia}"):
             with st.spinner('O Coach está analisando os replays...'):
                 analise = gerar_analise_ia(p_select_ia, p_data_ia)
                 st.write(analise)

else:
    st.warning("⚠️ Nenhuma fonte selecionada ou não foi possível carregar os CSVs do GitHub.")