"""
Aplicación Analítica - Dashboard EcoBici BA.
Capa de consumo (Serving Layer) que expone los KPIs y el mapa
interactivo consumiendo directamente el modelo estrella de la capa Gold.
"""
import streamlit as st
import pandas as pd
import sqlalchemy
import plotly.express as px



# Configuración de página de Streamlit
st.set_page_config(
    page_title="Dashboard EcoBici BA - Capa Gold",
    page_icon="🚲",
    layout="wide"
)

# URI de conexión al contenedor Postgres mapeado en la red interna de Docker
DB_URI = "postgresql://admin:admin@data_warehouse:5432/InfraCienciaDatos"

@st.cache_data(ttl=60)
def get_gold_metrics():
    """Extrae las métricas unificadas haciendo un JOIN rápido del Star Schema."""
    engine = sqlalchemy.create_engine(DB_URI)
    query = """
        SELECT 
            f.fact_key,
            f.bikes_available,
            f.slots_available,
            f.occupancy_ratio,
            s.station_name,
            s.address,
            s.total_capacity,
            s.latitude,
            s.longitude,
            t.full_timestamp,
            t.hour,
            t.day_of_week,
            t.is_weekend
        FROM gold.fact_station_availability f
        JOIN gold.dim_station s ON f.station_id = s.station_id
        JOIN gold.dim_time t ON f.time_id = t.time_id
        ORDER BY t.full_timestamp DESC;
    """
    df = pd.read_sql(query, con=engine)
    if not df.empty:
        df["full_timestamp"] = pd.to_datetime(df["full_timestamp"])
    return df

# --- TÍTULO PRINCIPAL ---
st.title("Sistema Analítico EcoBici Buenos Aires")
st.markdown("### `Etapa Final: Consumo de la Capa Gold (Star Schema)`")
st.write("Visualización en tiempo real y tendencias del estado de disponibilidad de la red.")

# Carga de datos
with st.spinner("Conectando con el Data Warehouse (Esquema Gold)..."):
    df_gold = get_gold_metrics()

if df_gold.empty:
    st.warning("⚠️ No se encontraron snapshots de datos en la capa gold. Asegurate de que el DAG 'gold_ecobici' haya corrido en Airflow.")
else:
    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.header("Filtros de Análisis")
    filtro_dia = st.sidebar.multiselect(
        "Seleccionar Día de la Semana",
        options=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
        default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    )
    
    # Aplicar filtros
    df_filtrado = df_gold[df_gold["day_of_week"].isin(filtro_dia)]
    
    # Obtener el último snapshot para las métricas e indicadores actuales
    ultimo_timestamp = df_filtrado["full_timestamp"].max()
    df_actual = df_filtrado[df_filtrado["full_timestamp"] == ultimo_timestamp]

    # --- FILA 1: MÉTRICAS GENERALES EN SNAPSHOT ---
    st.markdown(f"#### Estado de la Red al: `{ultimo_timestamp}`")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="📍 Estaciones Activas", value=int(df_actual["station_name"].nunique()))
    with col2:
        st.metric(label="🚲 Bicicletas Disponibles", value=int(df_actual["bikes_available"].sum()))
    with col3:
        st.metric(label="🔒 Anclajes Libres", value=int(df_actual["slots_available"].sum()))
    with col4:
        ratio_promedio = df_actual["occupancy_ratio"].mean() * 100
        st.metric(label="📈 Ocupación Promedio", value=f"{ratio_promedio:.1f}%")

    st.markdown("---")

    # --- FILA 2: MAPA GEOGRÁFICO INTERACTIVO ---
    st.subheader("Distribución Espacial y Saturación de Estaciones")
    st.write("El tamaño y color de los puntos representan la capacidad total y la tasa de ocupación actual.")
    
    # Renombrar temporalmente columnas para que Streamlit o Plotly las mapeen sin problemas
    df_mapa = df_actual.copy()
    
    fig_mapa = px.scatter_mapbox(
        df_mapa,
        lat="latitude",
        lon="longitude",
        color="occupancy_ratio",
        size="total_capacity",
        color_continuous_scale=px.colors.cyclical.IceFire,
        size_max=15,
        zoom=11.5,
        mapbox_style="open-street-map",
        hover_name="station_name",
        hover_data={"address": True, "bikes_available": True, "slots_available": True, "latitude": False, "longitude": False},
        labels={"occupancy_ratio": "Ratio de Ocupación"}
    )
    fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_mapa, use_container_width=True)

    st.markdown("---")



    #Nuevos gráficos
    st.markdown("---")
    st.subheader("Estado General de las Estaciones (Snapshot Actual)")
    
    # Creamos categorías lógicas basadas en el ratio de ocupación
    def categorizar_estacion(row):
        if row['bikes_available'] <= 3: return '🔴 Vacías (Faltan bicis)'
        elif row['slots_available'] <= 3: return '🟠 Saturadas (Faltan anclajes)'
        else: return '🟢 Equilibradas'
        
    df_actual['estado'] = df_actual.apply(categorizar_estacion, axis=1)
    
    # Contamos cuántas estaciones hay en cada estado
    df_estado = df_actual['estado'].value_counts().reset_index()
    df_estado.columns = ['Estado', 'Cantidad']
    
    fig_dona = px.pie(
        df_estado, 
        values='Cantidad', 
        names='Estado', 
        hole=0.5, # Esto lo hace un gráfico de dona
        color='Estado',
        color_discrete_map={
            '🔴 Vacías (Faltan bicis)': '#EF553B', 
            '🟠 Saturadas (Faltan anclajes)': '#FFA15A', 
            '🟢 Equilibradas': '#00CC96'
        },
        title="Distribución de Estaciones por Estado Operativo"
    )
    st.plotly_chart(fig_dona, use_container_width=True)

    st.markdown("---")

    st.subheader("Mapa de Calor: Demanda por Día y Hora")
    st.write("Identificación de los picos de ocupación a lo largo de la semana.")
    
    # Pivotamos los datos para crear la matriz
    pivot_heatmap = df_filtrado.pivot_table(
        index='day_of_week', 
        columns='hour', 
        values='occupancy_ratio', 
        aggfunc='mean'
    )
    
    # Ordenar los días (opcional, para que empiece en Lunes)
    dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    pivot_heatmap = pivot_heatmap.reindex(dias_orden)

    fig_heatmap = px.imshow(
        pivot_heatmap,
        labels=dict(x="Hora del Día", y="Día de la Semana", color="Ocupación"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
        title="Matriz de Ocupación Promedio",
        zmin=0, # <--- Mínimo 0
        zmax=1  # <--- Máximo 1
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)



#Graficos nuevos

        # --- FILA 3: ANÁLISIS TEMPORAL (HORAS PICO) ---
    st.subheader("Tendencia de Ocupación por Hora")
    st.write("Evolución del porcentaje de ocupación promedio a lo largo del día.")
    
    # Agrupamos por hora y calculamos el promedio de ocupación
    df_hourly = df_filtrado.groupby("hour")["occupancy_ratio"].mean().reset_index()
    # Pasamos el ratio a porcentaje para que sea más legible
    df_hourly["occupancy_percent"] = df_hourly["occupancy_ratio"] * 100
    
    fig_lineas = px.line(
        df_hourly,
        x="hour",
        y="occupancy_percent",
        labels={"hour": "Hora del Día", "occupancy_percent": "Ocupación Promedio (%)"},
        title="Picos de Demanda: Ocupación Promedio por Hora",
        markers=True,
        color_discrete_sequence=["#EF553B"] # Color rojo para destacar
    )
    
    # Agregamos una línea horizontal en el 50% como referencia de "Equilibrio"
    fig_lineas.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Equilibrio (50%)")
    fig_lineas.update_yaxes(range=[0, 100]) 
    
    fig_lineas.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
    st.plotly_chart(fig_lineas, use_container_width=True)
   


#GRAFICO BARRIOS

    st.markdown("---")
    st.subheader("Barrios con mayor uso de bicicletas (Estaciones vacías)")
    st.write("Ranking de barrios donde hay menos disponibilidad (las bicicletas están en uso o requieren reposición urgente).")
    
    # Diccionario de barrios
    barrios_caba = [
        "Agronomía", "Almagro", "Balvanera", "Barracas", "Belgrano", "Boedo", "Caballito", 
        "Chacarita", "Coghlan", "Colegiales", "Constitución", "Flores", "Floresta", 
        "La Boca", "La Paternal", "Liniers", "Mataderos", "Monte Castro", "Monserrat", 
        "Nueva Pompeya", "Núñez", "Palermo", "Parque Avellaneda", "Parque Chacabuco", 
        "Parque Chas", "Parque Patricios", "Puerto Madero", "Recoleta", "Retiro", 
        "Saavedra", "San Cristóbal", "San Nicolás", "San Telmo", "Vélez Sársfield", 
        "Versalles", "Villa Crespo", "Villa del Parque", "Villa Devoto", "Villa General Mitre", 
        "Villa Lugano", "Villa Luro", "Villa Ortúzar", "Villa Pueyrredón", "Villa Real", 
        "Villa Riachuelo", "Villa Santa Rita", "Villa Urquiza"
    ]

    def asignar_barrio(texto):
        if not isinstance(texto, str): return "Otro"
        texto = texto.upper()
        for b in barrios_caba:
            if b.upper() in texto:
                return b
        if "RETIRO" in texto or "CENTRO" in texto: return "Retiro"
        if "PALERMO" in texto or "ITALIA" in texto: return "Palermo"
        if "CABILDO" in texto: return "Belgrano"
        return "No especificado"

    # Aplicamos la función usando el nombre de la estación y la dirección
    df_actual['barrio'] = df_actual.apply(lambda row: asignar_barrio(str(row['station_name']) + " " + str(row['address'])), axis=1)
    
    # Agrupamos y calculamos promedio
    df_barrios = df_actual.groupby('barrio')['occupancy_ratio'].mean().reset_index()
    df_barrios['ocupacion_pct'] = df_barrios['occupancy_ratio'] * 100
    
    # FILTRAMOS los que no tienen barrio asignado para que no ensucien el gráfico
    df_barrios = df_barrios[~df_barrios['barrio'].isin(['No especificado', 'Otro'])]
    
    # ORDENAMOS DE MENOR A MAYOR (Los más vacíos primero)
    df_barrios = df_barrios.sort_values('ocupacion_pct', ascending=True)

    # Gráfico
    fig_barrios = px.bar(
        df_barrios,
        x='barrio',
        y='ocupacion_pct',
        text='ocupacion_pct',
        color='ocupacion_pct',
        color_continuous_scale='Blues_r', # Usamos tonos azules (los más claros son los más vacíos)
        labels={'barrio': 'Barrio', 'ocupacion_pct': 'Ocupación Promedio (%)'},
        title="Barrios con menor disponibilidad de bicicletas (Top Demanda)"
    )
    fig_barrios.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_barrios.update_layout(coloraxis_showscale=False, xaxis_tickangle=-45, height=500)
    
    st.plotly_chart(fig_barrios, use_container_width=True)
    
    st.info("💡 **Interpretación para el negocio:** Las barras más bajas representan los barrios donde las estaciones están más vacías (menor porcentaje de ocupación). Estos son los puntos donde se debe priorizar el envío de camiones con bicicletas para abastecer la demanda.")