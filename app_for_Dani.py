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

# --- 1. UTILIDADES Y PIL (INCLUIDO) ---
def procesar_foto(uploaded_file):
    """Reduce el tamaño de la foto con PIL para ahorrar espacio"""
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

# --- 2. LOGIN (CON DOBLE PIN) ---
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

# --- 3. DISEÑO RUSTAMASTER (VERDE) ---
u = st.session_state['user']
# Ocultamos la basura superior de Streamlit para que se vea SaaS
st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    [data-testid="stToolbar"] {{ visibility: visible !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{get_base64(st.secrets.get('APP_BACKGROUND_PATH'))});" if get_base64(st.secrets.get('APP_BACKGROUND_PATH')) else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.9); padding: 2rem; border-radius: 20px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 10px; border: none; font-weight: bold; }}
    h1, h2, .stMetric, label {{ color: #25D366 !important; }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center;'>🚚 RUTA MASTER - DANI</h2>", unsafe_allow_html=True)
tabs = st.tabs(["📝 REGISTRO", "🔧 MOTOR", "📊 REPORTES"])

# --- TAB 1: REGISTRO (ORIGINAL Y SENCILLO) ---
with tabs[0]:
    with st.form("f_dani", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Otros"])
        monto = col2.number_input("Monto (CRC)", min_value=0)
        km = st.number_input("Kilometraje Actual", min_value=0)
        foto = st.file_uploader("📷 Foto Comprobante (Opcional)", type=['jpg', 'png', 'jpeg'])
        if st.form_submit_button("SINCRONIZAR DATOS"):
            try:
                foto_bytes = procesar_foto(foto) if foto else None
                supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": foto_bytes}).execute()
                supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                st.success("✅ ¡Listo Dani! Datos sincronizados.")
            except: st.error("Error al conectar.")

# --- TAB 2: MOTOR ---
with tabs[1]:
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Actual", f"{kh:,} km")
    except: st.info("Sincronizando...")

# --- TAB 3: REPORTES RESTAURADO (GRÁFICO BARRAS Y TABLA PLANA) ---
with tabs[2]:
    st.header("📈 Historial de Viajes")
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    df = pd.DataFrame(rg.data)
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        m_sel = st.selectbox("Mes", meses, index=datetime.now().month-1)
        df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
        
        # RESTAURAMOS EL GRÁFICO DE BARRAS ORIGINAL
        grafico_datos = df_f.groupby('concepto')['monto'].sum()
        st.bar_chart(grafico_datos)
        
        # RESTAURAMOS LA TABLA DE DATOS PLANA
        st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
        
        st.divider()
        # SECCIÓN DE EDICIÓN Oculta (Usando el expanded de VS Code)
        with st.expander("🛠️ Administrar Registros (Ver Fotos o Borrar)"):
            for i, row in df_f.iterrows():
                c1, c2, c3 = st.columns([0.8, 0.1, 0.1])
                c1.write(f"📅 {row['fecha'].strftime('%d/%m')} | {row['concepto']}")
                if row.get('foto_comprobante'):
                    if c2.button("📷", key=f"img_{row['id']}"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                if c3.button("🗑️", key=f"del_{row['id']}"):
                    supabase.table("gastos").delete().eq("id", row['id']).execute()
                    st.rerun()
                    
    else: st.info("No hay datos registrados aún.")