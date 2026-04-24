import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io

# --- 0. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. MOTOR DE UTILIDADES (FOTOS Y ESTILO) ---
def procesar_foto(uploaded_file):
    """Optimiza la imagen antes de subirla para no saturar la base de datos"""
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

# --- 2. LOGIN MULTIUSUARIO ---
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

# --- 3. INTERFAZ VISUAL ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(0, 0, 0, 0.9); padding: 2rem; border-radius: 20px; border: 1px solid #25D366; }}
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 10px; font-weight: bold; }}
    h1, h2, label, .stMetric {{ color: #25D366 !important; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
tabs = st.tabs(["📝 REGISTRO", "📊 DATOS Y GASTOS"])

# --- TAB 1: REGISTRO DE GASTOS ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo de Gasto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = col2.number_input("Monto (CRC)", min_value=0, step=500)
        foto = st.file_uploader("📷 Foto del Comprobante", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("SINCRONIZAR GASTO"):
            try:
                foto_final = procesar_foto(foto) if foto else None
                # Guardamos directamente en la tabla gastos de Supabase
                supabase.table("gastos").insert({
                    "fecha": str(datetime.now().date()), 
                    "concepto": tipo, 
                    "monto": monto, 
                    "cliente_id": u,
                    "foto_comprobante": foto_final
                }).execute()
                st.success(f"✅ Gasto registrado para {u}")
                st.balloons()
            except: st.error("Error al guardar. Verifique la columna 'foto_comprobante' en Supabase.")

# --- TAB 2: VISUALIZACIÓN DE GASTOS ---
with tabs[1]:
    st.subheader("Análisis Mensual")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df = pd.DataFrame(rg.data)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            m_sel = st.selectbox("Seleccionar Mes", meses, index=datetime.now().month-1)
            df_f = df[df['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                # Métrica de Total Mensual
                st.metric(f"Total {m_sel}", f"CRC {df_f['monto'].sum():,.0f}")
                
                # Gráfico de Barras por concepto
                st.subheader("📈 Gastos por Categoría")
                st.bar_chart(df_f.groupby('concepto')['monto'].sum())
                
                # Tabla Detallada
                st.subheader("📋 Historial")
                st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
            else:
                st.info(f"No hay gastos registrados en {m_sel}")
        else:
            st.info("Aún no hay registros en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")