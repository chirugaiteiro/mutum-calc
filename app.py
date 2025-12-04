import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

import config
from modules import ingestor

st.set_page_config(page_title=config.APP_TITLE, layout="wide", page_icon="🛰️")

# CSS para ficar parecido com o menu do Siriema
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h1 {color: #2E8B57; font-size: 1.5rem;}
        /* Estilo para simular o menu lateral do Siriema */
        .stCheckbox {background-color: #f0f2f6; padding: 5px; border-radius: 5px; margin-bottom: 5px;}
    </style>
""", unsafe_allow_html=True)

def main():
    # --- HEADER ---
    st.title(f"{config.APP_TITLE} - Validação Ambiental")

    # --- UPLOAD INICIAL ---
    # Se não tiver arquivo, mostra upload na tela cheia. Se tiver, move para sidebar ou topo.
    if 'gdf_data' not in st.session_state:
        st.info("📂 Carregue o arquivo ZIP do projeto (Shapes)")
        uploaded_file = st.file_uploader("", type=["zip", "kml", "shp", "geojson"])
        
        if uploaded_file:
            with st.spinner("Processando..."):
                gdf, error = ingestor.process_file(uploaded_file)
                if error:
                    st.error(error)
                else:
                    st.session_state['gdf_data'] = gdf
                    st.session_state['file_name'] = uploaded_file.name
                    st.rerun() # Recarrega a página para montar o layout novo
        st.stop() # Para a execução aqui até ter arquivo

    # --- LAYOUT PRINCIPAL (SIRIEMA STYLE) ---
    # Coluna 1: Menu Lateral (Controles) | Coluna 2: Mapa
    col_menu, col_map = st.columns([1, 4])
    
    gdf = st.session_state['gdf_data']
    
    with col_menu:
        st.subheader("🛠️ Camadas")
        
        # 1. Seletor de Mapa Base (2008 / 2025)
        st.markdown("**Mapa Base**")
        basemap_name = st.selectbox(
            "Selecione a imagem:",
            options=list(config.BASEMAPS.keys()),
            label_visibility="collapsed"
        )
        
        st.divider()

        # 2. Controle de Camadas (TOC)
        st.markdown("**Visibilidade**")
        
        # Pega todas as classes presentes no arquivo
        available_labels = sorted(gdf['label_oficial'].unique())
        
        # Dicionário para guardar estado dos checkboxes
        layer_visibility = {}
        
        # Botão para limpar/selecionar tudo (opcional, simples aqui)
        if st.button("Desmarcar Todos", use_container_width=True):
             for label in available_labels:
                 st.session_state[f"check_{label}"] = False
        
        for label in available_labels:
            # Pega a cor do config para mostrar um "quadradinho" colorido ao lado do nome
            # (Truque usando HTML simples dentro do markdown do label não funciona bem no checkbox, 
            # então usamos a cor da borda do stCheckbox via CSS se quiséssemos avançar muito)
            
            # Default: True (visível)
            is_checked = st.checkbox(label, value=True, key=f"check_{label}")
            layer_visibility[label] = is_checked

        st.divider()
        
        # 3. Destaque (Cor Chapada)
        st.markdown("**Destacar Camada (Cor Sólida)**")
        highlight_layer = st.radio(
            "Clique para chapar a cor:",
            options=["Nenhuma"] + available_labels,
            index=0
        )
        
        # Botão para trocar arquivo
        st.divider()
        if st.button("🔄 Novo Arquivo"):
            del st.session_state['gdf_data']
            st.rerun()

    with col_map:
        # Prepara o mapa
        selected_basemap = config.BASEMAPS[basemap_name]
        
        # Centraliza
        try:
            centroid = gdf.geometry.centroid.iloc[0]
            start_loc = [centroid.y, centroid.x]
        except:
            start_loc = [config.MAP_CENTER_LAT, config.MAP_CENTER_LON]

        m = folium.Map(
            location=start_loc, 
            zoom_start=13, 
            tiles=selected_basemap["url"],
            attr=selected_basemap["attr"],
            name=selected_basemap["name"]
        )
        
        # Adiciona Geometrias
        for label, is_visible in layer_visibility.items():
            if not is_visible:
                continue
                
            subset = gdf[gdf['label_oficial'] == label]
            
            # Lógica da Cor Chapada (Highlight)
            # Se esta camada for a selecionada no Radio Button, opacidade = 1.0 (sólida)
            is_highlighted = (label == highlight_layer)
            
            folium.GeoJson(
                subset,
                name=label,
                style_function=lambda feature, hl=is_highlighted: {
                    'fillColor': feature['properties']['color'],
                    'color': feature['properties']['color'], # Borda da mesma cor
                    # Se destacado: Borda grossa e Opacidade total. Se não: Lê do config
                    'weight': 3 if hl else feature['properties'].get('weight', 1),
                    'fillOpacity': 1.0 if hl else feature['properties'].get('fillOpacity', 0.5),
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['label_oficial', 'area_ha'],
                    aliases=['Classe:', 'Área (ha):'],
                    localize=True
                )
            ).add_to(m)
        
        Fullscreen().add_to(m)

        # Renderiza mapa ocupando a altura toda disponível
        st_folium(m, use_container_width=True, height=750)

    # --- TABELA DE ÁREAS (EXPANDER NO FUNDO) ---
    with st.expander("📊 Ver Tabela de Áreas (Conferência)", expanded=True):
        resumo = gdf.groupby('label_oficial')['area_ha'].sum().reset_index()
        total = resumo['area_ha'].sum()
        st.dataframe(resumo, use_container_width=True)
        st.metric("Área Total", f"{total:.4f} ha")

if __name__ == "__main__":
    main()
