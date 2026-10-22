import streamlit as st

# 1. Configuración de la página (Título de la pestaña del navegador e ícono)
st.set_page_config(
    page_title="Inicio - EcoBici Analytics",
    page_icon="🚲",
    layout="wide"
)

# 2. Título principal
st.title("Sistema Analítico EcoBici Buenos Aires")
st.markdown("### Proyecto de infraestructura de datos para la red de bicicletas públicas de la Ciudad de Buenos Aires")
st.markdown("---")

# 3. Resumen Ejecutivo
st.subheader("Sobre el proyecto")
st.write("""
Bienvenido al sistema de análisis de la red de bicicletas públicas de la Ciudad de Buenos Aires. 
Esta aplicación consume datos en tiempo real y los procesa a través de una arquitectura de datos moderna (Data Pipeline) para ofrecer información accionable sobre la disponibilidad, ocupación y distribución de la flota.
""")

# 4. Arquitectura del Pipeline (Muy valorado en el ámbito académico)
st.markdown("### Arquitectura de los Datos")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info("**1. Ingesta**\n\nExtracción desde la API de CityBikes.")
with col2:
    st.info("**2. Almacenamiento**\n\nBase de datos relacional (PostgreSQL).")
with col3:
    st.info("**3. Modelado (Capa Gold)**\n\nData Warehouse con esquema estrella (Star Schema).")
with col4:
    st.info("**4. Consumo**\n\nVisualización interactiva con Streamlit y Plotly.")

st.markdown("---")


# 6. Tecnologías utilizadas (A los profes les encanta esto)
st.markdown("### Stack Tecnológico")
st.code("Python | Pandas | SQLAlchemy | PostgreSQL | Plotly | Streamlit | Docker", language="bash")
