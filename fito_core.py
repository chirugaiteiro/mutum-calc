# fito_core.py
import pandas as pd
import numpy as np
from scipy.stats import t

class CalculadoraInventario:
    @staticmethod
    def calcular_volume(df, metodo, area_parcela_m2, ff=0.33, eq_str=""):
        """Calcula volume individual e por hectare."""
        df_calc = df.copy()
        
        # Garante numéricos e preenche nulos com 0
        cols = ['DAP', 'ALTURA', 'ALTURA_COMERCIAL']
        for c in cols:
            if c in df_calc.columns: 
                df_calc[c] = pd.to_numeric(df_calc[c], errors='coerce').fillna(0)

        # Seleciona altura (Comercial tem prioridade se existir e for > 0)
        col_h = 'ALTURA_COMERCIAL' if 'ALTURA_COMERCIAL' in df_calc.columns and df_calc['ALTURA_COMERCIAL'].sum() > 0 else 'ALTURA'
        
        # Volume Individual
        if metodo == "Fator de Forma":
            # V = g * h * f (DAP em cm -> dividir por 100 para m, g = pi*d²/4)
            # Simplificando: (pi * DAP² / 40000) * H * f
            df_calc['VOL_IND'] = (np.pi * (df_calc['DAP']**2) / 40000) * df_calc[col_h] * ff
        else:
            try:
                # Segurança no eval: define o dicionário de variáveis permitidas
                local_vars = {
                    "DAP": df_calc['DAP'], 
                    "ALTURA": df_calc[col_h], 
                    "CAP": df_calc['DAP'] * np.pi, 
                    "PI": np.pi, 
                    "np": np,
                    "log": np.log,
                    "exp": np.exp
                }
                # Avalia a equação string (ex: "0.00007 * DAP**2.5 * ALTURA")
                df_calc['VOL_IND'] = eval(eq_str, {"__builtins__": None}, local_vars)
            except:
                df_calc['VOL_IND'] = 0

        # Extrapolação por hectare (Fator de Proporcionalidade)
        fator_extrapolacao = 10000 / area_parcela_m2
        df_calc['VOL_HA'] = df_calc['VOL_IND'] * fator_extrapolacao
        
        return df_calc

    @staticmethod
    def estatistica_acs(df_processado, area_total_ha, area_parcela_m2):
        """Calcula estatística de Amostragem Casual Simples (ACS)."""
        # Agrupa volume por parcela
        df_parc = df_processado.groupby('PARCELA')['VOL_HA'].sum().reset_index()
        
        n = len(df_parc) # Número de parcelas amostradas
        if n < 2: return None, "Número de parcelas insuficiente (mínimo 2)."
        
        N = (area_total_ha * 10000) / area_parcela_m2 # População total (quantas parcelas cabem na área)
        
        media = df_parc['VOL_HA'].mean()
        variancia = df_parc['VOL_HA'].var(ddof=1)
        desvio_padrao = np.sqrt(variancia)
        
        # Coeficiente de Variação (%)
        cv = (desvio_padrao / media) * 100 if media > 0 else 0
        
        # Fator de Correção para População Finita (fpc)
        f = n / N
        fpc = 1 - f if (1 - f) > 0 else 0
        
        # Variância da Média e Erro Padrão
        var_media = (variancia / n) * fpc
        erro_padrao = np.sqrt(var_media)
        
        # t-Student (Bicaudal, 95% confiança)
        t_val = t.ppf(0.975, df=n-1)
        
        ea = t_val * erro_padrao # Erro de Amostragem Absoluto (m³/ha)
        er = (ea / media) * 100 if media > 0 else 0 # Erro de Amostragem Relativo (%)
        
        ic_min = media - ea
        ic_max = media + ea
        
        total_vol = media * area_total_ha
        total_ea = ea * area_total_ha
        total_ic_min = ic_min * area_total_ha
        total_ic_max = ic_max * area_total_ha
        
        return {
            "media": media, "cv": cv, "er": er, "ea": ea,
            "ic_min": ic_min, "ic_max": ic_max,
            "total_vol": total_vol, "total_ea": total_ea, 
            "total_ic_min": total_ic_min, "total_ic_max": total_ic_max,
            "n": n, "area_amostrada": n * area_parcela_m2 / 10000
        }, None

class CalculadoraFitosso:
    @staticmethod
    def processar(df, area_parcela_m2):
        """Gera a tabela fitossociológica completa e índices de diversidade."""
        df_fito = df.copy()
        
        # Garante numéricos
        df_fito['DAP'] = pd.to_numeric(df_fito['DAP'], errors='coerce').fillna(0)
        
        # Área Basal Individual (g) em m² = (pi * DAP² / 40000)
        df_fito['AB_m2'] = (np.pi * (df_fito['DAP']**2)) / 40000
        
        # Parâmetros Gerais
        n_parcelas_totais = df_fito['PARCELA'].nunique()
        area_amostrada_ha = (n_parcelas_totais * area_parcela_m2) / 10000
        
        # Agrupamento por Espécie (Nome Científico)
        if 'NOME_CIENTIFICO' not in df_fito.columns:
            # Fallback se não tiver científico, usa o comum ou cria "Indeterminado"
            df_fito['NOME_CIENTIFICO'] = df_fito.get('NOME_COMUM', 'Indeterminado')

        grupo = df_fito.groupby('NOME_CIENTIFICO').agg(
            N=('DAP', 'count'),           # Número de indivíduos (Abundância)
            AB_Total=('AB_m2', 'sum'),    # Dominância Absoluta (Soma das Áreas Basais)
            Ocorrencias=('PARCELA', 'nunique') # Frequência Absoluta (Em quantas parcelas ocorre)
        ).reset_index()
        
        # --- CÁLCULOS ESTRUTURAIS ---
        
        # 1. Densidades
        grupo['DA'] = grupo['N'] / area_amostrada_ha  # Indivíduos por ha
        densidade_total = grupo['DA'].sum()
        grupo['DR'] = (grupo['DA'] / densidade_total) * 100 if densidade_total > 0 else 0
        
        # 2. Dominâncias
        grupo['DoA'] = grupo['AB_Total'] / area_amostrada_ha # m² por ha
        dominancia_total = grupo['DoA'].sum()
        grupo['DoR'] = (grupo['DoA'] / dominancia_total) * 100 if dominancia_total > 0 else 0
        
        # 3. Frequências
        grupo['FA'] = (grupo['Ocorrencias'] / n_parcelas_totais) * 100
        frequencia_total = grupo['FA'].sum()
        grupo['FR'] = (grupo['FA'] / frequencia_total) * 100 if frequencia_total > 0 else 0
        
        # 4. IVI (Índice de Valor de Importância)
        grupo['IVI'] = grupo['DR'] + grupo['DoR'] + grupo['FR']
        
        # Ordenar por IVI decrescente
        tabela_ivi = grupo.sort_values('IVI', ascending=False).reset_index(drop=True)
        
        # --- ÍNDICES DE DIVERSIDADE ECOLÓGICA ---
        
        # Shannon-Wiener (H') = - sum(pi * ln(pi))
        # Onde pi = proporção de indivíduos da espécie i em relação ao total
        total_ind = tabela_ivi['N'].sum()
        
        if total_ind > 0:
            pi = tabela_ivi['N'] / total_ind
            ln_pi = np.log(pi)
            shannon = -np.sum(pi * ln_pi)
            
            # Simpson (D) = 1 - sum(pi²)
            simpson = 1 - np.sum(pi**2)
            
            # Pielou (J') = H' / ln(S) -> S = Riqueza (número de espécies)
            riqueza_s = len(tabela_ivi)
            pielou = shannon / np.log(riqueza_s) if riqueza_s > 1 else 0
        else:
            shannon, simpson, pielou, riqueza_s = 0, 0, 0, 0
        
        indices = {
            "H' (Shannon)": shannon,
            "J' (Pielou)": pielou,
            "D (Simpson)": simpson,
            "Riqueza (S)": riqueza_s,
            "Indivíduos (N)": total_ind,
            "Area Basal Total (G)": grupo['DoA'].sum()
        }
        
        return tabela_ivi, indices
