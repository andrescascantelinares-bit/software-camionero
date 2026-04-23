import streamlit as st
from fpdf import FPDF
from PIL import Image
import io
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster Logistics", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. MOTOR DE OPTIMIZACIÓN Y UTILIDADES ---
def procesar_foto(uploaded_file):
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

def limpiar(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

# --- 2. LOGIN ---
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

# --- 3. ESTILO Y DISEÑO ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.9); padding: 2rem; border-radius: 20px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 10px; border: none; font-weight: bold; }}
    h1, h2, label, .stMetric {{ color: #25D366 !important; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
tabs = st.tabs(["📝 REGISTRO", "🔧 MOTOR", "📊 REPORTES Y DATOS"])

# --- TAB 1: REGISTRO (MÁS DINÁMICO Y EDITABLE) ---
with tabs[0]:
    st.subheader("Nuevo Registro de Gasto")
    with st.container():
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo de Gasto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = c2.number_input("Monto en Colones (CRC)", min_value=0, step=500)
        
        c3, c4 = st.columns(2)
        km = c3.number_input("Kilometraje Actual", min_value=0, step=1)
        fecha_manual = c4.date_input("Fecha del Gasto", datetime.now())
        
        foto = st.file_uploader("📷 Subir Comprobante (Opcional)", type=['jpg', 'png', 'jpeg'])
        
        if st.button("🚀 GUARDAR Y SINCRONIZAR"):
            try:
                f_b64 = procesar_foto(foto) if foto else None
                supabase.table("gastos").insert({
                    "fecha": str(fecha_manual), "concepto": tipo, "monto": monto, 
                    "cliente_id": u, "foto_comprobante": f_b64
                }).execute()
                supabase.table("viajes").insert({"fecha": str(fecha_manual), "km_actual": km, "cliente_id": u}).execute()
                st.success("✅ ¡Registro guardado exitosamente!")
                st.balloons()
            except: st.error("Error al sincronizar con la base de datos.")

# --- TAB 2: MOTOR ---
with tabs[1]:
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Actual", f"{kh:,} km")
    except: st.info("Sincronizando kilometraje...")

# --- TAB 3: REPORTES (GRÁFICOS RESTAURADOS) ---
with tabs[2]:
    st.subheader("Visualización de Datos")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Filtrar por Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                # MÉTRICA Y GRÁFICO (RESTAURADOS)
                st.metric(f"Total Gastos {m_sel}", f"CRC {df_f['monto'].sum():,.0f}")
                st.subheader("📈 Distribución de Gastos")
                st.bar_chart(df_f.groupby('concepto')['monto'].sum())
                
                # TABLA DE DATOS
                st.subheader("📋 Historial Detallado")
                st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
                
                # SECCIÓN DE EDICIÓN/FOTOS
                with st.expander("🛠️ Ver Fotos o Borrar Registros"):
                    for i, row in df_f.iterrows():
                        col_a, col_b, col_c = st.columns([0.6, 0.2, 0.2])
                        col_a.write(f"📅 {row['fecha'].strftime('%d/%m')} - {row['concepto']}")
                        if row.get('foto_comprobante'):
                            if col_b.button("📷 Ver", key=f"v_{row['id']}"):
                                st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                        if col_c.button("🗑️", key=f"d_{row['id']}"):
                            supabase.table("gastos").delete().eq("id", row['id']).execute()
                            st.rerun()
            else: st.info(f"No hay registros para {m_sel}.")
        else: st.info("Aún no tienes gastos registrados.")
    except Exception as e: st.error(f"Error al cargar reportes.")