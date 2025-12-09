import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import t
import io
import requests  # Necessário para conectar ao Flora do Brasil
import streamlit.components.v1 as components

# ==============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ==============================================================================

# --- LISTA DE ESPÉCIES PROTEGIDAS (Resolução Semade n.9/2015, Art. 52) ---
PROTECTED_SPECIES_MS = {
    # Espécies com fator 10
    "Peroba Rosa": 10, "Aspidosperma polyneuron": 10,
    "Cedro": 10, "Cedrela fissilis": 10,
    "Cedro Rosa": 10, "Cedrela odorata": 10,
    "Jequitibá": 10, "Cariniana legalis": 10,
    "Itaúba": 10, "Mezilaurus itaúba": 10,
    "Baraúna": 10, "Schinopsis brasiliensis": 10,
    "Quebracho": 10, "Melanoxylon brauna": 10,
    # Espécies com fator 5
    "Aroeira do Sertão": 5, "Myracrodrun urundeuva": 5,
    "Gonçalo Alves": 5, "Astronium fraxinifolium": 5,
    "Pequi": 5, "Caryocar brasiliense": 5,
    "Mangaba": 5, "Hancornia speciosa": 5,
    "Cagaita": 5, "Eugenia dysenterica Dc.": 5,
    "Guariroba": 5, "Syagrus oleracea": 5,
}

# --- FUNÇÃO INTELIGENTE DE BUSCA LOCAL (PRIORIDADE: CIENTÍFICO) ---
def get_compensation_factor(scientific_name, common_name):
    """
    Busca o fator de compensação normalizando strings.
    Prioridade: 1. Nome Científico -> 2. Nome Popular
    """
    sc_name_norm = str(scientific_name).strip().lower()
    cm_name_norm = str(common_name).strip().lower()
    protected_keys_norm = {k.strip().lower(): v for k, v in PROTECTED_SPECIES_MS.items()}
    
    if sc_name_norm in protected_keys_norm:
        return protected_keys_norm[sc_name_norm]
    if cm_name_norm in protected_keys_norm:
        return protected_keys_norm[cm_name_norm]
    return 0

# --- FUNÇÃO DE BUSCA ONLINE (API JBRJ) ---
@st.cache_data(show_spinner=False)
def buscar_nome_aceito_jbrj(nome_cientifico):
    """
    Consulta a API do Jardim Botânico (Flora e Funga do Brasil).
    Retorna o 'scientificName' aceito se for um sinônimo.
    """
    url = "https://servicos.jbrj.gov.br/flora/api/v1/taxa"
    params = {'nome': nome_cientifico}
    try:
        response = requests.get(url, params=params, timeout=3) # Timeout curto para não travar
        if response.status_code == 200:
            data = response.json()
            if data['result']:
                taxon = data['result'][0]
                if taxon.get('taxonomicStatus') == 'NOME_ACEITO':
                    return taxon.get('scientificName')
                elif taxon.get('acceptedNameUsage'):
                    return taxon.get('acceptedNameUsage').get('scientificName')
        return nome_cientifico
    except:
        return nome_cientifico

# --- FUNÇÃO DE RESET ---
def reset_app_state():
    st.session_state.resultados = None
    st.toast("Estado do sistema limpo. Redirecionando para a Aba 2.", icon="🧹")
    components.html("""<script>const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]'); if (tabs.length >= 2) { tabs[1].click(); }</script>""", height=0, width=0)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="M.U.T.U.M. - Inventário Florestal", page_icon="🌳", layout="wide")

# --- CSS VISUAL ---
st.markdown("""
<style>
    .dataframe { color: #ffffff !important; background-color: #1a1c24 !important; }
    .dataframe th { background-color: #2b2d3e !important; color: white !important; }
    .dataframe td { background-color: #1a1c24 !important; color: #e0e0e0 !important; }
    .dataframe tr:nth-child(even) td { background-color: #222430 !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INTERFACE PRINCIPAL
# ==============================================================================

st.title("🌳 M.U.T.U.M.")
st.markdown("##### Sistema de Análise de Inventário Florestal (Padrão IMASUL)")

if 'df_final' not in st.session_state: st.session_state.df_final = None
if 'resultados' not in st.session_state: st.session_state.resultados = None

tab1, tab2, tab3 = st.tabs(["📂 1. Dados & Importação", "⚙️ 2. Configuração & Cálculo", "📝 3. Relatório Final"])

# ==============================================================================
# ABA 1: IMPORTAÇÃO
# ==============================================================================
with tab1:
    st.header("Importação do Levantamento de Campo")
    st.warning("🚧 **AVISO:** Versão com Integração Flora do Brasil (Beta 0.7).")
    st.markdown("---")

    col_up_left, col_up_right = st.columns([1, 2])
    
    with col_up_left:
        st.info("💡 **Instruções:** Baixe o modelo Excel, preencha e faça o upload.")
        def gerar_modelo_xlsx():
            colunas_modelo = ["Parcela", "Área da Parcela", "Núm. Árvore", "Núm. Fuste", "Nome Científico", "Nome Comum", "Família", "CAP", "DAP", "Alt. Total", "Alt. Comercial", "Qual. Fuste", "X", "Y"]
            df_modelo = pd.DataFrame(columns=colunas_modelo)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_modelo.to_excel(writer, index=False, sheet_name='Campo')
            return buffer.getvalue()

        st.download_button(label="📥 Baixar Modelo (Excel .xlsx)", data=gerar_modelo_xlsx(), file_name="Modelo_Mutum.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with col_up_right:
        uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=["xlsx", "csv"])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file, sep=';' if b';' in uploaded_file.getvalue() else ',')
            else:
                df_raw = pd.read_excel(uploaded_file)

            df_raw.columns = df_raw.columns.str.strip()
            # Validação básica
            if 'DAP' not in df_raw.columns and 'CAP' not in df_raw.columns:
                st.error("❌ Falta coluna de diâmetro (CAP ou DAP).")
            else:
                df_proc = df_raw.copy()
                cols_num = ['DAP', 'CAP', 'Alt. Comercial', 'Alt. Total', 'Parcela']
                for col in cols_num:
                    if col in df_proc.columns:
                        if df_proc[col].dtype == object: df_proc[col] = df_proc[col].astype(str).str.replace(',', '.')
                        df_proc[col] = pd.to_numeric(df_proc[col], errors='coerce')

                if 'DAP' not in df_proc.columns: df_proc['DAP'] = np.nan
                if 'CAP' in df_proc.columns:
                    mask = (df_proc['DAP'].isna()) | (df_proc['DAP'] == 0)
                    df_proc.loc[mask, 'DAP'] = df_proc.loc[mask, 'CAP'] / np.pi

                df_proc = df_proc.dropna(subset=['Parcela', 'DAP'])
                df_proc = df_proc[df_proc['DAP'] > 0] 
                st.session_state.df_final = df_proc
                st.success("✅ Importação realizada com sucesso!")
                
                # Resumo rápido
                c1, c2, c3 = st.columns(3)
                c1.metric("Indivíduos", len(df_proc))
                c2.metric("Espécies", df_proc['Nome Comum'].nunique() if 'Nome Comum' in df_proc.columns else 0)
                with st.expander("Ver Tabela"): st.dataframe(df_proc, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: CÁLCULO
# ==============================================================================
with tab2:
    if st.session_state.df_final is None:
        st.warning("👈 Realize a importação na Aba 1 primeiro.")
    else:
        st.header("⚙️ Parâmetros do Inventário")
        
        c1, c2, c3 = st.columns(3)
        with c1: area_total_ha = st.number_input("Área Total (ha)", value=10.0, step=0.01)
        with c2: area_parcela_m2 = st.number_input("Área Parcela (m²)", value=1000.0, step=10.0)
        with c3: tipo_altura_calc = st.selectbox("Altura Ref.", ["Alt. Comercial", "Alt. Total"])

        st.markdown("---")
        if st.button("🚀 Calcular Resultados e Verificar Espécies (Online)", type="primary"):
            try:
                df_calc = st.session_state.df_final.copy()
                
                # CÁLCULO DE VOLUME (Simplificado para o exemplo)
                # Assume Fator de Forma 0.7 se não especificado
                df_calc['Vol_Ind'] = (np.pi * (df_calc['DAP']**2) / 40000) * df_calc[tipo_altura_calc] * 0.7

                # ESTATÍSTICA BÁSICA
                df_parcelas = df_calc.groupby('Parcela')['Vol_Ind'].sum().reset_index()
                fator_extrapolacao_ha = 10000 / area_parcela_m2
                df_parcelas['Vol_ha'] = df_parcelas['Vol_Ind'] * fator_extrapolacao_ha
                
                n = len(df_parcelas)
                if n < 2: raise ValueError("Mínimo de 2 parcelas necessário.")
                
                media = df_parcelas['Vol_ha'].mean()
                variancia = df_parcelas['Vol_ha'].var(ddof=1)
                desvio = np.sqrt(variancia)
                cv = (desvio / media) * 100
                
                # Totais
                N = (area_total_ha * 10000) / area_parcela_m2
                t_val = t.ppf(0.975, df=n-1)
                erro_padrao = np.sqrt((variancia / n) * (1 - n/N))
                ea = t_val * erro_padrao
                er = (ea / media) * 100
                total_vol = media * area_total_ha
                ic_inf = media - ea
                ic_sup = media + ea

                # --- PREPARAÇÃO PARA COMPENSAÇÃO ---
                df_calc['Nome Comum'] = df_calc['Nome Comum'].astype(str)
                df_calc['Nome Científico'] = df_calc['Nome Científico'].astype(str)
                df_calc['Família'] = df_calc['Família'].astype(str)

                # >>> CORREÇÃO DO ERRO: DEFINIR df_contagem_amostra ANTES DE TUDO <<<
                df_contagem_amostra = df_calc.groupby(['Nome Comum', 'Nome Científico']).size().reset_index(name='N_Amostra')

                # --- INTEGRAÇÃO COM FLORA DO BRASIL (API) ---
                st.info("🌐 Conectando ao Flora e Funga do Brasil para verificar sinônimos...")
                
                unique_species = df_calc['Nome Científico'].unique()
                mapa_sinonimos = {}
                
                bar = st.progress(0)
                for i, sp in enumerate(unique_species):
                    nome_limpo = str(sp).strip()
                    if len(nome_limpo) > 3:
                        nome_aceito = buscar_nome_aceito_jbrj(nome_limpo)
                        if nome_aceito and nome_aceito.lower() != nome_limpo.lower():
                            mapa_sinonimos[nome_limpo] = nome_aceito
                    bar.progress((i + 1) / len(unique_species))
                bar.empty()

                if mapa_sinonimos:
                    st.toast(f"{len(mapa_sinonimos)} nomes científicos atualizados!", icon="🔄")

                # --- LOOP DE COMPENSAÇÃO ---
                compensacao_list = []
                Fator_Extrapolacao_pop = area_total_ha / (n * area_parcela_m2 / 10000)
                
                for index, row in df_contagem_amostra.iterrows():
                    nome_comum = str(row['Nome Comum']).strip()
                    nome_cientifico_original = str(row['Nome Científico']).strip()
                    n_amostra = row['N_Amostra']
                    
                    # Verifica se temos um sinônimo detectado pela API
                    nome_para_verificar = mapa_sinonimos.get(nome_cientifico_original, nome_cientifico_original)
                    
                    # Busca o fator
                    compensacao_fator = get_compensation_factor(nome_para_verificar, nome_comum)
                        
                    if compensacao_fator > 0:
                        N_Estimado = n_amostra * Fator_Extrapolacao_pop
                        Mudas_Compensacao = np.ceil(N_Estimado) * compensacao_fator
                        
                        obs = f"(Sinônimo de {nome_para_verificar})" if nome_cientifico_original != nome_para_verificar else ""
                        
                        compensacao_list.append({
                            "Espécie": nome_comum, 
                            "Nome Científico": f"{nome_cientifico_original} {obs}", 
                            "N_Amostra": n_amostra,
                            "Fator_Compensacao": compensacao_fator, 
                            "N_Estimado": N_Estimado, 
                            "Mudas_Compensacao": Mudas_Compensacao
                        })

                # SALVAR RESULTADOS
                st.session_state.resultados = {
                    "stats": {
                        "media": media, "var": variancia, "dp": desvio, "cv": cv,
                        "ep": erro_padrao, "t": t_val, "ea": ea, "er": er, "ic_inf": ic_inf, "ic_sup": ic_sup,
                        "tot_vol": total_vol, "n": n, "N": N, "area_total": area_total_ha, "area_amostrada": n * area_parcela_m2 / 10000,
                        "top_sp": df_calc['Nome Comum'].mode()[0] if not df_calc.empty else "-",
                        "top_fam": df_calc['Família'].mode()[0] if not df_calc.empty else "-"
                    },
                    "compensacao_df": pd.DataFrame(compensacao_list)
                }
                
                st.toast("Cálculo realizado! Redirecionando...", icon="✅")
                components.html("""<script> const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]'); if (tabs.length >= 3) { tabs[2].click(); } </script>""", height=0, width=0)

            except ValueError as ve:
                st.error(f"Erro de Cálculo: {ve}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")

# ==============================================================================
# ABA 3: RELATÓRIO
# ==============================================================================
with tab3:
    if st.session_state.resultados is None:
        st.warning("👈 Realize o cálculo na Aba 2.")
    else:
        res = st.session_state.resultados["stats"]
        df_comp = st.session_state.resultados["compensacao_df"]
        
        st.markdown("## 📋 Relatório Técnico")
        st.markdown("---")

        c1, c2 = st.columns(2)
        c1.write(f"**Área Total:** {res['area_total']:.4f} ha")
        c1.write(f"**Volume Total:** {res['tot_vol']:.2f} m³")
        c2.write(f"**Erro de Amostragem:** {res['er']:.2f}%")
        
        if res['er'] <= 20: c2.success("Inventário Aprovado (Erro < 20%)")
        else: c2.error("Inventário Insuficiente (Erro > 20%)")

        st.markdown("---")
        st.markdown("### 🌳 Compensação Ambiental (Lei Semade 9/2015)")
        
        if not df_comp.empty:
            total_mudas = int(df_comp['Mudas_Compensacao'].sum())
            st.error(f"**Total de Mudas Exigidas:** {total_mudas}")
            st.dataframe(df_comp, hide_index=True, use_container_width=True)
        else:
            st.success("Nenhuma espécie protegida identificada na amostra.")

        st.button("Limpar Tudo", on_click=reset_app_state)
