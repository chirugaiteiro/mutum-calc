# fito_core.py
import pandas as pd
import numpy as np
from scipy.stats import t
from fito_config import LISTA_IMASUL_COMPENSACAO

class CalculadoraInventario:
    @staticmethod
    def calcular_volume(df, metodo, area_parcela_m2, ff=0.33, eq_str=""):
        """Calcula volume individual e por hectare."""
        df_calc = df.copy()
        
        # Garante numéricos
        cols = ['DAP', 'ALTURA', 'ALTURA_COMERCIAL']
        for c in cols:
            if c in df_calc.columns: 
                df_calc[c] = pd.to_numeric(df_calc[c], errors='coerce').fillna(0)

        col_h = 'ALTURA_COMERCIAL' if 'ALTURA_COMERCIAL' in df_calc.columns and df_calc['ALTURA_COMERCIAL'].sum() > 0 else 'ALTURA'
        
        if metodo == "Fator de Forma":
            df_calc['VOL_IND'] = (np.pi * (df_calc['DAP']**2) / 40000) * df_calc[col_h] * ff
        else:
            try:
                local_vars = {"DAP": df_calc['DAP'], "ALTURA": df_calc[col_h], "CAP": df_calc['DAP'] * np.pi, "PI": np.pi, "np": np, "log": np.log, "exp": np.exp}
                df_calc['VOL_IND'] = eval(eq_str, {"__builtins__": None}, local_vars)
            except:
                df_calc['VOL_IND'] = 0

        fator_extrapolacao = 10000 / area_parcela_m2
        df_calc['VOL_HA'] = df_calc['VOL_IND'] * fator_extrapolacao
        
        return df_calc

    @staticmethod
    def calcular_compensacao(df, area_total_ha, area_amostrada_ha):
        """
        Calcula a compensação obrigatória (Res. 9/2015) baseada na extrapolação.
        Retorna DataFrame com as mudas a repor.
        """
        if 'NOME_CIENTIFICO' not in df.columns and 'NOME_COMUM' not in df.columns:
            return pd.DataFrame()
            
        # Prepara colunas de texto
        if 'NOME_CIENTIFICO' in df.columns: df['NOME_CIENTIFICO'] = df['NOME_CIENTIFICO'].astype(str).str.upper().str.strip()
        else: df['NOME_CIENTIFICO'] = ""
        
        if 'NOME_COMUM' in df.columns: df['NOME_COMUM'] = df['NOME_COMUM'].astype(str).str.upper().str.strip()
        else: df['NOME_COMUM'] = ""

        # Agrupa contagem na amostra
        df_contagem = df.groupby(['NOME_COMUM', 'NOME_CIENTIFICO']).size().reset_index(name='N_Amostra')
        
        compensacao_list = []
        fator_populacao = area_total_ha / area_amostrada_ha if area_amostrada_ha > 0 else 0
        
        for _, row in df_contagem.iterrows():
            nc = row['NOME_CIENTIFICO']
            ncom = row['NOME_COMUM']
            n_amostra = row['N_Amostra']
            
            # Busca fator na lista (pelo científico ou comum)
            fator = LISTA_IMASUL_COMPENSACAO.get(nc, LISTA_IMASUL_COMPENSACAO.get(ncom, 0))
            
            if fator > 0:
                n_estimado = n_amostra * fator_populacao
                mudas = np.ceil(n_estimado) * fator
                
                compensacao_list.append({
                    "Espécie": ncom if ncom else nc,
                    "Nome Científico": nc,
                    "N_Amostra": n_amostra,
                    "Fator_Compensacao": fator,
                    "N_Estimado": n_estimado,
                    "Mudas_Compensacao": int(mudas)
                })
                
        return pd.DataFrame(compensacao_list)

    @staticmethod
    def estatistica_acs(df_processado, area_total_ha, area_parcela_m2):
        """Calcula estatística ACS completa."""
        df_parc = df_processado.groupby('PARCELA')['VOL_HA'].sum().reset_index()
        
        n = len(df_parc)
        if n < 2: return None, "Número de parcelas insuficiente (mínimo 2)."
        
        N = (area_total_ha * 10000) / area_parcela_m2
        
        media = df_parc['VOL_HA'].mean()
        variancia = df_parc['VOL_HA'].var(ddof=1)
        desvio_padrao = np.sqrt(variancia)
        cv = (desvio_padrao / media) * 100 if media > 0 else 0
        
        f = n / N
        fpc = 1 - f if (1 - f) > 0 else 0
        var_media = (variancia / n) * fpc
        erro_padrao = np.sqrt(var_media)
        
        t_val = t.ppf(0.975, df=n-1)
        
        ea = t_val * erro_padrao
        er = (ea / media) * 100 if media > 0 else 0
        
        ic_min = media - ea
        ic_max = media + ea
        
        total_vol = media * area_total_ha
        total_ea = ea * area_total_ha
        total_ic_min = ic_min * area_total_ha
        total_ic_max = ic_max * area_total_ha
        
        # Dados Florísticos Básicos
        top_sp = "-"
        top_fam = "-"
        if 'NOME_COMUM' in df_processado.columns: 
             top_sp = df_processado['NOME_COMUM'].mode()[0] if not df_processado.empty else "-"
        if 'FAMILIA' in df_processado.columns:
             top_fam = df_processado['FAMILIA'].mode()[0] if not df_processado.empty else "-"

        return {
            "media": media, "var": variancia, "dp": desvio_padrao, "cv": cv, 
            "var_media": var_media, "ep": erro_padrao, "t": t_val,
            "ea": ea, "er": er, "ic_min": ic_min, "ic_max": ic_max,
            "total_vol": total_vol, "total_ea": total_ea, 
            "total_ic_min": total_ic_min, "total_ic_max": total_ic_max,
            "n": n, "N": N, 
            "area_total": area_total_ha, "area_amostrada": n * area_parcela_m2 / 10000,
            "top_sp": top_sp, "top_fam": top_fam
        }, None

class CalculadoraFitosso:
    @staticmethod
    def processar(df, area_parcela_m2):
        # (Mantido idêntico à versão anterior - Fitossociologia)
        df_fito = df.copy()
        df_fito['DAP'] = pd.to_numeric(df_fito['DAP'], errors='coerce').fillna(0)
        df_fito['AB_m2'] = (np.pi * (df_fito['DAP']**2)) / 40000
        n_parcelas_totais = df_fito['PARCELA'].nunique()
        area_amostrada_ha = (n_parcelas_totais * area_parcela_m2) / 10000
        
        if 'NOME_CIENTIFICO' not in df_fito.columns:
            df_fito['NOME_CIENTIFICO'] = df_fito.get('NOME_COMUM', 'Indeterminado')

        grupo = df_fito.groupby('NOME_CIENTIFICO').agg(
            N=('DAP', 'count'), AB_Total=('AB_m2', 'sum'), Ocorrencias=('PARCELA', 'nunique')
        ).reset_index()
        
        grupo['DA'] = grupo['N'] / area_amostrada_ha
        densidade_total = grupo['DA'].sum()
        grupo['DR'] = (grupo['DA'] / densidade_total) * 100 if densidade_total > 0 else 0
        grupo['DoA'] = grupo['AB_Total'] / area_amostrada_ha
        dominancia_total = grupo['DoA'].sum()
        grupo['DoR'] = (grupo['DoA'] / dominancia_total) * 100 if dominancia_total > 0 else 0
        grupo['FA'] = (grupo['Ocorrencias'] / n_parcelas_totais) * 100
        frequencia_total = grupo['FA'].sum()
        grupo['FR'] = (grupo['FA'] / frequencia_total) * 100 if frequencia_total > 0 else 0
        grupo['IVI'] = grupo['DR'] + grupo['DoR'] + grupo['FR']
        
        tabela_ivi = grupo.sort_values('IVI', ascending=False).reset_index(drop=True)
        
        total_ind = tabela_ivi['N'].sum()
        if total_ind > 0:
            pi = tabela_ivi['N'] / total_ind
            ln_pi = np.log(pi)
            shannon = -np.sum(pi * ln_pi)
            simpson = 1 - np.sum(pi**2)
            riqueza_s = len(tabela_ivi)
            pielou = shannon / np.log(riqueza_s) if riqueza_s > 1 else 0
        else:
            shannon, simpson, pielou, riqueza_s = 0, 0, 0, 0
        
        indices = {
            "H' (Shannon)": shannon, "J' (Pielou)": pielou, "D (Simpson)": simpson,
            "Riqueza (S)": riqueza_s, "Indivíduos (N)": total_ind, "Area Basal Total (G)": grupo['DoA'].sum()
        }
        return tabela_ivi, indices
