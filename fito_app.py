# fito_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import chisquare

# Importação dos módulos internos
from fito_config import LISTA_IMASUL_COMPENSACAO
from fito_utils import padronizar_colunas, auditoria_dados
from fito_core import CalculadoraInventario, CalculadoraFitosso

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mutum Fito & Inventário", page_icon="🌿", layout="wide")

# CSS para Tabelas e Alertas
st.markdown("""
<style>
    .stAlert { padding: 0.5rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.title("🌿 Mutum - Validação Florestal e Fitossociologia")
st.markdown("#### Sistema de Auditoria e Análise para Licenciamento (IMASUL)")

# --- UPLOAD E ESTADO ---
if 'df_raw' not in st.session_state: st.session_state.df_raw = None

with st.expander("📂 Importação de Dados (Upload)", expanded=True):
    uploaded_file = st.file_uploader("Carregar planilha (.xlsx, .csv)", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, sep=None, engine='python') # Tenta detectar separador
            else:
                df = pd.read_excel(uploaded_file)
            
            # Padronização Automática
            df_padrao = padronizar_colunas(df)
            st.session_state.df_raw = df_padrao
            st.success(f"Arquivo carregado! {len(df)} linhas detectadas.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

# --- CORPO PRINCIPAL ---
if st.session_state.df_raw is not None:
    df = st.session_state.df_raw
    
    # Validação de Colunas Críticas
    cols_req = ['PARCELA', 'DAP', 'ALTURA']
    missing = [c for c in cols_req if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas obrigatórias não encontradas (ou não identificadas): {', '.join(missing)}")
        st.info("Verifique se os nomes estão próximos de: Parcela, DAP, Altura, Nome Científico.")
    else:
        tab_audit, tab_inv, tab_fito = st.tabs(["🕵️ 1. Auditoria & Lista Vermelha", "📊 2. Inventário (Vol)", "🌿 3. Fitossociologia"])

        # =====================================================================
        # ABA 1: AUDITORIA (O "PENTE FINO")
        # =====================================================================
        with tab_audit:
            st.markdown("### 🔍 Diagnóstico de Integridade dos Dados")
            
            col_audit1, col_audit2 = st.columns([1, 1])
            
            # --- RELATÓRIO DE ERROS ---
            with col_audit1:
                st.markdown("##### 🚨 Alertas Biométricos e Taxonômicos")
                df_log = auditoria_dados(df)
                
                if not df_log.empty:
                    n_crit = len(df_log[df_log['Tipo'].str.contains("CRÍTICO")])
                    n_err = len(df_log[df_log['Tipo'].str.contains("Erro")])
                    
                    if n_crit > 0: st.error(f"Detectadas **{n_crit}** ocorrências CRÍTICAS (Espécies Ameaçadas/Erro Grave).")
                    elif n_err > 0: st.warning(f"Detectadas **{n_err}** inconsistências prováveis.")
                    
                    st.dataframe(
                        df_log.style.applymap(
                            lambda x: 'color: red; font-weight: bold' if "CRÍTICO" in str(x) else ('color: orange' if "Alerta" in str(x) else ''), 
                            subset=['Tipo']
                        ), 
                        use_container_width=True, height=300
                    )
                else:
                    st.success("✅ Nenhum erro grave ou espécie ameaçada detectados automaticamente.")

            # --- ANÁLISE FORENSE (BENFORD) ---
            with col_audit2:
                st.markdown("##### 📉 Lei de Benford (Detecção de Fraude)")
                try:
                    # Extrai primeiro dígito do DAP (ignorando 0 e pontos)
                    daps = df['DAP'].dropna()
                    daps = daps[daps > 0]
                    first_digits = daps.astype(str).str.lstrip('0.').str[0].astype(int)
                    counts = first_digits.value_counts(normalize=True).sort_index()
                    
                    # Benford Teórico
                    digits = np.arange(1, 10)
                    benford_probs = np.log10(1 + 1/digits)
                    
                    # Gráfico
                    fig_ben = go.Figure()
                    fig_ben.add_trace(go.Bar(x=digits, y=counts.get(digits, 0), name='Dados Observados', marker_color='#1E90FF'))
                    fig_ben.add_trace(go.Scatter(x=digits, y=benford_probs, name='Lei de Benford (Esperado)', line=dict(color='red', width=3)))
                    
                    fig_ben.update_layout(title="Distribuição do 1º Dígito (DAP)", xaxis_title="Dígito", yaxis_title="Frequência", height=350)
                    st.plotly_chart(fig_ben, use_container_width=True)
                    st.caption("ℹ️ Se as barras azuis divergirem muito da linha vermelha, suspeite de manipulação de dados.")
                except:
                    st.warning("Não foi possível gerar gráfico de Benford (dados insuficientes).")

            st.divider()
            
            # --- BOXPLOTS (DISPERSÃO) ---
            st.markdown("##### 📦 Análise de Dispersão (Boxplot)")
            col_bp1, col_bp2 = st.columns(2)
            with col_bp1:
                fig_box_dap = px.box(df, y="DAP", title="Dispersão de DAP (cm)")
                st.plotly_chart(fig_box_dap, use_container_width=True)
            with col_bp2:
                fig_box_alt = px.box(df, y="ALTURA", title="Dispersão de Altura (m)")
                st.plotly_chart(fig_box_alt, use_container_width=True)

        # =====================================================================
        # ABA 2: INVENTÁRIO (VOLUME)
        # =====================================================================
        with tab_inv:
            st.markdown("### 🧮 Estatística Florestal (ACS)")
            
            c1, c2, c3, c4 = st.columns(4)
            area_tot = c1.number_input("Área Total (ha)", value=10.0)
            area_parc = c2.number_input("Área Parcela (m²)", value=1000.0)
            metodo = c3.selectbox("Método Vol", ["Fator de Forma", "Equação"])
            
            ff = 0.33
            eq_str = ""
            if metodo == "Fator de Forma":
                ff = c4.number_input("Fator (f)", value=0.33)
            else:
                eq_str = st.text_input("Equação Python (Use: DAP, ALTURA, PI, np)", "np.exp(-9.7 + 0.9*np.log(DAP**2 * ALTURA))")

            if st.button("Calcular Inventário", type="primary"):
                df_vol = CalculadoraInventario.calcular_volume(df, metodo, area_parc, ff, eq_str)
                res_est, erro_msg = CalculadoraInventario.estatistica_acs(df_vol, area_tot, area_parc)
                
                if erro_msg:
                    st.error(erro_msg)
                else:
                    # Cards de Resultado
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Volume Médio", f"{res_est['media']:.2f} m³/ha")
                    k2.metric("Erro Amostragem", f"{res_est['er']:.2f} %", delta_color="normal" if res_est['er'] <= 20 else "inverse")
                    k3.metric("IC (95%)", f"[{res_est['ic_min']:.1f}; {res_est['ic_max']:.1f}]")
                    k4.metric("Vol Total", f"{res_est['total_vol']:.0f} m³")
                    
                    if res_est['er'] > 20:
                        st.error(f"⚠️ **ATENÇÃO:** O Erro de Amostragem ({res_est['er']:.2f}%) está acima de 20%. O inventário pode ser rejeitado.")
                    else:
                        st.success("✅ Erro de Amostragem dentro do limite aceitável (< 20%).")

        # =====================================================================
        # ABA 3: FITOSSOCIOLOGIA
        # =====================================================================
        with tab_fito:
            st.markdown("### 🌿 Estrutura e Diversidade")
            
            if 'NOME_CIENTIFICO' not in df.columns:
                st.warning("⚠️ Coluna 'NOME_CIENTIFICO' não encontrada. Renomeie sua planilha.")
            else:
                tabela_ivi, indices = CalculadoraFitosso.processar(df, area_parc)
                
                # Exibe Índices Ecológicos
                i1, i2, i3, i4 = st.columns(4)
                i1.metric("Shannon (H')", f"{indices['H\' (Shannon)']:.2f}")
                i2.metric("Pielou (J')", f"{indices['J\' (Pielou)']:.2f}")
                i3.metric("Riqueza (S)", indices['Riqueza (S)'])
                i4.metric("Indivíduos (N)", indices['Indivíduos (N)'])
                
                st.divider()
                
                # Tabela IVI
                st.markdown("##### Tabela Fitossociológica (Ordenada por IVI)")
                
                # Formatação visual
                st.dataframe(
                    tabela_ivi.style.format({
                        "DA": "{:.1f}", "DR": "{:.2f}%",
                        "DoA": "{:.2f}", "DoR": "{:.2f}%",
                        "FA": "{:.1f}", "FR": "{:.2f}%",
                        "IVI": "{:.2f}"
                    }).background_gradient(subset=['IVI'], cmap='Greens'),
                    use_container_width=True
                )
                
                # Gráfico de Pareto (IVI)
                top_15 = tabela_ivi.head(15)
                fig_ivi = px.bar(top_15, x='NOME_CIENTIFICO', y='IVI', title="Top 15 Espécies (Valor de Importância)", color='IVI')
                st.plotly_chart(fig_ivi, use_container_width=True)
