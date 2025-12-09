# fito_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import streamlit.components.v1 as components

# --- IMPORTAÇÃO DOS MÓDULOS INTERNOS ---
try:
    from fito_config import LISTA_IMASUL_COMPENSACAO
    from fito_utils import padronizar_colunas, auditoria_dados
    from fito_core import CalculadoraInventario, CalculadoraFitosso
except ImportError as e:
    st.error(f"Erro ao importar módulos internos: {e}")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="M.U.T.U.M. - Fitossociologia & Inventário", page_icon="🐦", layout="wide")

st.markdown("""
<style>
    .stAlert { padding: 0.5rem; border-radius: 5px; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
    @media print {
        [data-testid="stSidebar"], .stButton, .stFileUploader { display: none !important; }
        .block-container { padding-top: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🐦 M.U.T.U.M. - Validação Florestal")
st.markdown("#### Sistema de Auditoria de Inventário e Caracterização de Vegetação")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Projeto")
    tipologia = st.selectbox("Tipologia Vegetal Declarada:", ["Savana Arbórea Aberta (Cerradão)", "Savana Arbórea Densa", "Floresta Estacional", "Chaco", "Outro"])
    st.divider()
    st.header("2. Arquivo")
    uploaded_file = st.file_uploader("Upload Planilha (.xlsx, .csv)", type=["xlsx", "csv"])

# --- FUNÇÃO AUXILIAR: GERAR MODELO (RESGATADA) ---
def gerar_modelo_xlsx():
    colunas_modelo = ["Parcela", "Área da Parcela", "Núm. Árvore", "Nome Científico", "Nome Comum", "Família", "CAP", "DAP", "Alt. Total", "Alt. Comercial"]
    df_modelo = pd.DataFrame(columns=colunas_modelo)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_modelo.to_excel(writer, index=False, sheet_name='Campo')
    return buffer.getvalue()

if 'df_raw' not in st.session_state: st.session_state.df_raw = None
if 'resultados' not in st.session_state: st.session_state.resultados = None

# --- PROCESSAMENTO DO UPLOAD ---
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                if len(df.columns) < 2: uploaded_file.seek(0); df = pd.read_csv(uploaded_file, sep=',')
            except: df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
        
        st.session_state.df_raw = padronizar_colunas(df)
        st.sidebar.success(f"✅ Arquivo processado: {len(df)} linhas.")
    except Exception as e:
        st.error(f"Erro crítico ao ler arquivo: {e}")

# --- CORPO PRINCIPAL ---
if st.session_state.df_raw is None:
    st.info("👋 Bem-vindo! Faça o upload da sua planilha de campo ou baixe o modelo abaixo.")
    st.download_button("📥 Baixar Modelo Excel (.xlsx)", data=gerar_modelo_xlsx(), file_name="Modelo_Mutum.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    df = st.session_state.df_raw
    required = ['PARCELA', 'DAP']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas obrigatórias faltando: {', '.join(missing)}")
    else:
        tab_audit, tab_inv, tab_fito = st.tabs(["🕵️ 1. Auditoria & Biometria", "📊 2. Inventário (Volume)", "🌿 3. Fitossociologia"])

        # =====================================================================
        # ABA 1: AUDITORIA (AS NOVIDADES)
        # =====================================================================
        with tab_audit:
            st.markdown("### 🔍 Diagnóstico de Integridade e Fraude")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### 🚨 Alertas e Espécies Ameaçadas")
                with st.spinner("Verificando Lista Vermelha MMA..."):
                    df_log = auditoria_dados(df)
                if not df_log.empty:
                    criticos = df_log[df_log['Tipo'].str.contains("CRÍTICO")]
                    if not criticos.empty: st.error(f"⛔ **BLOQUEANTE:** {len(criticos)} Espécies Ameaçadas detectadas.")
                    st.dataframe(df_log.style.map(lambda x: 'color: red' if "CRÍTICO" in str(x) else 'color: orange', subset=['Tipo']), height=300)
                else:
                    st.success("✅ Nenhum problema grave detectado.")

            with c2:
                st.markdown("##### 📉 Teste da Lei de Benford")
                try:
                    daps = df['DAP'].dropna()[df['DAP'] > 0]
                    first_digits = daps.astype(str).str.lstrip('0.').str[0].astype(int)
                    counts = first_digits.value_counts(normalize=True).sort_index()
                    digits = np.arange(1, 10)
                    benford = np.log10(1 + 1/digits)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=digits, y=counts.get(digits, 0), name='Seus Dados'))
                    fig.add_trace(go.Scatter(x=digits, y=benford, name='Padrão Natural', line=dict(color='red', dash='dash')))
                    st.plotly_chart(fig, use_container_width=True)
                except: st.warning("Dados insuficientes para Benford.")
            
            st.divider()
            cb1, cb2 = st.columns(2)
            with cb1: st.plotly_chart(px.box(df, y="DAP", title="Boxplot DAP (cm)"), use_container_width=True)
            with cb2: 
                col_h = 'ALTURA_COMERCIAL' if 'ALTURA_COMERCIAL' in df.columns else 'ALTURA'
                st.plotly_chart(px.box(df, y=col_h, title="Boxplot Altura (m)"), use_container_width=True)

        # =====================================================================
        # ABA 2: INVENTÁRIO (O CLÁSSICO RESTAURADO)
        # =====================================================================
        with tab_inv:
            st.markdown("### 🧮 Cálculo e Relatório Técnico")
            with st.form("calc_form"):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                area_tot = col_f1.number_input("Área Total (ha)", value=10.0)
                area_parc = col_f2.number_input("Área Parcela (m²)", value=1000.0)
                metodo = col_f3.selectbox("Método", ["Fator de Forma", "Equação"])
                ff = col_f4.number_input("Fator (f)", value=0.33) if metodo == "Fator de Forma" else 0.33
                eq_user = st.text_input("Equação", "np.exp(-9.7 + 0.9*np.log(DAP**2 * ALTURA))") if metodo != "Fator de Forma" else ""
                
                if st.form_submit_button("🚀 Calcular Tudo"):
                    df_vol = CalculadoraInventario.calcular_volume(df, metodo, area_parc, ff, eq_user)
                    stats, err = CalculadoraInventario.estatistica_acs(df_vol, area_tot, area_parc)
                    if err: st.error(err)
                    else:
                        # Calcula Compensação
                        df_comp = CalculadoraInventario.calcular_compensacao(df_vol, area_tot, stats['area_amostrada'])
                        st.session_state.resultados = {"stats": stats, "compensacao": df_comp}
                        st.toast("Cálculo realizado!", icon="✅")
                        # Auto-scroll para relatório
                        st.divider()

            # --- RELATÓRIO FINAL (LAYOUT RESTAURADO) ---
            if st.session_state.resultados:
                res = st.session_state.resultados["stats"]
                df_comp = st.session_state.resultados["compensacao"]
                
                st.markdown("---")
                st.markdown("## 📋 Resultados do Inventário")

                # Cards Resumo
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Volume Médio", f"{res['media']:.2f} m³/ha")
                k2.metric("Erro Amostragem", f"{res['er']:.2f} %", delta_color="normal" if res['er'] <= 20 else "inverse")
                k3.metric("IC [95%]", f"[{res['ic_min']:.1f}; {res['ic_max']:.1f}]")
                k4.metric("Vol Total", f"{res['total_vol']:.0f} m³")

                # Seção Compensação Obrigatória (Restaurada)
                st.markdown("### 🌳 Compensação Obrigatória (Res. Semade n.9/2015)")
                if not df_comp.empty:
                    total_mudas = int(df_comp['Mudas_Compensacao'].sum())
                    st.warning(f"⚠️ **ATENÇÃO: ESPÉCIES PROTEGIDAS DETECTADAS!**")
                    st.success(f"O total de mudas exigido é de **{total_mudas:,} mudas**.")
                    st.dataframe(df_comp, hide_index=True)
                else:
                    st.info("✅ Nenhuma espécie de compensação obrigatória (Art. 52) detectada.")

                # Tabela Detalhada (Restaurada)
                st.markdown("### 📊 Tabela de Análise Estatística")
                dados_tabela = [
                    ["Média Aritmética", f"{res['media']:.4f} m³/ha", f"{res['total_vol']:.4f} m³"],
                    ["Variância", f"{res['var']:.4f}", "-"],
                    ["Desvio Padrão", f"{res['dp']:.4f} m³/ha", "-"],
                    ["Coeficiente de Variação", f"{res['cv']:.2f} %", "-"],
                    ["Variância da Média", f"{res['var_media']:.4f}", "-"],
                    ["Erro Padrão da Média", f"{res['ep']:.4f} m³/ha", "-"],
                    ["Valor de t (Student)", f"{res['t']:.4f}", "-"],
                    ["Erro de Amostragem (Absoluto)", f"± {res['ea']:.4f} m³/ha", f"± {res['total_ea']:.4f} m³"],
                    ["Erro de Amostragem (Relativo)", f"{res['er']:.2f} %", f"{res['er']:.2f} %"],
                    ["Intervalo de Confiança (Mínimo)", f"{res['ic_min']:.4f} m³/ha", f"{res['total_ic_min']:.4f} m³"],
                    ["Intervalo de Confiança (Máximo)", f"{res['ic_max']:.4f} m³/ha", f"{res['total_ic_max']:.4f} m³"]
                ]
                df_relatorio = pd.DataFrame(dados_tabela, columns=["Parâmetro", "Estimativa/ha", "Estimativa Total"])
                st.table(df_relatorio)
                
                # Botão CSV Tabela
                csv = df_relatorio.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Tabela Estatística (CSV)", csv, "Relatorio_Estatistico.csv", "text/csv")

        # =====================================================================
        # ABA 3: FITOSSOCIOLOGIA (NOVIDADE MANTIDA)
        # =====================================================================
        with tab_fito:
            st.markdown(f"### 🌿 Caracterização da Vegetação")
            tabela_ivi, indices = CalculadoraFitosso.processar(df, 1000) # Assumindo 1000m² para fito visual
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Shannon (H')", f"{indices['H\' (Shannon)']:.2f}")
            c2.metric("Pielou (J')", f"{indices['J\' (Pielou)']:.2f}")
            c3.metric("Riqueza (S)", f"{indices['Riqueza (S)']}")
            c4.metric("Área Basal", f"{indices['Area Basal Total (G)']:.2f} m²/ha")
            
            st.dataframe(tabela_ivi.style.background_gradient(subset=['IVI'], cmap='Greens'), use_container_width=True)
            
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(tabela_ivi.head(15).sort_values('IVI'), x='IVI', y='NOME_CIENTIFICO', orientation='h', title="Top 15 IVI"), use_container_width=True)
            with g2: 
                try:
                    bins = np.arange(0, df['DAP'].max() + 5, 5)
                    labels = [f"{int(b)}-{int(b+5)}" for b in bins[:-1]]
                    df['Classe_DAP'] = pd.cut(df['DAP'], bins=bins, labels=labels, right=False)
                    contagem = df['Classe_DAP'].value_counts().sort_index()
                    st.plotly_chart(px.bar(x=contagem.index.astype(str), y=contagem.values, title="Distribuição Diamétrica"), use_container_width=True)
                except: st.warning("Erro no gráfico diamétrico.")
