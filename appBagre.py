import streamlit as st
import pandas as pd
import plotly.express as px
import re
import numpy as np
import google.generativeai as genai
import os

# Configuração de estabilidade para a API
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

st.set_page_config(page_title="App Bagre do Mês", layout="wide", page_icon="🐟")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 App Bagre do Mês - Bagres FC")
st.markdown("Analise de performance entre GC e MM com pesos científicos de los bagre.")

# Arquivos Atuais
URL_GC = "ranking_bagre_do_mes.csv"
URL_MM = "ranking_mm_bagre.csv"

# Arquivos Históricos (Novos)
HIST_GC = "historico_gc_geral.csv"
HIST_MM = "historico_mm_geral.csv"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 API Key não encontrada nos Secrets do Streamlit!")

def gerar_analise_ia(player_nome, stats, contexto="mensal"):
    try:
        # Tenta usar o modelo que você definiu
        model = genai.GenerativeModel('gemini-2.5-pro') 
        
        if contexto == "mensal":
            prompt = f"""
            Você é um Coach profissional de CS2, conhecido por ser técnico mas muito zoeiro.
            Analise os seguintes dados do jogador {player_nome} deste mês:
            - ADR: {stats['adr']:.1f}, KDR: {stats['kdr']:.2f}, WinRate: {stats['winrate']:.1f}%, HS%: {stats['hs']:.1f}%, Score: {stats['score']:.1f}
            Escreva um parágrafo curto com elogio, puxão de orelha e dicas de treino. Zoe ele primeiro e depois dê dicas.
            Use gírias de CS (pinador, carregador, baixa o braço, rusha B, bagre) e seja engraçado.
            """
        else:
            # Prompt específico para a Tab 6 (Evolução)
            prompt = f"""
            Você é um Coach de CS2 de Caçapava. Analise a evolução de {player_nome}:
            Dados Atuais: ADR {stats['atual_adr']:.1f}, KDR {stats['atual_kdr']:.2f}
            Dados Anteriores: ADR {stats['passado_adr']:.1f}, KDR {stats['passado_kdr']:.2f}
            Diga se ele está melhorando ou virando um bagre de águas profundas. Seja curto, grosso e use gírias.
            """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            return response.text
        except:
            return f"⚠️ O Coach teve um piripaque técnico: {str(e)}"

def clean_val(val):
    if pd.isna(val) or val == 'N/D' or val == '':
        return np.nan
    if isinstance(val, str):
        match = re.search(r"(\d+[.,]\d+|\d+)", val.split('\n')[0])
        if match:
            return float(match.group(1).replace(',', '.'))
    return float(val) if isinstance(val, (int, float)) else np.nan

def get_stats_mm(text, pattern):
    m = re.search(pattern, str(text))
    return int(m.group(1)) if m else np.nan

def process_df(df, source_type):
    df.columns = [c.lower().strip() for c in df.columns]
    res = pd.DataFrame()
    res['player'] = df['player']
    # Mantém a coluna de mês se ela existir no CSV
    if 'mes' in df.columns:
        res['mes'] = df['mes']

    res['adr'] = df.get('adr', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['hs'] = df.get('hs_pct', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['rating'] = df.get('rating', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['winrate'] = df.get('winrate', pd.Series([np.nan]*len(df))).apply(clean_val)
    res['fk'] = df.get('first_kills', pd.Series([np.nan]*len(df))).apply(clean_val)

    if source_type == "MM":
        if 'hs_pct' in df.columns:
            k = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"KILLS\s*[\n\s]*(\d+)"))
            d = df['hs_pct'].apply(lambda x: get_stats_mm(x, r"DEATHS\s*[\n\s]*(\d+)"))
            res['kdr'] = (k / d.replace(0, 1)).round(2)
        else:
            res['kdr'] = np.nan
        if 'kdr' in df.columns:
            fallback = df['kdr'].apply(clean_val)
            res['kdr'] = res['kdr'].fillna(fallback)
    else:
        res['kdr'] = df.get('kdr', pd.Series([np.nan]*len(df))).apply(clean_val)
    return res

@st.cache_data(show_spinner=False)
def load_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url)

# --- SIDEBAR ---
st.sidebar.header("📂 Fonte de Dados (GitHub)")
use_mm = st.sidebar.checkbox("Usar MM", value=True)
use_gc = st.sidebar.checkbox("Usar GC", value=True)

if st.sidebar.button("🔄 Recarregar dados"):
    st.cache_data.clear()

data_list = []
if use_mm:
    try: data_list.append(process_df(load_csv(URL_MM), "MM"))
    except: st.sidebar.warning("Arquivo MM não encontrado.")
if use_gc:
    try: data_list.append(process_df(load_csv(URL_GC), "GC"))
    except: st.sidebar.warning("Arquivo GC não encontrado.")

if len(data_list) > 0:
    df = pd.concat(data_list).groupby('player').mean(numeric_only=True).reset_index()
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

    # --- TABS ---
    tabs = st.tabs(["📊 Dashboard", "🔍 Player Stats", "📝 WhatsApp", "🧠 AI Scouting", "🆚 Comparativo 1x1", "📈 Estou + ou - Bagre?"])

    with tabs[0]: # Dashboard
        col_bagre, col_mvp = st.columns(2)
        with col_bagre:
            st.error(f"🐟 **BAGRE DO MÊS:** {df.iloc[0]['player'].upper()}")
            st.metric("Pontuação de Bagre", f"{df.iloc[0]['score']:.1f}")
        with col_mvp:
            st.success(f"⭐ **MVP DA GALERA:** {df.iloc[-1]['player'].upper()}")
            st.metric("Pontuação de MVP", f"{df.iloc[-1]['score']:.1f}")
        
        st.dataframe(df[['player', 'score', 'rating', 'kdr', 'adr', 'hs']].style.background_gradient(cmap='RdYlGn'), use_container_width=True)
        m_escolhida = st.selectbox("Selecione a Métrica:", ["score", "rating", "kdr", "adr", "hs", "winrate"])
        st.plotly_chart(px.bar(df, x='player', y=m_escolhida, color=m_escolhida, color_continuous_scale='RdYlGn'), use_container_width=True)

    with tabs[1]: # Player Stats
        p_select = st.selectbox("Selecione um player:", df['player'].unique())
        p_data = df[df['player'] == p_select].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rating", f"{p_data['rating']:.2f}")
        c2.metric("KDR", f"{p_data['kdr']:.2f}")
        c3.metric("ADR", f"{p_data['adr']:.1f}")
        c4.metric("HS%", f"{p_data['hs']:.1f}%")

    with tabs[2]: # WhatsApp
        bagre, mvp = df.iloc[0]['player'], df.iloc[-1]['player']
        relatorio = f"*🐟 RELATÓRIO: BAGRE DO MÊS* 🐟\n\n🏆 *BAGRE:* {bagre.upper()}\n⭐ *MVP:* {mvp.upper()}\n\n*Ranking:*\n"
        for i, row in df.sort_values('score', ascending=False).reset_index().iterrows():
            relatorio += f"{i+1}. {row['player']} - {row['score']:.1f} pts\n"
        st.text_area("Copie para o Zap:", relatorio, height=250)

    with tabs[3]: # AI Scouting
        p_select_ia = st.selectbox("Análise do Coach:", df['player'].unique(), key="ia_mensal")
        if st.button(f"Gerar Análise para {p_select_ia}"):
            with st.spinner('O Coach está analisando...'):
                st.write(gerar_analise_ia(p_select_ia, df[df['player'] == p_select_ia].iloc[0]))

    with tabs[5]:

        st.subheader("🆚 Duelo de Bagres: Comparativo Lado a Lado")

        st.markdown("Selecione dois jogadores para ver quem está carregando e quem está pinando.")



        # Seleção dos jogadores

        col_sel1, col_sel2 = st.columns(2)

        with col_sel1:

            p1 = st.selectbox("Primeiro Player:", df['player'].unique(), index=0, key="comp_p1")

        with col_sel2:

            p2 = st.selectbox("Segundo Player:", df['player'].unique(), index=1, key="comp_p2")



        if p1 == p2:

            st.warning("⚠️ Selecione jogadores diferentes para uma comparação justa!")

        else:

            # Filtra os dados dos dois selecionados

            d1 = df[df['player'] == p1].iloc[0]

            d2 = df[df['player'] == p2].iloc[0]



            # --- PARTE 1: MÉTRICAS EM DESTAQUE ---

            st.markdown(f"### {p1} vs {p2}")

            m1, m2, m3, m4 = st.columns(4)

           

            # Função auxiliar para mostrar quem vence na métrica

            def delta_label(v1, v2, invert=False):

                diff = v1 - v2

                # Se invert for True (tipo Score de Bagre), menor valor é melhor

                is_p1_better = (diff < 0) if invert else (diff > 0)

                return f"{v1:.2f} vs {v2:.2f}", "normal" if diff == 0 else ("inverse" if is_p1_better else "normal")



            m1.metric("Rating", f"{d1['rating']:.2f}", f"vs {d2['rating']:.2f}", delta_color="normal" if d1['rating'] >= d2['rating'] else "inverse")

            m2.metric("KDR", f"{d1['kdr']:.2f}", f"vs {d2['kdr']:.2f}", delta_color="normal" if d1['kdr'] >= d2['kdr'] else "inverse")

            m3.metric("ADR", f"{d1['adr']:.1f}", f"vs {d2['adr']:.1f}", delta_color="normal" if d1['adr'] >= d2['adr'] else "inverse")

            m4.metric("Score de Bagre", f"{d1['score']:.1f}", f"vs {d2['score']:.1f} (Menor é melhor)", delta_color="inverse" if d1['score'] <= d2['score'] else "normal")



            # --- PARTE 2: GRÁFICO DE BARRAS AGRUPADAS ---

            metrics_list = ['rating', 'kdr', 'adr', 'hs', 'winrate']

           

            # Prepara os dados para o Plotly (formato longo)

            comp_data = []

            for m in metrics_list:

                comp_data.append({"Métrica": m.upper(), "Valor": d1[m], "Player": p1})

                comp_data.append({"Métrica": m.upper(), "Valor": d2[m], "Player": p2})

           

            df_comp_chart = pd.DataFrame(comp_data)



            fig_duel = px.bar(

                df_comp_chart,

                x="Métrica",

                y="Valor",

                color="Player",

                barmode="group",

                text_auto='.2f',

                title=f"Análise Técnica: {p1} vs {p2}",

                color_discrete_sequence=['#00CC96', '#EF553B'] # Verde para Player 1, Vermelho para Player 2 (ou vice-versa)

            )

           

            fig_duel.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="white")

            st.plotly_chart(fig_duel, use_container_width=True)



            # --- PARTE 3: VEREDITO DA IA ---

            if st.button(f"Pedir veredito do Coach sobre este duelo"):

                with st.spinner('O Coach está analisando a treta...'):

                    prompt_duelo = f"""

                    Você é um Coach de CS2 zoeiro. Compare esses dois jogadores:

                    Jogador 1 ({p1}): ADR {d1['adr']:.1f}, KDR {d1['kdr']:.2f}, Score {d1['score']:.1f}

                    Jogador 2 ({p2}): ADR {d2['adr']:.1f}, KDR {d2['kdr']:.2f}, Score {d2['score']:.1f}

                   

                    Diga quem está carregando quem e faça uma piada com o perdedor do duelo.

                    Use gírias de CS e seja curto e grosso.

                    """

                    try:

                        model = genai.GenerativeModel('gemini-1.5-flash-latest')

                        response = model.generate_content(prompt_duelo)

                        st.info(response.text)

                    except Exception as e:

                        st.error(f"O Coach se recusou a opinar: {e}")

    with tabs[5]: # TAB 6: Estou + ou - Bagre?
        st.subheader("📈 Análise de Evolução Temporal")
        try:
            # Carrega e processa o histórico
            h_gc = process_df(load_csv(HIST_GC), "GC")
            h_mm = process_df(load_csv(HIST_MM), "MM")
            df_h = pd.concat([h_gc, h_mm]).groupby(['player', 'mes']).mean(numeric_only=True).reset_index()
            
            p_evol = st.selectbox("Selecione seu nick:", df_h['player'].unique())
            df_p_h = df_h[df_h['player'] == p_evol].sort_values('mes')
            
            if len(df_p_h) < 2:
                st.info("💡 Você precisa de dados de pelo menos 2 meses no histórico para ver a evolução.")
            else:
                st.plotly_chart(px.line(df_p_h, x='mes', y='kdr', title=f"Evolução de KDR - {p_evol}", markers=True), use_container_width=True)
                
                atual, passado = df_p_h.iloc[-1], df_p_h.iloc[-2]
                c1, c2, c3 = st.columns(3)
                c1.metric("KDR Atual", f"{atual['kdr']:.2f}", f"{atual['kdr'] - passado['kdr']:.2f}")
                c2.metric("ADR Atual", f"{atual['adr']:.1f}", f"{atual['adr'] - passado['adr']:.1f}")
                c3.metric("HS% Atual", f"{atual['hs']:.1f}%", f"{atual['hs'] - passado['hs']:.1f}%")
                
                if st.button("Coach, estou melhorando?"):
                    stats_ia = {
                        "atual_adr": atual['adr'], "atual_kdr": atual['kdr'],
                        "passado_adr": passado['adr'], "passado_kdr": passado['kdr']
                    }
                    st.success(gerar_analise_ia(p_evol, stats_ia, contexto="evolucao"))
        except:
            st.warning("⚠️ Arquivos de histórico não encontrados. Rode os scrapers novos para gerá-los!")

    with tabs[5]: 
        st.subheader("📈 + ou - Bagre?")
        try:
            # Carrega e processa o histórico
            h_gc = process_df(load_csv(HIST_GC), "GC")
            h_mm = process_df(load_csv(HIST_MM), "MM")
            df_h = pd.concat([h_gc, h_mm]).groupby(['player', 'mes']).mean(numeric_only=True).reset_index()
            
            p_evol = st.selectbox("Selecione seu nick:", df_h['player'].unique())
            df_p_h = df_h[df_h['player'] == p_evol].sort_values('mes')
            
            if len(df_p_h) < 2:
                st.info("💡 Você precisa de dados de pelo menos 2 meses no histórico para ver a evolução.")
            else:
                st.plotly_chart(px.line(df_p_h, x='mes', y='kdr', title=f"Evolução de KDR - {p_evol}", markers=True), use_container_width=True)
                
                atual, passado = df_p_h.iloc[-1], df_p_h.iloc[-2]
                c1, c2, c3 = st.columns(3)
                c1.metric("KDR Atual", f"{atual['kdr']:.2f}", f"{atual['kdr'] - passado['kdr']:.2f}")
                c2.metric("ADR Atual", f"{atual['adr']:.1f}", f"{atual['adr'] - passado['adr']:.1f}")
                c3.metric("HS% Atual", f"{atual['hs']:.1f}%", f"{atual['hs'] - passado['hs']:.1f}%")
                
                if st.button("Coach, estou melhorando?"):
                    stats_ia = {
                        "atual_adr": atual['adr'], "atual_kdr": atual['kdr'],
                        "passado_adr": passado['adr'], "passado_kdr": passado['kdr']
                    }
                    st.success(gerar_analise_ia(p_evol, stats_ia, contexto="evolucao"))
        except:
            st.warning("⚠️ Arquivos de histórico não encontrados. Rode os scrapers novos para gerá-los!")

else:
    st.warning("⚠️ Nenhuma fonte selecionada ou arquivos não encontrados.")