# fito_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- IMPORTAÇÃO DOS MÓDULOS INTERNOS ---
try:
    # Tenta importar os módulos que criamos
    from fito_config import LISTA_IMASUL_COMPENSACAO
    from fito_utils import padronizar_colunas, auditoria_dados
    from fito_core import CalculadoraInventario, CalculadoraFitosso
except ImportError as e:
    st.error(f"Erro ao importar módulos internos: {e}. Verifique se fito_config.py, fito_utils.py e fito_core.py estão na mesma pasta.")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="M.U.T.U.M. - Fitossociologia & Inventário", 
    page_icon="🌿", 
    layout="wide"
)

# Estilização (CSS) para impressão e alertas visuais
st.markdown("""
<style>
    .stAlert { padding: 0.5rem; border-radius: 5px; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
    /* Oculta sidebar na impressão */
    @media print {
        [data-testid="stSidebar"], .stButton, .stFileUploader { display: none !important; }
        .block-container { padding-top: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🐦 M.U.T.U.M. - Validação Florestal")
st.markdown("#### Sistema de Auditoria de Inventário e Caracterização de Vegetação")

# --- BARRA LATERAL (CONFIGURAÇÕES GERAIS) ---
with st.sidebar:
    st.header("1. Projeto")
    tipologia = st.selectbox(
        "Tipologia Vegetal Declarada:", 
        ["Savana Arbórea Aberta (Cerradão)", "Savana Arbórea Densa", "Floresta Estacional", "Chaco", "Outro"]
    )
    st.info(f"Analisando parâmetros para: **{tipologia}**")
    st.divider()
    st.header("2. Arquivo")
    uploaded_file = st.file_uploader("Upload Planilha de Campo (.xlsx, .csv)", type=["xlsx", "csv"])
    
    st.caption("Certifique-se que sua planilha tenha as colunas: Parcela, DAP, Altura e Nome Científico.")

# --- ESTADO DA SESSÃO ---
if 'df_raw' not in st.session_state: st.session_state.df_raw = None

# --- PROCESSAMENTO DO UPLOAD ---
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            # Tenta ler CSV (detectando separador automaticamente se possível, ou usando ;)
            try:
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                if len(df.columns) < 2: # Se falhar, tenta vírgula
                     uploaded_file.seek(0)
                     df = pd.read_csv(uploaded_file, sep=',')
            except:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
        
        # Padroniza nomes de colunas (DAP, ALTURA, PARCELA, etc.) usando nosso utils
        df_padrao = padronizar_colunas(df)
        st.session_state.df_raw = df_padrao
        st.sidebar.success(f"✅ Arquivo processado: {len(df)} árvores identificadas.")
    except Exception as e:
        st.error(f"Erro crítico ao ler arquivo: {e}")

# --- CORPO PRINCIPAL ---
if st.session_state.df_raw is not None:
    df = st.session_state.df_raw
    
    # Verificação mínima de colunas para não quebrar o código
    required = ['PARCELA', 'DAP']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Colunas obrigatórias faltando: {', '.join(missing)}")
        st.warning("O sistema espera colunas como: 'Parcela', 'DAP', 'Altura', 'Nome Científico'. Verifique o cabeçalho do seu Excel.")
    else:
        # TABS DE NAVEGAÇÃO
        tab_audit, tab_inv, tab_fito = st.tabs([
            "🕵️ 1. Auditoria & Biometria", 
            "📊 2. Inventário (Volume)", 
            "🌿 3. Fitossociologia (Estrutura)"
        ])

        # =====================================================================
        # ABA 1: AUDITORIA (VALIDAÇÃO DE DADOS)
        # =====================================================================
        with tab_audit:
            st.markdown("### 🔍 Diagnóstico de Integridade e Fraude")
            
            c1, c2 = st.columns(2)
            
            # 1.1 Relatório de Erros (usa fito_utils.auditoria_dados)
            with c1:
                st.markdown("##### 🚨 Alertas Biométricos e Espécies Ameaçadas")
                with st.spinner("Cruzando dados com Lista Vermelha MMA..."):
                    # Aqui a mágica acontece: ele cruza com o CSV do MMA
                    df_log = auditoria_dados(df)
                
                if not df_log.empty:
                    # Filtros de gravidade para exibir mensagens
                    criticos = df_log[df_log['Tipo'].str.contains("CRÍTICO|Ameaçada")]
                    erros = df_log[df_log['Tipo'].str.contains("Erro")]
                    alertas = df_log[df_log['Tipo'].str.contains("Alerta")]
                    
                    if not criticos.empty:
                        st.error(f"⛔ **BLOQUEANTE:** Encontradas {len(criticos)} espécies Ameaçadas ou Erros Críticos.")
                    elif not erros.empty:
                        st.warning(f"⚠️ **ATENÇÃO:** Encontrados {len(erros)} erros de consistência (ex: árvore 'panqueca').")
                    else:
                        st.info(f"ℹ️ Encontrados {len(alertas)} alertas de verificação.")
                    
                    # Exibe tabela colorida
                    st.dataframe(
                        df_log.style.map(
                            lambda x: 'color: red; font-weight: bold' if "CRÍTICO" in str(x) else ('color: orange' if "Alerta" in str(x) else ''), 
                            subset=['Tipo']
                        ), use_container_width=True, height=350
                    )
                else:
                    st.success("✅ Nenhum problema grave detectado na varredura automática.")

            # 1.2 Lei de Benford (Fraude Numérica)
            with c2:
                st.markdown("##### 📉 Teste da Lei de Benford (1º Dígito do DAP)")
                st.caption("Verifica se os dados de DAP seguem um padrão natural ou se foram 'inventados'.")
                try:
                    daps = df['DAP'].dropna()
                    daps = daps[daps > 0]
                    # Pega o primeiro dígito significativo (1-9)
                    first_digits = daps.astype(str).str.lstrip('0.').str[0].astype(int)
                    counts = first_digits.value_counts(normalize=True).sort_index()
                    
                    # Distribuição Teórica de Benford
                    digits = np.arange(1, 10)
                    benford_probs = np.log10(1 + 1/digits)
                    
                    fig_ben = go.Figure()
                    fig_ben.add_trace(go.Bar(x=digits, y=counts.get(digits, 0), name='Seu Inventário', marker_color='#4682B4'))
                    fig_ben.add_trace(go.Scatter(x=digits, y=benford_probs, name='Padrão Natural (Benford)', line=dict(color='red', width=3, dash='dash')))
                    
                    fig_ben.update_layout(xaxis_title="Dígito (1-9)", yaxis_title="Frequência", height=350, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_ben, use_container_width=True)
                    
                    # Interpretação básica para o usuário
                    diff_1 = abs(counts.get(1, 0) - benford_probs[0])
                    if diff_1 > 0.15: # 15% de diferença no dígito 1 é suspeito
                         st.error("⚠️ **Alerta de Fraude:** A distribuição dos dados desvia significativamente do padrão natural (Lei de Benford).")
                except:
                    st.warning("Dados insuficientes para teste de Benford.")

            st.divider()
            
            # 1.3 Boxplots (Dispersão)
            st.markdown("##### 📦 Análise de Dispersão (Detecção de 'Achatamento')")
            cb1, cb2 = st.columns(2)
            with cb1:
                fig_dap = px.box(df, y="DAP", title="Boxplot DAP (cm) - Verifique Outliers")
                st.plotly_chart(fig_dap, use_container_width=True)
            with cb2:
                col_h = 'ALTURA_COMERCIAL' if 'ALTURA_COMERCIAL' in df.columns else 'ALTURA'
                fig_alt = px.box(df, y=col_h, title=f"Boxplot Altura ({col_h}) (m)")
                st.plotly_chart(fig_alt, use_container_width=True)

        # =====================================================================
        # ABA 2: INVENTÁRIO (VOLUME)
        # =====================================================================
        with tab_inv:
            st.markdown("### 🧮 Cálculo Volumétrico e Estatística (ACS)")
            
            # Formulário de Configuração
            with st.form("calc_form"):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                area_tot = col_f1.number_input("Área Total (ha)", value=10.0, step=0.1)
                area_parc = col_f2.number_input("Área Parcela (m²)", value=1000.0, step=100.0)
                metodo = col_f3.selectbox("Método Volume", ["Fator de Forma", "Equação Personalizada"])
                
                ff = 0.33
                eq_user = ""
                if metodo == "Fator de Forma":
                    ff = col_f4.number_input("Fator de Forma (f)", value=0.33, step=0.01)
                else:
                    eq_user = st.text_input("Equação Python (Vars: DAP, ALTURA)", "np.exp(-9.7 + 0.9*np.log(DAP**2 * ALTURA))")
                
                btn_calc = st.form_submit_button("🚀 Calcular Estatística", type="primary")

            if btn_calc:
                with st.spinner("Processando estatística inferencial..."):
                    # Chama o cálculo no fito_core.py
                    df_vol = CalculadoraInventario.calcular_volume(df, metodo, area_parc, ff, eq_user)
                    res, err = CalculadoraInventario.estatistica_acs(df_vol, area_tot, area_parc)
                
                if err:
                    st.error(err)
                else:
                    st.divider()
                    # Dashboard de Resultados
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Volume Médio", f"{res['media']:.2f} m³/ha", help="Média estimada por hectare")
                    
                    delta_color = "normal" if res['er'] <= 20 else "inverse"
                    k2.metric("Erro de Amostragem", f"{res['er']:.2f} %", delta_color=delta_color, help="Limite aceitável: 20%")
                    
                    k3.metric("IC [Min; Max]", f"[{res['ic_min']:.1f}; {res['ic_max']:.1f}]", help="Intervalo de Confiança 95%")
                    k4.metric("Volume Total", f"{res['total_vol']:.0f} m³", help=f"Para {area_tot} hectares")

                    if res['er'] > 20:
                        st.error(f"❌ **REPROVADO:** O Erro de Amostragem ({res['er']:.2f}%) excede o limite de 20%. Necessário amostrar mais parcelas.")
                    else:
                        st.success(f"✅ **APROVADO:** O levantamento atende a precisão requerida ({res['er']:.2f}%).")
                    
                    with st.expander("Ver Tabela Resumo Estatístico"):
                        st.json(res)

        # =====================================================================
        # ABA 3: FITOSSOCIOLOGIA (ESTRUTURA)
        # =====================================================================
        with tab_fito:
            st.markdown(f"### 🌿 Caracterização da Vegetação: {tipologia}")
            st.caption("Análise estrutural para validar a tipologia declarada (Áreas de Encrave).")
            
            if 'NOME_CIENTIFICO' not in df.columns:
                st.warning("⚠️ Coluna 'NOME_CIENTIFICO' não encontrada. O sistema tentará usar 'NOME_COMUM'.")
            
            # Processamento Fitossociológico no fito_core.py
            tabela_ivi, indices = CalculadoraFitosso.processar(df, area_parc)
            
            # 3.1 Índices Ecológicos (Cards)
            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            col_i1.metric("Shannon (H')", f"{indices['H\' (Shannon)']:.2f}", help="Diversidade. Cerradão conservado geralmente > 2.0")
            col_i2.metric("Pielou (J')", f"{indices['J\' (Pielou)']:.2f}", help="Equabilidade (0-1). Próximo a 1 indica distribuição uniforme.")
            col_i3.metric("Riqueza (S)", f"{indices['Riqueza (S)']}", help="Número de espécies encontradas.")
            col_i4.metric("Área Basal (G)", f"{indices['Area Basal Total (G)']:.2f} m²/ha", help="Ocupação do solo.")
            
            # Validação Simples de Tipologia (Regras de Bolso)
            if tipologia == "Savana Arbórea Aberta (Cerradão)":
                if indices['H\' (Shannon)'] < 2.0:
                    st.warning(f"⚠️ **Alerta de Tipologia:** Índice de Shannon ({indices['H\' (Shannon)']:.2f}) baixo para um Cerradão típico. Pode indicar antropização ou transição.")
                else:
                    st.success("✅ Índice de diversidade compatível com formações savânicas/florestais.")

            st.divider()
            
            # 3.2 Tabela IVI (Heatmap)
            st.markdown("##### 🏆 Tabela Fitossociológica (Top Espécies por IVI)")
            # Exibe com gradiente de cor no IVI para destacar as dominantes
            st.dataframe(
                tabela_ivi.style.format({
                    "DA": "{:.1f}", "DR": "{:.2f}%",
                    "DoA": "{:.2f}", "DoR": "{:.2f}%",
                    "FA": "{:.1f}", "FR": "{:.2f}%",
                    "IVI": "{:.2f}"
                }).background_gradient(subset=['IVI'], cmap='Greens'),
                use_container_width=True, height=400
            )
            
            # 3.3 Gráficos
            g1, g2 = st.columns(2)
            with g1:
                # Gráfico de Pareto (IVI)
                top15 = tabela_ivi.head(15)
                # Ordena para o gráfico ficar bonito (maior em cima)
                top15 = top15.sort_values('IVI', ascending=True) 
                fig_ivi = px.bar(top15, x='IVI', y='NOME_CIENTIFICO', orientation='h', title="Top 15 Espécies (IVI)", color='IVI')
                st.plotly_chart(fig_ivi, use_container_width=True)
            
            with g2:
                # Distribuição Diamétrica (Jota Invertido)
                st.markdown("##### 🌲 Estrutura Diamétrica (Jota Invertido)")
                try:
                    # Cria classes de diâmetro (5 em 5 cm)
                    bins = np.arange(0, df['DAP'].max() + 5, 5)
                    labels = [f"{int(b)}-{int(b+5)}" for b in bins[:-1]]
                    # Cria coluna temporária para o gráfico
                    df_graf = df.copy()
                    df_graf['Classe_DAP'] = pd.cut(df_graf['DAP'], bins=bins, labels=labels, right=False)
                    contagem_classes = df_graf['Classe_DAP'].value_counts().sort_index()
                    
                    fig_jota = px.bar(x=contagem_classes.index.astype(str), y=contagem_classes.values, 
                                      title="Distribuição de Diâmetros (Esperado: Decrescente)")
                    fig_jota.update_xaxes(title="Classe de DAP (cm)")
                    fig_jota.update_yaxes(title="Nº Indivíduos")
                    st.plotly_chart(fig_jota, use_container_width=True)
                    
                    # Verificação rápida do "Jota"
                    if len(contagem_classes) > 2:
                        if contagem_classes.iloc[0] < contagem_classes.iloc[1]:
                             st.info("ℹ️ A distribuição não apresenta o formato clássico de 'Jota Invertido' perfeito (falta de regeneração nas classes iniciais?).")
                except Exception as e:
                    st.warning(f"Não foi possível gerar gráfico diamétrico: {e}")
