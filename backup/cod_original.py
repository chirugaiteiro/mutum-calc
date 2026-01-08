import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import t
import io
import streamlit.components.v1 as components

# --- LISTA DE ESPÉCIES PROTEGIDAS (Resolução Semade n.9/2015, Art. 52) ---
PROTECTED_SPECIES_MS = {
# --- GRUPO FATOR 10 ---
    "Peroba Rosa": 10, "Aspidosperma polyneuron": 10,
    "Cedro": 10, "Cedrela fissilis": 10, "Cedrela brasiliensis": 10, # Sinônimo
    "Cedro Rosa": 10, "Cedrela odorata": 10, "Cedrela mexicana": 10, # Sinônimo
    "Jequitibá": 10, "Cariniana legalis": 10, "Cariniana brasiliensis": 10, # Sinônimo
    "Itaúba": 10, "Mezilaurus itaúba": 10, "Mezilaurus itauba": 10, "Silvia itauba": 10, # Sinônimo
    "Baraúna": 10, "Schinopsis brasiliensis": 10, "Schinopsis glabra": 10, # Sinônimo
    "Quebracho": 10, "Melanoxylon brauna": 10, "Braúna": 10,
    
    # --- GRUPO FATOR 5 ---
    "Aroeira do Sertão": 5, "Myracrodrun urundeuva": 5, "Astronium urundeuva": 5, # Sinônimo MUITO comum
    "Aroeira": 5, "Astronium juglandifolium": 5, # Sinônimo
    "Gonçalo Alves": 5, "Astronium fraxinifolium": 5, "Astronium graveolens": 5, "Astonium graveolens": 5, "Astonium fraxinifolium": 5, "Astronium Fraxinifolium": 5, "Astronium Graveolens": 5, "Astonium Graveolens": 5, "Astronium Fraxinifolium": 5, # Confusão comum, melhor prevenir
    "Pequi": 5, "Caryocar brasiliense": 5, "Caryocar coriaceum": 5,
    "Mangaba": 5, "Hancornia speciosa": 5,
    "Cagaita": 5, "Eugenia dysenterica": 5, "Eugenia dysenterica Dc.": 5, "Stenocalyx dysentericus": 5, # Sinônimo antigo
    "Guariroba": 5, "Syagrus oleracea": 5, "Cocos oleracea": 5, # Sinônimo antigo
    "Gueroba": 5,
}

# --- FUNÇÃO DE RESET (Limpa estado e redireciona) ---
def reset_app_state():
    st.session_state.resultados = None
    st.toast("Estado do sistema limpo. Redirecionando para a Aba 2.", icon="🧹")
    components.html(
        """
        <script>
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            if (tabs.length >= 2) { tabs[1].click(); }
        </script>
        """,
        height=0, width=0
    )


# --- Configuração da Página ---
st.set_page_config(
    page_title="M.U.T.U.M. - Inventário Florestal",
    page_icon="🌳",
    layout="wide"
)

# --- CSS VISUAL (Mantido) ---
st.markdown("""
<style>
    .dataframe { color: #ffffff !important; background-color: #1a1c24 !important; }
    .dataframe th { background-color: #2b2d3e !important; color: white !important; }
    .dataframe td { background-color: #1a1c24 !important; color: #e0e0e0 !important; }
    .dataframe tr:nth-child(even) td { background-color: #222430 !important; }
    @media print { * { color: black !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
</style>
""", unsafe_allow_html=True)


st.title("🌳 M.U.T.U.M.")
st.markdown("##### Sistema de Análise de Inventário Florestal (Padrão IMASUL)")

# --- Gerenciamento de Estado ---
if 'df_final' not in st.session_state: st.session_state.df_final = None
if 'resultados' not in st.session_state: st.session_state.resultados = None

tab1, tab2, tab3 = st.tabs(["📂 1. Dados & Importação", "⚙️ 2. Configuração & Cálculo", "📝 3. Relatório Final"])

# ==============================================================================
# ABA 1: IMPORTAÇÃO E DASHBOARD COMPLETO
# ==============================================================================
with tab1:
    st.header("Importação do Levantamento de Campo")
    
    # --- NOVO AVISO DE VERSÃO BETA ---
    st.warning("🚧 **AVISO:** Esta ferramenta está na **Versão Beta 0.5** e deve ser usada apenas para testes e verificação. A responsabilidade técnica é do engenheiro florestal responsável.")
    st.markdown("---")

    col_up_left, col_up_right = st.columns([1, 2])
    
    with col_up_left:
        st.info("💡 **Instruções:** Baixe o modelo Excel, preencha e faça o upload.")
        
        def gerar_modelo_xlsx():
            colunas_modelo = [
                "Parcela", "Área da Parcela", "Núm. Árvore", "Núm. Fuste", 
                "Nome Científico", "Nome Comum", "Família", 
                "CAP", "DAP", "Alt. Total", "Alt. Comercial", "Qual. Fuste", "X", "Y"
            ]
            df_modelo = pd.DataFrame(columns=colunas_modelo)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_modelo.to_excel(writer, index=False, sheet_name='Campo')
            return buffer.getvalue()

        st.download_button(
            label="📥 Baixar Modelo (Excel .xlsx)",
            data=gerar_modelo_xlsx(),
            file_name="Modelo_Mutum.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_up_right:
        uploaded_file = st.file_uploader("Arraste sua planilha aqui (Excel ou CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        try:
            # Leitura
            if uploaded_file.name.endswith('.csv'):
                try:
                    df_raw = pd.read_csv(uploaded_file, sep=';')
                    if len(df_raw.columns) < 2:
                        uploaded_file.seek(0)
                        df_raw = pd.read_csv(uploaded_file, sep=',')
                except:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=',')
            else:
                df_raw = pd.read_excel(uploaded_file)

            df_raw.columns = df_raw.columns.str.strip()

            # Validação e Tratamento
            colunas_obrigatorias = ['Parcela', 'Alt. Comercial', 'Alt. Total']
            if not all(c in df_raw.columns for c in colunas_obrigatorias):
                st.error("❌ Faltam colunas obrigatórias: Parcela, Alt. Comercial ou Alt. Total.")
            elif not ('DAP' in df_raw.columns or 'CAP' in df_raw.columns):
                st.error("❌ Falta coluna de diâmetro (CAP ou DAP).")
            else:
                df_proc = df_raw.copy()
                cols_num = ['DAP', 'CAP', 'Alt. Comercial', 'Alt. Total', 'Parcela']
                for col in cols_num:
                    if col in df_proc.columns:
                        if df_proc[col].dtype == object:
                             df_proc[col] = df_proc[col].astype(str).str.replace(',', '.')
                        df_proc[col] = pd.to_numeric(df_proc[col], errors='coerce')

                if 'DAP' not in df_proc.columns: df_proc['DAP'] = np.nan
                if 'CAP' in df_proc.columns:
                    mask = (df_proc['DAP'].isna()) | (df_proc['DAP'] == 0)
                    df_proc.loc[mask, 'DAP'] = df_proc.loc[mask, 'CAP'] / np.pi

                df_proc = df_proc.dropna(subset=['Parcela', 'DAP'])
                df_proc = df_proc[df_proc['DAP'] > 0] 
                st.session_state.df_final = df_proc

                st.success("✅ Importação realizada com sucesso!")
                st.markdown("---")

                # Dashboard (Mantido)
                qtd_parcelas = df_proc['Parcela'].nunique()
                qtd_arvores = len(df_proc)
                n_especies = df_proc['Nome Comum'].nunique() if 'Nome Comum' in df_proc.columns else 0
                n_familias = df_proc['Família'].nunique() if 'Família' in df_proc.columns else 0

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Parcelas", qtd_parcelas)
                c2.metric("Indivíduos", qtd_arvores)
                c3.metric("Espécies", n_especies)
                c4.metric("Famílias", n_familias)

                st.markdown("##### 📏 Conferência de Variáveis")
                dap_min, dap_max, dap_med = df_proc['DAP'].min(), df_proc['DAP'].max(), df_proc['DAP'].mean()
                col_h = 'Alt. Comercial' if df_proc['Alt. Comercial'].sum() > 0 else 'Alt. Total'
                h_min, h_max, h_med = df_proc[col_h].min(), df_proc[col_h].max(), df_proc[col_h].mean()

                k1, k2, k3, k4, k5, k6 = st.columns(6)
                k1.metric("DAP Mín", f"{dap_min:.1f}")
                k2.metric("DAP Méd", f"{dap_med:.1f}")
                k3.metric("DAP Máx", f"{dap_max:.1f}")
                k4.metric(f"H. Mín", f"{h_min:.1f}")
                k5.metric(f"H. Méd", f"{h_med:.1f}")
                k6.metric(f"H. Máx", f"{h_max:.1f}")

                with st.expander("🔍 Visualizar Tabela Completa de Dados", expanded=True):
                    st.dataframe(df_proc, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# ABA 2: CONFIGURAÇÃO E CÁLCULO
# ==============================================================================
with tab2:
    if st.session_state.df_final is None:
        st.warning("👈 Realize a importação na Aba 1 primeiro.")
    else:
        st.header("⚙️ Parâmetros do Inventário")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            area_total_ha = st.number_input("Área Total do Projeto (ha)", value=10.0, step=0.01, format="%.4f")
        with c2:
            area_parcela_m2 = st.number_input("Área da Parcela (m²)", value=1000.0, step=10.0)
        with c3:
            tipo_altura_calc = st.selectbox("Altura para Cálculo:", ["Alt. Comercial", "Alt. Total"], index=0)

        st.markdown("---")
        tipo_calculo = st.radio("Método de Volume:", ["Fator de Forma (f)", "Equação Personalizada"], horizontal=True)
        
        ff_input = 0.7
        equacao_user = ""

        if tipo_calculo == "Fator de Forma (f)":
            ff_input = st.number_input("Valor de f:", value=0.4, step=0.01)
        else:
            equacao_user = st.text_input("Equação:", value="DAP * DAP * ALTURA * 0.00007854 * 0.4", help="Use DAP, ALTURA e CAP como variáveis.")

        st.markdown("---")
        
        if st.button("🚀 Calcular Resultados", type="primary"):
            try:
                df_calc = st.session_state.df_final.copy()
                
                # CÁLCULO DE VOLUME INDIVIDUAL
                if tipo_calculo == "Fator de Forma (f)":
                    df_calc['Vol_Ind'] = (np.pi * (df_calc['DAP']**2) / 40000) * df_calc[tipo_altura_calc] * ff_input
                else:
                    eq_proc = equacao_user.replace("ALTURA", f"df_calc['{tipo_altura_calc}']")
                    eq_proc = eq_proc.replace("DAP", "df_calc['DAP']").replace("CAP", "df_calc['CAP']").replace("PI", "np.pi")
                    df_calc['Vol_Ind'] = eval(eq_proc)

                # Estatística e Extrapolação
                df_parcelas = df_calc.groupby('Parcela')['Vol_Ind'].sum().reset_index()
                fator_extrapolacao_ha = 10000 / area_parcela_m2
                df_parcelas['Vol_ha'] = df_parcelas['Vol_Ind'] * fator_extrapolacao_ha
                
                n = len(df_parcelas)
                Area_Amostrada_ha = n * (area_parcela_m2 / 10000)

                if n < 2:
                    st.error("Erro: Mínimo de 2 parcelas necessário.")
                else:
                    N = (area_total_ha * 10000) / area_parcela_m2
                    media = df_parcelas['Vol_ha'].mean()
                    
                    # --- GUARDA DE ESTABILIDADE CRÍTICA ---
                    if media <= 0 or np.isnan(media) or df_parcelas.empty or df_parcelas['Vol_ha'].isnull().all():
                         raise ValueError("Média de volume (m³/ha) inválida. Verifique se as colunas de Altura e DAP estão preenchidas corretamente (volume > 0).")
                        
                    variancia = df_parcelas['Vol_ha'].var(ddof=1)
                    desvio = np.sqrt(variancia)
                    cv = (desvio / media) * 100
                    
                    f = n / N
                    fpc = 1 - f if (1-f) > 0 else 0
                    var_media = (variancia / n) * fpc
                    erro_padrao = np.sqrt(var_media)
                    
                    t_val = t.ppf(0.975, df=n-1)
                    ea = t_val * erro_padrao
                    er = (ea / media) * 100
                    
                    ic_inf = media - ea
                    ic_sup = media + ea
                    
                    # Totais
                    total_vol = media * area_total_ha
                    total_ea = ea * area_total_ha
                    total_ic_inf = ic_inf * area_total_ha
                    total_ic_sup = ic_sup * area_total_ha

                    # Florística e Compensação
                    df_calc['Nome Comum'] = df_calc['Nome Comum'].astype(str)
                    df_calc['Nome Científico'] = df_calc['Nome Científico'].astype(str)
                    df_calc['Família'] = df_calc['Família'].astype(str)

                    top_sp = df_calc['Nome Comum'].mode()[0] if 'Nome Comum' in df_calc.columns and not df_calc['Nome Comum'].empty else "-"
                    top_fam = df_calc['Família'].mode()[0] if 'Família' in df_calc.columns and not df_calc['Família'].empty else "-"

                    df_contagem_amostra = df_calc.groupby(['Nome Comum', 'Nome Científico']).size().reset_index(name='N_Amostra')
                    compensacao_list = []
                    Fator_Extrapolacao_pop = area_total_ha / Area_Amostrada_ha if Area_Amostrada_ha > 0 else 0
                    
                    for index, row in df_contagem_amostra.iterrows():
                        nome_comum = str(row['Nome Comum']).strip()
                        nome_cientifico = str(row['Nome Científico']).strip()
                        n_amostra = row['N_Amostra']
                        
                        compensacao_fator = PROTECTED_SPECIES_MS.get(nome_cientifico, PROTECTED_SPECIES_MS.get(nome_comum, 0))
                            
                        if compensacao_fator > 0:
                            N_Estimado = n_amostra * Fator_Extrapolacao_pop
                            Mudas_Compensacao = np.ceil(N_Estimado) * compensacao_fator
                            
                            compensacao_list.append({
                                "Espécie": nome_comum, "Nome Científico": nome_cientifico, "N_Amostra": n_amostra,
                                "Fator_Compensacao": compensacao_fator, "N_Estimado": N_Estimado, "Mudas_Compensacao": Mudas_Compensacao
                            })

                    # Salvar
                    st.session_state.resultados = {
                        "stats": {
                            "media": media, "var": variancia, "dp": desvio, "cv": cv, "var_media": var_media,
                            "ep": erro_padrao, "t": t_val, "ea": ea, "er": er, "ic_inf": ic_inf, "ic_sup": ic_sup,
                            "tot_vol": total_vol, "tot_ea": total_ea, "tot_ic_inf": total_ic_inf, "tot_ic_sup": total_ic_sup,
                            "n": n, "N": N, "area_total": area_total_ha, "area_amostrada": Area_Amostrada_ha,
                            "top_sp": top_sp, "top_fam": top_fam
                        },
                        "compensacao_df": pd.DataFrame(compensacao_list)
                    }
                    
                    st.toast("Cálculo realizado! Redirecionando...", icon="✅")
                    
                    # AUTO-NAVEGAÇÃO
                    components.html("""<script> const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]'); if (tabs.length >= 3) { tabs[2].click(); } </script>""", height=0, width=0)

            except ValueError as ve:
                st.error(f"Erro de Cálculo Crítico: {ve}")
                st.info("Verifique se as colunas de DAP/CAP e Altura possuem dados numéricos válidos e se os valores de área não são zero.")
            except Exception as e:
                st.error(f"Erro inesperado durante o processamento: {e}")

# ==============================================================================
# ABA 3: RELATÓRIO TÉCNICO
# ==============================================================================
with tab3:
    if st.session_state.resultados is None:
        st.warning("👈 Realize o cálculo na Aba 2 para gerar o relatório.")
        st.button("🧹 Reiniciar Cálculos", disabled=True) 
    else:
        res = st.session_state.resultados["stats"]
        df_comp = st.session_state.resultados["compensacao_df"]
        
        st.markdown("## 📋 Relatório Técnico de Inventário Florestal")
        st.markdown("---")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown("#### 📍 Dados da Área")
            st.write(f"**Área Total do Projeto:** {res['area_total']:.4f} ha")
            st.write(f"**Área Amostrada:** {res['area_amostrada']:.4f} ha ({res['n']} parcelas)")
            st.write(f"**Intensidade Amostral:** {(res['n'] / res['N'] * 100):.2f}%")

        with col_res2:
            st.markdown("#### 🌿 Destaques Florísticos")
            st.write(f"**Espécie mais comum:** {res['top_sp']}")
            st.write(f"**Família mais comum:** {res['top_fam']}")
            st.write("**Método:** Amostragem Casual Simples (ACS)")

        st.markdown("---")

        # --- DENTRO DA ABA 3 (Substituindo o bloco de compensação antigo) ---

      
        st.markdown("## 🌳 Validação de Compensação (Res. Semade n.9/2015)")
        
        # 1. Preparação dos dados
        df_amostra = st.session_state.df_final
        res_stats = st.session_state.resultados["stats"]
        fator_extrapolacao = res_stats["area_total"] / res_stats["area_amostrada"] if res_stats["area_amostrada"] > 0 else 0
        
        # Agrupar todas as espécies
        df_todas_sp = df_amostra.groupby(['Nome Comum', 'Nome Científico']).size().reset_index(name='N_Amostra')
        df_todas_sp['N_Populacao'] = (df_todas_sp['N_Amostra'] * fator_extrapolacao)
        
        # Identificação automática inicial
        def buscar_fator(row):
            nc = str(row['Nome Científico']).strip()
            np = str(row['Nome Comum']).strip()
            return PROTECTED_SPECIES_MS.get(nc, PROTECTED_SPECIES_MS.get(np, 0))
        
        df_todas_sp['Fator (x)'] = df_todas_sp.apply(buscar_fator, axis=1)
        
        # Interface de Alerta
        if (df_todas_sp['Fator (x)'] > 0).any():
            st.warning("⚠️ **ESPÉCIES PROTEGIDAS DETECTADAS:** Valide os valores na tabela abaixo e ajuste o Fator (x) se houver erros de digitação nos nomes.")
        else:
            st.info("💡 **VERIFICAÇÃO:** Nenhuma espécie protegida foi identificada automaticamente. Revise a lista abaixo para garantir que nenhum nome com erro de digitação passou despercebido.")
        
        # 2. TABELA COM AJUSTE AUTOMÁTICO E COLUNA DE MUDAS
        # O data_editor permite que o usuário altere o fator e veja o resultado na hora
        df_editavel = st.data_editor(
            df_todas_sp,
            column_config={
                "Nome Comum": st.column_config.TextColumn("Nome Popular", width="medium"),
                "Nome Científico": st.column_config.TextColumn("Nome Científico", width="large"),
                "N_Amostra": st.column_config.NumberColumn("N° Amostrado", format="%d"),
                "N_Populacao": st.column_config.NumberColumn("N° População", format="%.2f"),
                "Fator (x)": st.column_config.SelectboxColumn(
                    "Fator (x)",
                    options=[0, 5, 10],
                    help="Selecione o fator de compensação conforme a Resolução."
                )
            },
            disabled=["Nome Comum", "Nome Científico", "N_Amostra", "N_Populacao"],
            hide_index=True,
            use_container_width=True, # Ajuste automático de largura
            num_rows="dynamic"        # Evita barras de rolagem desnecessárias se a lista for pequena
        )
        
        # 3. CÁLCULO DAS MUDAS POR ESPÉCIE E TOTAL
        df_editavel['Mudas por Espécie'] = (np.ceil(df_editavel['N_Populacao']) * df_editavel['Fator (x)']).astype(int)
        
        # Exibição da coluna de mudas calculada na hora (logo abaixo ou via nova tabela)
        st.markdown("##### 📊 Resumo de Mudas por Espécie")
        st.dataframe(
            df_editavel[df_editavel['Fator (x)'] > 0][['Nome Comum', 'Fator (x)', 'Mudas por Espécie']],
            hide_index=True,
            use_container_width=True
        )
        
        total_geral = df_editavel['Mudas por Espécie'].sum()
        
        st.markdown("---")
        if total_geral > 0:
            st.success(f"### 🌱 TOTAL DE COMPENSAÇÃO: {total_geral:,} mudas".replace(",", "."))
        else:
            st.info("Nenhuma muda de compensação exigida.")


        # Diagnóstico e Tabela Oficial


        st.markdown("#### 🎯 Diagnóstico Estatístico")
        if res['er'] <= 20.0:
            st.success(f"**APROVADO:** Erro de amostragem de **{res['er']:.2f}%** (Lim: 20%).")
        else:
            st.error(f"**INSUFICIENTE:** Erro de amostragem de **{res['er']:.2f}%** (> 20%).")
            st.caption("Recomendação: Aumentar o número de parcelas.")

        st.markdown("#### 📊 Tabela de Análise Estatística")
        
        dados_tabela = [
            ["Média Aritmética", f"{res['media']:.4f} m³/ha", f"{res['tot_vol']:.4f} m³"],
            ["Variância", f"{res['var']:.4f}", "-"],
            ["Desvio Padrão", f"{res['dp']:.4f} m³/ha", "-"],
            ["Coeficiente de Variação", f"{res['cv']:.2f} %", "-"],
            ["Variância da Média", f"{res['var_media']:.4f}", "-"],
            ["Erro Padrão da Média", f"{res['ep']:.4f} m³/ha", "-"],
            ["Valor de t (Student)", f"{res['t']:.4f}", "-"],
            ["Erro de Amostragem (Absoluto)", f"± {res['ea']:.4f} m³/ha", f"± {res['tot_ea']:.4f} m³"],
            ["Erro de Amostragem (Relativo)", f"{res['er']:.2f} %", f"{res['er']:.2f} %"],
            ["Intervalo de Confiança (Mínimo)", f"{res['ic_inf']:.4f} m³/ha", f"{res['tot_ic_inf']:.4f} m³"],
            ["Intervalo de Confiança (Máximo)", f"{res['ic_sup']:.4f} m³/ha", f"{res['tot_ic_sup']:.4f} m³"]
        ]
        
        df_relatorio = pd.DataFrame(dados_tabela, columns=["Parâmetro Estatístico", "Estimativa por Hectare", "Estimativa Total"])
        st.table(df_relatorio)
        st.caption(f"População (N): {res['N']:.2f} | Graus de Liberdade: {res['n']-1}")
        
        # Downloads e Reset
        st.markdown("<br>", unsafe_allow_html=True)
        col_down, col_reset = st.columns([1, 1])

        csv_t = df_relatorio.to_csv(index=False).encode('utf-8')
        col_down.download_button("📥 Baixar Tabela (CSV)", csv_t, "Resultados_Inventario.csv", "text/csv")
        
        col_reset.button("🧹 Reiniciar Cálculos", type="secondary", on_click=reset_app_state)
