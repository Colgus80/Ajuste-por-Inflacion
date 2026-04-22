import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ajuste por Inflación y Estacionalidad", layout="wide")

st.title("📊 Análisis de Ventas: Ajuste por Inflación y Estacionalidad")
st.markdown("Esta aplicación permite reexpresar ventas históricas a moneda homogénea, pesificando automáticamente las exportaciones en USD según el BCRA y ajustando por el índice IPIM.")

# --- 1. CARGA DE TABLAS DE REFERENCIA ---
@st.cache_data
def cargar_tablas_referencia():
    ruta_archivo = "data/indices_maestro.xlsx" 
    
    df_indices = pd.read_excel(
        ruta_archivo, 
        sheet_name="INDICES", 
        skiprows=5, 
        usecols="A:B",
        names=["Fecha", "Indice"]
    ).dropna()

    df_dolar = pd.read_excel(
        ruta_archivo, 
        sheet_name="DOLAR DE REFERENCIA-BCRA", 
        usecols="A:B",
        names=["Fecha", "Cotizacion"]
    ).dropna()
    
    # Llevamos las fechas al formato MM/YYYY para que coincida con la visualización
    df_indices["Periodo"] = pd.to_datetime(df_indices["Fecha"]).dt.strftime('%m/%Y')
    df_dolar["Periodo"] = pd.to_datetime(df_dolar["Fecha"]).dt.strftime('%m/%Y')
    
    return df_indices, df_dolar

try:
    df_indices, df_dolar = cargar_tablas_referencia()
    st.sidebar.success("✅ Base de datos cargada correctamente.")
except FileNotFoundError:
    st.error("❌ No se encontró el archivo 'indices_maestro.xlsx' en la carpeta 'data/'.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error al leer la base de datos: {e}")
    st.stop()

periodos_disponibles = sorted(df_indices["Periodo"].unique().tolist(), reverse=True)

# --- 2. DATOS DE LOS ÚLTIMOS EE.CC. ---
st.header("1. Datos del Ejercicio (EE.CC.)")

col1, col2, col3 = st.columns(3)

with col1:
    fecha_eecc = st.date_input(
        "Fecha Últimos EE.CC.:", 
        value=datetime(2025, 6, 30), 
        format="DD/MM/YYYY" 
    )

with col2:
    facturacion_eecc = st.number_input(
        "Facturación EE.CC.:", 
        min_value=0, 
        value=0, 
        step=1000, 
        format="%d"
    )

with col3:
    meses_ejercicio = st.number_input(
        "Meses del Ejercicio:", 
        min_value=1, 
        value=12, 
        step=1
    )

# --- 3. PARÁMETROS DE REEXPRESIÓN ---
st.subheader("Parámetros de Reexpresión")

# Buscamos el último mes disponible en los índices como valor por defecto
try:
    ultimo_mes_str = periodos_disponibles[0] # Ej: "03/2026"
    ultimo_mes_dt = datetime.strptime(ultimo_mes_str, "%m/%Y")
    # Lo llevamos al final del mes para que se vea correcto en el date_input
    ultimo_mes_dt = ultimo_mes_dt + pd.offsets.MonthEnd(0)
except:
    ultimo_mes_dt = datetime.today()

fecha_reexpresion = st.date_input(
    "Fecha a la cual se requiere reexpresar:", 
    value=ultimo_mes_dt,
    format="DD/MM/YYYY" 
)

st.markdown("---")

# --- 4. GENERACIÓN DINÁMICA DE MESES POST CIERRE ---
st.header("2. Facturación Post Cierre")

# Convertimos a Timestamp de Pandas para poder operar fácilmente
fecha_eecc_ts = pd.to_datetime(fecha_eecc)
fecha_actual_ts = pd.to_datetime(datetime.today())

mes_inicio_post_cierre = fecha_eecc_ts + pd.DateOffset(months=1)

if mes_inicio_post_cierre <= fecha_actual_ts:
    # Genera una lista de meses desde el cierre hasta hoy
    rango_meses = pd.date_range(
        start=mes_inicio_post_cierre.replace(day=1), 
        end=fecha_actual_ts.replace(day=1), 
        freq='MS'
    )
    
    # Inicializamos o actualizamos la tabla en session_state si cambia el rango
    if "df_post_cierre" not in st.session_state or len(st.session_state.df_post_cierre) != len(rango_meses):
        st.session_state.df_post_cierre = pd.DataFrame({
            "Periodo": [mes.strftime('%m/%Y') for mes in rango_meses],
            "Local ($)": [0] * len(rango_meses),
            "Externo ($)": [0] * len(rango_meses),
            "Externo (USD)": [0.0] * len(rango_meses)
        })
    
    st.write("Complete la facturación para los meses habilitados:")
    
    df_editado = st.data_editor(
        st.session_state.df_post_cierre,
        column_config={
            "Periodo": st.column_config.TextColumn("Periodo", disabled=True),
            "Local ($)": st.column_config.NumberColumn("Local ($)", min_value=0, step=1, format="%d"),
            "Externo ($)": st.column_config.NumberColumn("Externo ($)", min_value=0, step=1, format="%d"),
            "Externo (USD)": st.column_config.NumberColumn("Externo (USD)", min_value=0.0, format="USD %.2f")
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("La fecha de los últimos EE.CC. es reciente. No hay meses post cierre para habilitar.")
    df_editado = pd.DataFrame()


# --- 5. MOTOR DE CÁLCULO Y RESUMEN ---
st.markdown("---")
st.header("3. Resumen Información Reexpresada en Moneda Homogénea")

if st.button("Calcular Promedios y Variación", type="primary"):
    
    periodo_reexp_str = fecha_reexpresion.strftime('%m/%Y')
    periodo_eecc_str = fecha_eecc.strftime('%m/%Y')
    
    with st.spinner("Procesando índices..."):
        # 1. Reexpresión de EE.CC.
        try:
            indice_actualizacion = df_indices.loc[df_indices["Periodo"] == periodo_reexp_str, "Indice"].values[0]
            indice_eecc = df_indices.loc[df_indices["Periodo"] == periodo_eecc_str, "Indice"].values[0]
            coef_eecc = indice_actualizacion / indice_eecc
        except IndexError:
            st.error(f"No se encontró índice IPIM para las fechas seleccionadas ({periodo_eecc_str} o {periodo_reexp_str}).")
            st.stop()
            
        promedio_mensual_eecc_historico = facturacion_eecc / meses_ejercicio if meses_ejercicio > 0 else 0
        promedio_mensual_eecc_reexpresado = promedio_mensual_eecc_historico * coef_eecc
        
        # 2. Reexpresión Post Cierre
        total_post_cierre_reexpresado = 0
        cantidad_meses_post = 0
        resultados_post = []

        if not df_editado.empty:
            for index, row in df_editado.iterrows():
                mes_venta = row["Periodo"]
                
                try:
                    indice_base = df_indices.loc[df_indices["Periodo"] == mes_venta, "Indice"].values[0]
                    coeficiente = indice_actualizacion / indice_base
                except IndexError:
                    coeficiente = 1.0 
                    
                try:
                    cotizacion_dolar = df_dolar.loc[df_dolar["Periodo"] == mes_venta, "Cotizacion"].values[0]
                except IndexError:
                    cotizacion_dolar = 0.0 
                    
                ventas_usd_pesificadas = row["Externo (USD)"] * cotizacion_dolar
                total_historico = row["Local ($)"] + row["Externo ($)"] + ventas_usd_pesificadas
                reexpresado = total_historico * coeficiente
                
                total_post_cierre_reexpresado += reexpresado
                cantidad_meses_post += 1
                
                resultados_post.append({
                    "Periodo": mes_venta,
                    "Histórico ($)": total_historico,
                    "Coeficiente": coeficiente,
                    "Reexpresado ($)": reexpresado
                })

        promedio_post_cierre_reexpresado = total_post_cierre_reexpresado / cantidad_meses_post if cantidad_meses_post > 0 else 0
        
        # 3. Variación
        variacion = 0
        if promedio_mensual_eecc_reexpresado > 0:
            variacion = ((promedio_post_cierre_reexpresado / promedio_mensual_eecc_reexpresado) - 1) * 100

        # Función para aplicar formato argentino
        def formato_arg(numero):
            return f"{numero:,.0f}".replace(",", ".")

        # 4. Visualización de Métricas
        col_r1, col_r2, col_r3 = st.columns(3)
        
        col_r1.metric(
            label="Promedio Mensual EE.CC.", 
            value=f"$ {formato_arg(promedio_mensual_eecc_reexpresado)}"
        )
        col_r2.metric(
            label="Promedio Mensual Post Cierre", 
            value=f"$ {formato_arg(promedio_post_cierre_reexpresado)}"
        )
        col_r3.metric(
            label="Variación (%)", 
            value=f"{formato_arg(variacion)} %"
        )
        
        if resultados_post:
            st.subheader("Detalle Post Cierre Reexpresado")
            
            # Formateamos el DataFrame antes de mostrarlo
            df_mostrar = pd.DataFrame(resultados_post)
            # Aplicamos una función lambda para que los montos se vean con puntos en los miles
            df_mostrar["Histórico ($)"] = df_mostrar["Histórico ($)"].apply(lambda x: f"$ {formato_arg(x)}")
            df_mostrar["Reexpresado ($)"] = df_mostrar["Reexpresado ($)"].apply(lambda x: f"$ {formato_arg(x)}")
            df_mostrar["Coeficiente"] = df_mostrar["Coeficiente"].apply(lambda x: f"{x:.4f}")
            
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
