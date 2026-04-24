import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. UTILIDADES Y PROCESAMIENTO DE FOTOS ---
def procesar_foto(uploaded_file):
    """Reduce el tamaño de la foto para ahorrar espacio en Supabase"""
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=70)
    return base64.b64encode(output.getvalue()).decode()

def get_base64(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    return None

# --- 2. LOGIN (DOBLE PIN: DANI Y PAPÁ) ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 3. DISEÑO Y ESTILOS ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.9); padding: 2rem; border-radius: 20px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 10px; font-weight: bold; border: none; }}
    h1, h2, label, .stMetric {{ color: #25D366 !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

# Selector de Mes Global (Afecta a todas las pestañas)
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
m_sel = st.selectbox("📅 Filtrar información por mes:", meses, index=datetime.now().month-1)
st.write("") # Espacio en blanco

# --- ESTRUCTURA DE 3 PESTAÑAS EXACTA ---
tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- PESTAÑA 1: REGISTRO (Ingreso de datos) ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo de Gasto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = col2.number_input("Monto (CRC)", min_value=0, step=500)
        km = st.number_input("Kilometraje Actual", min_value=0, step=1)
        foto = st.file_uploader("📷 Foto del Comprobante", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("SINCRONIZAR DATOS"):
            try:
                foto_final = procesar_foto(foto) if foto else None
                # Guarda el gasto
                supabase.table("gastos").insert({
                    "fecha": str(datetime.now().date()), 
                    "concepto": tipo, "monto": monto, 
                    "cliente_id": u, "foto_comprobante": foto_final
                }).execute()
                # Guarda el Kilometraje
                if km > 0:
                    supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                st.success("✅ Datos guardados correctamente en la nube.")
            except: st.error("Error al guardar. Verifique su conexión.")

# --- LECTURA DE BASE DE DATOS (Para Pestañas 2 y 3) ---
df = pd.DataFrame()
df_f = pd.DataFrame()
try:
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    df = pd.DataFrame(rg.data)
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
        df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
except: pass

# --- PESTAÑA 2: GASTOS (Administrar, Ver fotos y Borrar) ---
with tabs[1]:
    st.subheader(f"Lista de Gastos - {m_sel}")
    if not df_f.empty:
        for i, row in df_f.iterrows():
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"📅 {row['fecha'].strftime('%d/%m')} | {row['concepto']} | `CRC {row['monto']:,.0f}`")
            # Botón de ver foto
            if row.get('foto_comprobante'):
                if c2.button("📷 Ver", key=f"img_{row['id']}"):
                    st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            # Botón de borrar
            if c3.button("🗑️ Borrar", key=f"del_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute()
                st.rerun()
    else:
        st.info(f"No hay registros ingresados en {m_sel}.")

# --- PESTAÑA 3: DATOS (Métricas, Gráficos y Motor) ---
with tabs[2]:
    st.subheader("Análisis de Operación")
    
    # Métrica de Kilometraje Actual (Motor)
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Actual Flota", f"{kh:,} km")
    except: pass
    st.divider()

    # Gráficos y tabla de datos
    if not df_f.empty:
        st.metric(f"Total Gastado ({m_sel})", f"CRC {df_f['monto'].sum():,.0f}")
        
        st.write("📈 Gráfico de Gastos por Categoría")
        st.bar_chart(df_f.groupby('concepto')['monto'].sum())
        
        st.write("📋 Tabla Resumen")
        st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
    else:
        st.info("Ingresa gastos para ver los gráficos de este mes.")