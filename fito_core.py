# fito_core.py
import pandas as pd
import numpy as np
from scipy.stats import t

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

        # Seleciona altura (Comercial tem prioridade se existir e for > 0)
        col_h = 'ALTURA_COMERCIAL' if 'ALTURA_COMERCIAL' in df_calc.columns and df_calc['ALTURA_COMERCIAL'].sum() > 0 else 'ALTURA'
        
        # Volume Individual
        if metodo == "Fator de Forma":
            # V = g * h * f
            df_calc['VOL_IND'] = (np.pi * (df_calc['DAP']**2) / 40000) * df_calc[col_h] * ff
        else:
            try:
                # Segurança no eval
                local_vars = {
                    "DAP": df_calc['DAP'], "ALTURA": df_calc[col_h], 
                    "CAP": df_calc['DAP'] * np.pi, "PI": np.pi, "np": np
                }
                df_calc['VOL_IND'] = eval(eq_str, {"__builtins__": None}, local_vars)
            except:
                df_calc['VOL_IND'] = 0

        # Extrapolação por hectare
        fator_extrapolacao = 10000 / area_parcela_m2
        df_calc['VOL_HA'] = df_calc['VOL_IND'] * fator_extrapolacao
        
        return df_calc

    @staticmethod
    def estatistica_acs(df_processado, area_total_ha, area_parcela_m2):
        """Calcula estatística de Amostragem Casual Simples."""
        # Agrupa por parcela
        df_parc = df_processado.groupby('PARCELA')['VOL_HA'].sum().reset_index()
        
        n = len(df_parc) # Número de parcelas
        if n < 2: return None, "Número de parcelas insuficiente (n < 2)."
        
        N = (area_total_ha * 10000) / area_parcela_m2 # População total de parcelas cabíveis
        
        media = df_parc['VOL_HA'].mean()
        variancia = df_parc['VOL_HA'].var(ddof=1)
        desvio_padrao = np.sqrt(variancia)
        cv = (desvio_padrao / media) * 100 if media > 0 else 0
        
        # Fator de Correção para População Finita
        f = n / N
        fpc = 1 - f if (1 - f) > 0 else 0
        
        var_media = (variancia / n) * fpc
        erro_padrao = np.sqrt(var_media)
        
        # t-Student (95%)
        t_val = t.ppf(0.975, df=n-1)
        
        ea = t_val * erro_padrao # Erro Absoluto
        er = (ea / media) * 100 if media > 0 else 0 # Erro Relativo
        
        ic_min = media - ea
        ic_max = media + ea
        
        total_vol = media * area_total_ha
        
        return {
            "media": media, "cv": cv, "er": er, "ea": ea,
            "ic_min": ic_min, "ic_max": ic_max,
            "total_vol": total_vol, "n": n, "area_amostrada": n * area_parcela_m2 / 10000
        }, None

class CalculadoraFitosso:
    @staticmethod
    def processar(df, area_parcela_m2):
        """Gera a tabela fitossociológica completa (IVI, Shannon, Pielou)."""
        df_fito = df.copy()
        
        # Área Basal Individual (g) em m²
        # g = (pi * DAP^2) / 40000
        df_fito['AB_m2'] = (np.pi * (df_fito['DAP']**2)) / 40000
        
        # Parâmetros Gerais
        n_parcelas = df_fito['PARCELA'].nunique()
        area_amostrada_ha = (n_parcelas * area_parcela_m2) / 10000
        
        # Agrupamento por Espécie
        grupo = df_fito.groupby('NOME_CIENTIFICO').agg(
            N=('DAP', 'count'),           # Número de indivíduos
            AB_Total=('AB_m2', 'sum'),    # Dominância absoluta da espécie
            Ocorrencias=('PARCELA', 'nunique') # Em quantas parcelas ocorre
        ).reset_index()
        
        # --- CÁLCULOS ESTRUTURAIS ---
        
        # 1. Densidades
        # DA (Ind/ha)
        grupo['DA'] = grupo['N'] / area_amostrada_ha
        # DR (%)
        grupo['DR'] = (grupo['DA'] / grupo['DA'].sum()) * 100
        
        # 2. Dominâncias
        # DoA (m²/ha)
        grupo['DoA'] = grupo['AB_Total'] / area_amostrada_ha
        # DoR (%)
        grupo['DoR'] = (grupo['DoA'] / grupo['DoA'].sum()) * 100
        
        # 3. Frequências
        # FA (%) = (n_parcelas_ocorre / n_parcelas_totais) * 100
        grupo['FA'] = (grupo['Ocorrencias'] / n_parcelas) * 100
        # FR (%)
        grupo['FR'] = (grupo['FA'] / grupo['FA'].sum()) * 100
        
        # 4. IVI (Índice de Valor de Importância)
        grupo['IVI'] = grupo['DR'] + grupo['DoR'] + grupo['FR']
        
        # Ordenar por IVI
        tabela_ivi = grupo.sort_values('IVI', ascending=False).reset_index(drop=True)
        
        # --- ÍNDICES DE DIVERSIDADE ---
        
        # Shannon-Wiener (H') = - sum(pi * ln(pi))
        # pi = ni / N_total
        total_ind = tabela_ivi['N'].sum()
        pi = tabela_ivi['N'] / total_ind
        ln_pi = np.log(pi)
        shannon = -np.sum(pi * ln_pi)
        
        # Simpson (D) = 1 - sum(pi^2)
        simpson = 1 - np.sum(pi**2)
        
        # Pielou (J') = H' / ln(S) -> S = Riqueza (número de espécies)
        riqueza = len(tabela_ivi)
        pielou = shannon / np.log(riqueza) if riqueza > 1 else 0
        
        indices = {
            "H' (Shannon)": shannon,
            "J' (Pielou)": pielou,
            "D (Simpson)": simpson,
            "Riqueza (S)": riqueza,
            "Indivíduos (N)": total_ind
        }
        
        return tabela_ivi, indices
