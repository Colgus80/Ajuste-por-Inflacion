import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ajuste por Inflación y Estacionalidad", layout="wide")

st.title("📊 Análisis de Ventas: Ajuste por Inflación y Estacionalidad")
st.markdown("Esta aplicación permite reexpresar ventas históricas a moneda homogénea, pesificando automáticamente las exportaciones en USD según el BCRA y ajustando por el índice IPIM.")

# --- 1. CARGA DE TABLAS DE REFERENCIA (Desde GitHub/Carpeta Local) ---
@st.cache_data
def cargar_tablas_referencia():
    # Ruta al archivo dentro de tu repositorio (asegúrate de respetar mayúsculas/minúsculas)
    ruta_archivo = "data/indices_maestro.xlsx" 
    
    # INDICES: Saltamos las 5 filas iniciales vacías/títulos y tomamos las columnas A y B
    df_indices = pd.read_excel(
        ruta_archivo, 
        sheet_name="INDICES", 
        skiprows=5, 
        usecols="A:B",
        names=["Fecha", "Indice"]
    ).dropna()

    # DOLAR BCRA: Leemos desde el principio y tomamos columnas A y B
    df_dolar = pd.read_excel(
        ruta_archivo, 
        sheet_name="DOLAR DE REFERENCIA-BCRA", 
        usecols="A:B",
        names=["Fecha", "Cotizacion"]
    ).dropna()
    
    # Convertimos las fechas al formato estandarizado YYYY-MM para facilitar los cruces
    df_indices["Periodo"] = pd.to_datetime(df_indices["Fecha"]).dt.strftime('%Y-%m')
    df_dolar["Periodo"] = pd.to_datetime(df_dolar["Fecha"]).dt.strftime('%Y-%m')
    
    return df_indices, df_dolar

# Intentamos cargar la base de datos
try:
    df_indices, df_dolar = cargar_tablas_referencia()
    st.sidebar.success("✅ Base de datos (Índices y Dólar) cargada correctamente.")
except FileNotFoundError:
    st.error("❌ No se encontró el archivo 'indices_maestro.xlsx' en la carpeta 'data/'.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error al leer la base de datos: {e}")
    st.stop()

# Lista de periodos (YYYY-MM) para los menús desplegables
periodos_disponibles = sorted(df_indices["Periodo"].unique().tolist(), reverse=True)


# --- 2. ENTRADA DE DATOS (EMPRESA Y PARÁMETROS) ---
st.header("1. Datos de la Empresa y Parámetros")

col1, col2, col3 = st.columns(3)
with col1:
    empresa = st.text_input("Nombre de la Empresa:")
with col2:
    filial = st.text_input("Filial:")
with col3:
    cuenta = st.text_input("Cuenta:")

st.markdown("---")

col_fecha_act, col_vacio = st.columns([1, 2])
with col_fecha_act:
    # Este es el mes "destino" al cual se llevará toda la plata
    periodo_actualizacion = st.selectbox("Mes de Actualización (Último mes F.3064):", periodos_disponibles)


# --- 3. CARGA DE FACTURACIÓN (MATRIZ INTERACTIVA) ---
st.header("2. Facturación Post Cierre")
st.write("Carga los meses a analizar. Selecciona el periodo y digita los montos. Las ventas en USD se pesificarán al cierre de su mes correspondiente.")

# Creamos un DataFrame vacío para que el usuario lo llene en la interfaz
num_filas = st.number_input("Cantidad de meses a cargar:", min_value=1, max_value=24, value=6)

if "df_ventas" not in st.session_state or len(st.session_state.df_ventas) != num_filas:
    st.session_state.df_ventas = pd.DataFrame({
        "Mes Venta (YYYY-MM)": [periodos_disponibles[0]] * num_filas,
        "Local (ARS)": [0.0] * num_filas,
        "Externo (ARS)": [0.0] * num_filas,
        "Externo (USD)": [0.0] * num_filas
    })

# Usamos st.data_editor con configuración de columnas para que el "Mes" sea un desplegable
edited_df = st.data_editor(
    st.session_state.df_ventas,
    column_config={
        "Mes Venta (YYYY-MM)": st.column_config.SelectboxColumn(
            "Mes Venta (YYYY-MM)",
            help="Selecciona el mes en el que se realizó la venta",
            options=periodos_disponibles,
            required=True
        ),
        "Local (ARS)": st.column_config.NumberColumn("Local (ARS)", min_value=0.0, format="$ %.2f"),
        "Externo (ARS)": st.column_config.NumberColumn("Externo (ARS)", min_value=0.0, format="$ %.2f"),
        "Externo (USD)": st.column_config.NumberColumn("Externo (USD)", min_value=0.0, format="USD %.2f")
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic"
)


# --- 4. MOTOR DE CÁLCULO Y GENERACIÓN DE INFORME ---
if st.button("Procesar Ajuste por Inflación y Dólar", type="primary"):
    
    # Buscamos el índice de la fecha de actualización
    try:
        indice_actualizacion = df_indices.loc[df_indices["Periodo"] == periodo_actualizacion, "Indice"].values[0]
    except IndexError:
        st.error("No se encontró el índice IPIM para el mes de actualización seleccionado.")
        st.stop()

    resultados = []
    
    with st.spinner("Realizando cruces de índices y cotizaciones..."):
        for index, row in edited_df.iterrows():
            mes_venta = row["Mes Venta (YYYY-MM)"]
            
            # Solo procesamos si el usuario seleccionó un mes
            if pd.notna(mes_venta) and mes_venta != "":
                
                # 1. Buscar Índice base
                try:
                    indice_base = df_indices.loc[df_indices["Periodo"] == mes_venta, "Indice"].values[0]
                    coeficiente = indice_actualizacion / indice_base
                except IndexError:
                    coeficiente = 1.0 # Fallback si no hay índice
                    
                # 2. Buscar Dólar
                try:
                    cotizacion_dolar = df_dolar.loc[df_dolar["Periodo"] == mes_venta, "Cotizacion"].values[0]
                except IndexError:
                    cotizacion_dolar = 0.0 # Fallback si no hay cotización
                
                # 3. Cálculos
                ventas_usd_pesificadas = row["Externo (USD)"] * cotizacion_dolar
                total_historico = row["Local (ARS)"] + row["Externo (ARS)"] + ventas_usd_pesificadas
                total_reexpresado = total_historico * coeficiente
                
                resultados.append({
                    "Periodo Venta": mes_venta,
                    "Cotiz. BCRA": cotizacion_dolar,
                    "USD en ARS": ventas_usd_pesificadas,
                    "Total Local + Exp (Histórico)": total_historico,
                    "Coef. Aplicado": coeficiente,
                    "TOTAL REEXPRESADO": total_reexpresado
                })
        
        df_resultados = pd.DataFrame(resultados)
        
    # --- 5. VISUALIZACIÓN DEL INFORME FINAL ---
    st.header("3. Informe de Evolución en Moneda Homogénea")
    
    if not df_resultados.empty:
        total_historico_sum = df_resultados['Total Local + Exp (Histórico)'].sum()
        total_reexpresado_sum = df_resultados['TOTAL REEXPRESADO'].sum()
        
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Facturación Histórica Total", f"$ {total_historico_sum:,.2f}")
        col_res2.metric("Facturación Reexpresada Total", f"$ {total_reexpresado_sum:,.2f}")
        
        # Muestra la tabla resultante con formato de moneda
        st.dataframe(
            df_resultados.style.format({
                "Cotiz. BCRA": "$ {:.2f}",
                "USD en ARS": "$ {:,.2f}",
                "Total Local + Exp (Histórico)": "$ {:,.2f}",
                "Coef. Aplicado": "{:.4f}",
                "TOTAL REEXPRESADO": "$ {:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico comparativo
        st.subheader("Gráfico de Evolución")
        # Preparamos los datos para el gráfico
        df_grafico = df_resultados.copy()
        df_grafico = df_grafico.set_index("Periodo Venta")[["Total Local + Exp (Histórico)", "TOTAL REEXPRESADO"]]
        st.line_chart(df_grafico)
        
    else:
        st.warning("No se generaron resultados. Verifica los datos ingresados.")
