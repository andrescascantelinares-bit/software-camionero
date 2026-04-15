import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os

# --- 0. CONFIGURACIÓN DE PÁGINA (Debe ser el primer comando) ---
st.set_page_config(page_title="Logística", layout="centered")

# --- INICIALIZAR SUPABASE ---
@st.cache_resource
def init_conexion():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_conexion()

# --- 1. GESTIÓN DE MARCA (LOGO Y FONDO) ---
@st.cache_resource
def obtener_marca():
    try:
        logo = st.secrets.get("APP_LOGO_PATH", None)
        fondo = st.secrets.get("APP_BACKGROUND_PATH", None)
        return logo, fondo
    except Exception:
        return None, None

logo_path, fondo_path = obtener_marca()

# --- INYECTAR FONDO DE PANTALLA (Si existe) ---
if fondo_path and os.path.exists(fondo_path):
    with open(fondo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url(data:image/png;base64,{encoded_string});
        background-size: cover;
        background-position: center;
        background-blend-mode: overlay;
        background-color: rgba(255,255,255,0.85); /* 0.85 hace que el fondo sea blanquito para poder leer las letras */
    }}
    </style>
    """,
    unsafe_allow_html=True
    )

# --- 2. CONFIGURACIÓN DE APOYO TÉCNICO Y SIDEBAR ---
FECHA_SOPORTE = "2026-05-01" 

def mostrar_estado_soporte():
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    with st.sidebar:
        # Aquí es donde aparece el Logo de tu primo
        if logo_path and os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            st.divider()

        st.markdown("### 🛡️ Aisaac-Shield")
        if fecha_actual > FECHA_SOPORTE:
            st.info("Soporte técnico: Finalizado")
            url_wa = "https://wa.me/5068XXX?text=Hola%20Andres!%20Necesito%20actualizar%20la%20app"
            st.link_button("📲 Contactar a Andrés", url_wa)
        else:
            st.success("Soporte técnico: Activo")
            st.caption(f"Vence el: {FECHA_SOPORTE}")

mostrar_estado_soporte()

# --- 3. FUNCIONES DE BASE DE DATOS (NUBE) ---
def guardar_gasto(fecha, concepto, monto, foto_bytes):
    foto_b64 = base64.b64encode(foto_bytes).decode('utf-8') if foto_bytes else None
    datos = {"fecha": fecha, "concepto": concepto, "monto": monto, "foto": foto_b64}
    supabase.table("gastos").insert(datos).execute()

def eliminar_gasto_db(id_gasto):
    supabase.table("gastos").delete().eq("id", id_gasto).execute()

# --- 4. INTERFAZ PRINCIPAL (TABS) ---
tab1, tab2, tab3 = st.tabs(["➕ Viajes", "📉 Gastos con Foto", "📊 Resumen"])

with tab1:
    st.header("Registrar Viaje")
    with st.form("form_viaje", clear_on_submit=True):
        f = st.date_input("Fecha", datetime.now())
        cli = st.text_input("Cliente")
        ori = st.text_input("Origen")
        des = st.text_input("Destino")
        mon = st.number_input("Monto Flete (CRC)", min_value=0, step=1000)
        not_v = st.text_area("Notas")
        
        if st.form_submit_button("Guardar Viaje"):
            if not cli.strip() or mon == 0:
                st.error("⚠️ ¡Epa! Te faltó poner el nombre del cliente o el monto está en cero. Revisá los datos.")
            else:
                try:
                    with st.spinner("Buscando señal y conectando con la nube..."):
                        datos_viaje = {"fecha": f.strftime("%Y-%m-%d"), "cliente": cli, "origen": ori, "destino": des, "monto": mon, "notas": not_v}
                        supabase.table("viajes").insert(datos_viaje).execute()
                        st.success("✅ Viaje guardado con éxito.")
                except Exception:
                    st.error("📡 Sin señal. No pudimos conectar con la base de datos. Por favor, buscá un lugar con internet e intentalo de nuevo.")
                    st.warning("💡 Tip: No cerrés la app para no perder lo que escribiste.")

with tab2:
    st.header("Registrar Gasto")
    with st.form("form_gasto", clear_on_submit=True):
        f_g = st.date_input("Fecha Gasto", datetime.now())
        concep = st.selectbox("Concepto", ["Diesel", "Peaje", "Mantenimiento", "Comida", "Otros"])
        mon_g = st.number_input("Monto (CRC)", min_value=0, step=1000)
        img_file = st.camera_input("Capturar factura")
        
        if st.form_submit_button("Guardar Gasto"):
            if mon_g == 0:
                st.error("⚠️ El monto del gasto no puede estar en cero.")
            else:
                try:
                    with st.spinner("Buscando señal... Enviando factura..."):
                        foto_bin = img_file.getvalue() if img_file else None
                        guardar_gasto(f_g.strftime("%Y-%m-%d"), concep, mon_g, foto_bin)
                        st.success("✅ Gasto guardado con éxito.")
                except Exception:
                    st.error("📡 Error de conexión. La señal está muy débil para subir la foto o el gasto.")
                    st.info("Intentá de nuevo cuando tengás mejor cobertura.")

with tab3:
    st.header("📊 Resumen y Excel")
    try:
        res_viajes = supabase.table("viajes").select("*").execute()
        res_gastos = supabase.table("gastos").select("*").execute()
        datos_cargados = True
    except Exception:
        st.error("📡 Sin conexión. No pudimos descargar el resumen de la nube.")
        datos_cargados = False
        res_viajes = None
        res_gastos = None
    
    if datos_cargados:
        cols_v = ['id', 'fecha', 'cliente', 'origen', 'destino', 'monto', 'notas']
        cols_g = ['id', 'fecha', 'concepto', 'monto', 'foto']
        df_v = pd.DataFrame(res_viajes.data) if res_viajes.data else pd.DataFrame(columns=cols_v)
        df_g = pd.DataFrame(res_gastos.data) if res_gastos.data else pd.DataFrame(columns=cols_g)

        if not df_v.empty or not df_g.empty:
            df_v['fecha'] = pd.to_datetime(df_v['fecha'])
            df_g['fecha'] = pd.to_datetime(df_g['fecha'])
            años = sorted(df_g['fecha'].dt.year.unique(), reverse=True) if not df_g.empty else [datetime.now().year]
            col1, col2 = st.columns(2)
            a_sel = col1.selectbox("Año", años)
            m_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel_nom = col2.selectbox("Mes", m_nombres, index=datetime.now().month - 1)
            m_sel = m_nombres.index(m_sel_nom) + 1

            df_v_f = df_v[(df_v['fecha'].dt.year == a_sel) & (df_v['fecha'].dt.month == m_sel)]
            df_g_f = df_g[(df_g['fecha'].dt.year == a_sel) & (df_g['fecha'].dt.month == m_sel)]

            t_v = df_v_f['monto'].sum()
            t_g = df_g_f['monto'].sum()
            st.metric("Ganancia Neta", f"₡{t_v - t_g:,.0f}", delta=f"Fletes: ₡{t_v:,.0f}")

            st.divider()
            if not df_g_f.empty:
                csv = df_g_f.drop(columns=['foto']).to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Gastos para Excel", csv, f"gastos_{m_sel_nom}.csv", "text/csv")
                fig = px.pie(df_g_f, values='monto', names='concepto', hole=0.4, title="Distribución de Gastos")
                st.plotly_chart(fig)

            for _, row in df_g_f.iterrows():
                with st.expander(f"{row['concepto']} - ₡{row['monto']:,.0f}"):
                    if row['foto']: 
                        st.image(base64.b64decode(row['foto']))
                    if st.button("Eliminar", key=f"del_{row['id']}"):
                        eliminar_gasto_db(row['id'])
                        st.rerun()
        else:
            st.info("Sin datos registrados aún.")