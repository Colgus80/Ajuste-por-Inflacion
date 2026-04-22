import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.header("CARGA DE DATOS")

# --- 1. DATOS DE LOS ÚLTIMOS EE.CC. ---
st.subheader("Datos del Ejercicio")

col1, col2, col3 = st.columns(3)

with col1:
    # Formato de fecha para ingresar solo Mes y Año
    fecha_eecc = st.date_input(
        "Fecha Últimos EE.CC.:", 
        value=datetime(2025, 6, 30), # Valor de ejemplo (06/2025)
        format="MM/YYYY"
    )

with col2:
    # step=1 y format="%d" aseguran que no haya decimales en la entrada
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

# --- 2. FECHA DE REEXPRESIÓN ---
st.subheader("Parámetros de Reexpresión")
# Simulamos que leemos el último mes de tu tabla de índices (ej. 03/2026)
ultimo_mes_ipim = datetime(2026, 3, 31) 

fecha_reexpresion = st.date_input(
    "Fecha a la cual se requiere reexpresar:", 
    value=ultimo_mes_ipim,
    format="MM/YYYY"
)

st.markdown("---")

# --- 3. GENERACIÓN DINÁMICA DE MESES POST CIERRE ---
st.subheader("Facturación Post Cierre")

# Calculamos el mes siguiente al cierre de los EE.CC.
mes_inicio_post_cierre = fecha_eecc + relativedelta(months=1)
# Fecha actual (hoy 04/2026)
fecha_actual = datetime(2026, 4, 1)

# Generamos la lista de meses automáticamente
if mes_inicio_post_cierre <= fecha_actual:
    rango_meses = pd.date_range(
        start=mes_inicio_post_cierre.replace(day=1), 
        end=fecha_actual.replace(day=1), 
        freq='MS' # MS = Month Start (Inicio de mes)
    )
    
    # Creamos el DataFrame inicial para la tabla
    df_post_cierre = pd.DataFrame({
        "Periodo": [mes.strftime('%m/%Y') for mes in rango_meses],
        "Ventas ($)": [0] * len(rango_meses)
    })
    
    st.write("Complete la facturación para los meses habilitados:")
    
    # Tabla editable sin decimales
    df_editado = st.data_editor(
        df_post_cierre,
        column_config={
            "Periodo": st.column_config.TextColumn("Periodo", disabled=True), # El usuario no puede cambiar el mes
            "Ventas ($)": st.column_config.NumberColumn(
                "Ventas ($)", 
                min_value=0, 
                step=1, 
                format="%d" # Sin decimales
            )
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("La fecha de los últimos EE.CC. es reciente. No hay meses post cierre para habilitar.")
    df_editado = pd.DataFrame()


# --- 4. RESUMEN INFORMACION REEXPRESADA ---
st.markdown("---")
st.subheader("Resumen Información Reexpresada en Moneda Homogénea")

if st.button("Calcular Promedios y Variación"):
    # (Aquí iría la búsqueda real de los índices IPIM en tu tabla)
    # Para el ejemplo, simularemos los coeficientes:
    coef_eecc = 1.85  # Inflación desde fecha_eecc hasta fecha_reexpresion
    coef_post_cierre_promedio = 1.30 # Promedio de los coeficientes de los meses cargados
    
    # Cálculos
    promedio_mensual_eecc_historico = facturacion_eecc / meses_ejercicio
    promedio_mensual_eecc_reexpresado = promedio_mensual_eecc_historico * coef_eecc
    
    total_post_cierre_historico = df_editado["Ventas ($)"].sum() if not df_editado.empty else 0
    cantidad_meses_post = len(df_editado) if not df_editado.empty else 1
    
    # Asumiendo un cálculo simplificado para el ejemplo
    promedio_post_cierre_reexpresado = (total_post_cierre_historico / cantidad_meses_post) * coef_post_cierre_promedio
    
    variacion = 0
    if promedio_mensual_eecc_reexpresado > 0:
        variacion = ((promedio_post_cierre_reexpresado / promedio_mensual_eecc_reexpresado) - 1) * 100

    # Funciones para formatear números al estilo 1.500.000 (Puntos para miles, sin decimales)
    def formato_arg(numero):
        return f"{numero:,.0f}".replace(",", ".")

    # Mostramos los resultados en columnas
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
