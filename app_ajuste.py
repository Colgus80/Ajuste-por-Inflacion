import streamlit as st
import pandas as pd
import numpy as np

# --- FUNCIÓN DE CONVERSIÓN DE FECHAS DE EXCEL ---
def limpiar_fechas_excel(df, nombre_columna):
    """
    Convierte números seriales de Excel (ej: 46082.0) a formato de fecha YYYY-MM.
    Ignora valores nulos o textos que no sean fechas.
    """
    # Convertimos a numérico, forzando a NaN lo que sea texto puro
    fechas_numericas = pd.to_numeric(df[nombre_columna], errors='coerce')
    
    # Convertimos el número serial a fecha real (origen de Excel en Windows)
    fechas_reales = pd.to_datetime(fechas_numericas, origin='1899-12-30', unit='D')
    
    # Formateamos a Año-Mes (ej. "2026-03") para que sea fácil de cruzar
    df["Periodo"] = fechas_reales.dt.strftime('%Y-%m')
    
    # Eliminamos filas donde no se pudo detectar un periodo válido
    return df.dropna(subset=["Periodo"])

# --- 1. CARGA Y LIMPIEZA DE TABLAS DE REFERENCIA ---
st.sidebar.header("1. Archivos de Referencia")
uploaded_file = st.sidebar.file_uploader("Subir Excel maestro (con INDICES y DOLAR)", type=["xls", "xlsx"])

if uploaded_file:
    try:
        # Carga cruda
        df_indices_raw = pd.read_excel(uploaded_file, sheet_name="INDICES")
        df_dolar_raw = pd.read_excel(uploaded_file, sheet_name="DOLAR DE REFERENCIA-BCRA")
        
        # Limpieza y formateo (Asumiendo que las fechas están en la primera columna)
        # Ajusta el nombre de la columna si en tu Excel se llama distinto
        col_fecha_indices = df_indices_raw.columns[0] 
        col_fecha_dolar = df_dolar_raw.columns[0]
        
        df_indices = limpiar_fechas_excel(df_indices_raw.copy(), col_fecha_indices)
        df_dolar = limpiar_fechas_excel(df_dolar_raw.copy(), col_fecha_dolar)
        
        # Asumiendo que el índice está en la 2da columna y la cotización en la 2da
        col_valor_indice = df_indices.columns[1]
        col_valor_dolar = df_dolar.columns[1]
        
        st.sidebar.success("Tablas procesadas. Fechas seriales convertidas a YYYY-MM.")
        
    except Exception as e:
        st.sidebar.error(f"Error al procesar: {e}")
        st.stop()
else:
    st.info("Sube tu archivo de Excel en la barra lateral para continuar.")
    st.stop()

# --- 2. ENTRADA DE DATOS PARA EL CÁLCULO ---
st.header("Cálculo de Ajuste")

# Generamos una lista de periodos disponibles basada en la tabla de índices
periodos_disponibles = sorted(df_indices["Periodo"].unique().tolist(), reverse=True)

col1, col2 = st.columns(2)
with col1:
    periodo_actualizacion = st.selectbox("Mes de Actualización (Cierre F.3064):", periodos_disponibles)
with col2:
    periodo_ventas = st.selectbox("Mes de la Venta a registrar:", periodos_disponibles)

col_local, col_usd = st.columns(2)
with col_local:
    ventas_locales = st.number_input("Ventas Locales (ARS):", min_value=0.0)
with col_usd:
    ventas_usd = st.number_input("Ventas Exportación (USD):", min_value=0.0)

# --- 3. MOTOR DE BÚSQUEDA Y CÁLCULO ---
if st.button("Calcular Ajuste para este Mes", type="primary"):
    
    # 1. Buscar Índice base (del mes de la venta) y de actualización
    try:
        indice_base = df_indices.loc[df_indices["Periodo"] == periodo_ventas, col_valor_indice].values[0]
        indice_actualizacion = df_indices.loc[df_indices["Periodo"] == periodo_actualizacion, col_valor_indice].values[0]
        coeficiente = indice_actualizacion / indice_base
    except IndexError:
        st.error("No se encontró el índice IPIM para los periodos seleccionados.")
        st.stop()

    # 2. Buscar Dólar BCRA del mes de la venta
    try:
        cotizacion_dolar = df_dolar.loc[df_dolar["Periodo"] == periodo_ventas, col_valor_dolar].values[0]
    except IndexError:
        st.warning("No se encontró cotización para ese mes, se asume 0.")
        cotizacion_dolar = 0.0

    # 3. Cálculos matemáticos
    ventas_pesificadas = ventas_usd * cotizacion_dolar
    total_historico = ventas_locales + ventas_pesificadas
    total_reexpresado = total_historico * coeficiente

    # 4. Mostrar Resultados
    st.subheader("Resultados del Cruce de Datos")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Coeficiente de Ajuste", f"{coeficiente:.4f}")
    col_res2.metric("Cotización BCRA (Mes Venta)", f"$ {cotizacion_dolar:,.2f}")
    col_res3.metric("Ventas USD Pesificadas", f"$ {ventas_pesificadas:,.2f}")
    
    st.success(f"**Total Histórico:** $ {total_historico:,.2f}  |  **Total Reexpresado:** $ {total_reexpresado:,.2f}")
