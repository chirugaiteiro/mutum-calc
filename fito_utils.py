# fito_utils.py
import pandas as pd
import numpy as np
import difflib
import streamlit as st
from fito_config import (
    LISTA_IMASUL_COMPENSACAO, 
    URL_LISTA_MMA_CSV,
    LIMITES_BIOMETRICOS, 
    SINONIMOS_COLUNAS
)

# --- FUNÇÕES DE CARGA DE DADOS (CACHEADA) ---

@st.cache_data(ttl=3600) # Cache por 1 hora para não travar a cada recálculo
def carregar_lista_mma_csv(url):
    """
    Baixa e processa o CSV da Lista Vermelha do GitHub.
    Retorna um dicionário otimizado: {'NOME CIENTIFICO': 'CATEGORIA (CR/EN/VU)'}
    """
    try:
        # Lê o CSV (delimitador ; conforme seu arquivo)
        df = pd.read_csv(url, sep=';', encoding='utf-8', on_bad_lines='skip')
        
        # Mapeia as colunas baseadas no seu arquivo flora-ameacada-2021.csv
        # Colunas esperadas: 'Espécie (FB 2020)' e 'Sugestão de Categoria 2021'
        if 'Espécie (FB 2020)' not in df.columns:
            return {}

        # Limpeza básica
        df = df[['Espécie (FB 2020)', 'Sugestão de Categoria 2021']].dropna()
        df['Espécie (FB 2020)'] = df['Espécie (FB 2020)'].str.strip().str.upper()
        
        # Cria o dicionário {ESPECIE: CATEGORIA}
        return pd.Series(
            df['Sugestão de Categoria 2021'].values, 
            index=df['Espécie (FB 2020)']
        ).to_dict()
        
    except Exception as e:
        # Em caso de erro (sem internet, link quebrado), retorna vazio e loga silenciosamente
        print(f"Erro ao carregar lista MMA: {e}")
        return {}

# --- FUNÇÕES DE PADRONIZAÇÃO E AUDITORIA ---

def padronizar_colunas(df):
    """Renomeia as colunas do DataFrame para o padrão interno."""
    df.columns = df.columns.str.strip().str.upper()
    mapa_renomeacao = {}
    for col_padrao, variacoes in SINONIMOS_COLUNAS.items():
        for col_df in df.columns:
            if any(var in col_df for var in variacoes):
                if col_df not in mapa_renomeacao.values():
                    mapa_renomeacao[col_df] = col_padrao
    return df.rename(columns=mapa_renomeacao)

def verificar_taxonomia(nome_cientifico_input, nome_comum_input, dict_mma):
    """
    Cruza o nome com as listas (IMASUL e MMA carregada do CSV).
    """
    resultado = {
        "status_imasul": False, "fator_comp": 0, 
        "status_mma": False, "categoria_mma": None,
        "sugestao_nome": None, "similaridade": 0.0
    }
    
    nome_buscado = str(nome_cientifico_input).strip().upper()
    nome_comum_buscado = str(nome_comum_input).strip().upper()
    
    # 1. Verifica Lista MMA (Usando o dicionário carregado do CSV)
    if dict_mma:
        if nome_buscado in dict_mma:
            resultado["status_mma"] = True
            resultado["categoria_mma"] = dict_mma[nome_buscado]
        else:
            # Fuzzy match apenas se o dicionário não for vazio
            match = difflib.get_close_matches(nome_buscado, dict_mma.keys(), n=1, cutoff=0.85)
            if match:
                resultado["status_mma"] = True
                resultado["categoria_mma"] = dict_mma[match[0]]
                resultado["sugestao_nome"] = match[0]
                resultado["similaridade"] = difflib.SequenceMatcher(None, nome_buscado, match[0]).ratio()

    # 2. Verifica Lista IMASUL (Mantida igual)
    if nome_buscado in LISTA_IMASUL_COMPENSACAO:
        resultado["status_imasul"] = True
        resultado["fator_comp"] = LISTA_IMASUL_COMPENSACAO[nome_buscado]
    elif nome_comum_buscado in LISTA_IMASUL_COMPENSACAO:
        resultado["status_imasul"] = True
        resultado["fator_comp"] = LISTA_IMASUL_COMPENSACAO[nome_comum_buscado]
    
    return resultado

def auditoria_dados(df):
    """Pente Fino nos dados importados."""
    logs = []
    
    # Carrega a lista do MMA uma única vez antes de iterar
    dict_mma = carregar_lista_mma_csv(URL_LISTA_MMA_CSV)
    
    # Converte colunas numéricas
    cols_check = ['DAP', 'ALTURA', 'ALTURA_COMERCIAL']
    for col in cols_check:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    for idx, row in df.iterrows():
        parcela = row.get('PARCELA', '-')
        dap = row.get('DAP', 0)
        cap = row.get('CAP', 0)
        ht = row.get('ALTURA', 0)
        
        # Conversão CAP -> DAP
        if dap == 0 and cap > 0:
            dap = cap / np.pi
            
        # 1. Checagem Biométrica
        if dap > LIMITES_BIOMETRICOS['DAP_MAX_CM']:
            logs.append({"Linha": idx+2, "Parcela": parcela, "Erro": "DAP Suspeito (Muito Alto)", "Valor": f"{dap:.1f} cm", "Tipo": "Alerta ⚠️"})
        
        if ht > LIMITES_BIOMETRICOS['ALTURA_MAX_M']:
            logs.append({"Linha": idx+2, "Parcela": parcela, "Erro": "Altura Suspeita (Gigante)", "Valor": f"{ht:.1f} m", "Tipo": "Alerta ⚠️"})
            
        if ht > 0 and dap > 0:
            esbeltez = ht / (dap / 100)
            if esbeltez > 250:
                 logs.append({"Linha": idx+2, "Parcela": parcela, "Erro": "Árvore 'Agulha' (Erro Escala)", "Valor": f"Rel: {esbeltez:.1f}", "Tipo": "Erro ❌"})
            if esbeltez < 20:
                 logs.append({"Linha": idx+2, "Parcela": parcela, "Erro": "Árvore 'Panqueca' (DAP > Altura?)", "Valor": f"Rel: {esbeltez:.1f}", "Tipo": "Erro ❌"})

        # 2. Checagem Taxonômica (Passando o dict_mma)
        nome_cient = row.get('NOME_CIENTIFICO', '')
        nome_comum = row.get('NOME_COMUM', '')
        
        # Só verifica se tem nome científico preenchido (não gasta processamento com vazios)
        if nome_cient or nome_comum:
            res_tax = verificar_taxonomia(nome_cient, nome_comum, dict_mma)
            
            if res_tax['status_mma']:
                msg = f"Ameaçada MMA: {res_tax['categoria_mma']}"
                if res_tax['sugestao_nome']:
                    msg += f" (Digitado: {nome_cient} -> Sugerido: {res_tax['sugestao_nome']})"
                logs.append({"Linha": idx+2, "Parcela": parcela, "Erro": msg, "Valor": nome_cient, "Tipo": "CRÍTICO 🚨"})
            
    return pd.DataFrame(logs)
