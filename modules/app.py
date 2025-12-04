import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

# Importando nossos módulos locais
import config
from modules import ingestor

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    page_icon="🛰️"
)

# --- ESTILIZAÇÃO CSS (Visual Siriema/Imasul) ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        h1 {color: #2E8B57;}
        div[data-testid="stMetricValue"] {font-size: 1.2rem;}
    </style>
""", unsafe_allow_html=True)

def main():
    st.title(f"{config.APP_TITLE} - Validação de Imóvel")
    st.markdown("---")

    # --- SEÇÃO 1: UPLOAD (O Input) ---
    col_up1, col_up2 = st.columns([1, 2])
    
    with col_up1:
        st.info("📂 **Carregar Arquivo do Projeto**")
        uploaded_file = st.file_uploader(
            "Arraste seu ZIP, SHP, KML ou GeoJSON",
            type=["zip", "kml", "shp", "geojson", "gpkg"]
        )
        
        # Selectbox decorativo (pois o ingestor força SIRGAS, mas visualmente conforta o usuário)
        st.selectbox("Projeção de Entrada (Detectada/Convertida)", ["SIRGAS 2000 (EPSG:4674) - Padrão"])

    # --- PROCESSAMENTO ---
    if uploaded_file is not None:
        # Usa session_state para não reprocessar toda hora que mexe no mapa
        if 'gdf_data' not in st.session_state or st.session_state.get('last_file') != uploaded_file.name:
            with st.spinner("🛰️ Processando geometria e identificando classes..."):
                gdf, error = ingestor.process_file(uploaded_file)
                
                if error:
                    st.error(f"Erro no processamento: {error}")
                    st.stop()
                else:
                    st.session_state['gdf_data'] = gdf
                    st.session_state['last_file'] = uploaded_file.name
                    st.toast("Arquivo processado com sucesso!", icon="✅")

        # Recupera dados da memória
        gdf = st.session_state['gdf_data']

        # --- SEÇÃO 2: TABELA RESUMO (Estilo Siriema) ---
        st.subheader("📋 Áreas do Imóvel (Conferência)")
        
        # Agrupa por Classe Oficial para somar as áreas
        resumo = gdf.groupby('label_oficial')['area_ha'].sum().reset_index()
        resumo = resumo.rename(columns={'label_oficial': 'Classe / Categoria', 'area_ha': 'Área Calculada (ha)'})
        
        # Adiciona linha de total
        total_area = resumo['Área Calculada (ha)'].sum()
        
        # Mostra tabela bonitinha
        st.dataframe(
            resumo.style.format({"Área Calculada (ha)": "{:.4f}"}),
            use_container_width=True,
            hide_index=True
        )
        
        # Métricas rápidas abaixo da tabela
        c1, c2, c3 = st.columns(3)
        c1.metric("Área Total Processada", f"{total_area:.4f} ha")
        c2.metric("Qtd. de Polígonos", len(gdf))
        c3.metric("CRS Utilizado", config.CRS_INTERNAL)

        st.markdown("---")

        # --- SEÇÃO 3: MAPA INTERATIVO ---
        st.subheader("🗺️ Visualização Espacial")
        
        # Criação do Mapa Folium
        # Centro inicial: pega o centroide da primeira geometria ou o padrão do config
        try:
            centroid = gdf.geometry.centroid.iloc[0]
            start_loc = [centroid.y, centroid.x]
        except:
            start_loc = [config.MAP_CENTER_LAT, config.MAP_CENTER_LON]

        m = folium.Map(location=start_loc, zoom_start=12, tiles=None) # Tiles=None para customizar

        # Adiciona Imagem de Satélite (Esri World Imagery)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satélite',
            overlay=False,
            control=True
        ).add_to(m)

        # Adiciona Mapa de Ruas (OpenStreetMap) como opção
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='Mapa de Ruas',
            overlay=False,
            control=True
        ).add_to(m)

        # Adiciona as camadas do GeoDataFrame
        # Iteramos sobre as classes encontradas para criar camadas separadas (LayerControl)
        for label in gdf['label_oficial'].unique():
            # Filtra o gdf apenas para essa classe
            subset = gdf[gdf['label_oficial'] == label]
            
            # Pega a cor dessa classe (baseado na primeira linha do subset)
            color = subset.iloc[0]['color']
            
            folium.GeoJson(
                subset,
                name=label,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color, # Borda
                    'weight': 2,
                    'fillOpacity': 0.6
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['label_oficial', 'area_ha'],
                    aliases=['Classe:', 'Área (ha):'],
                    localize=True
                )
            ).add_to(m)

        # Adiciona controle de camadas (Checkboxes)
        folium.LayerControl(collapsed=False).add_to(m)
        Fullscreen().add_to(m)

        # Renderiza no Streamlit
        st_folium(m, use_container_width=True, height=600)

if __name__ == "__main__":
    main()
