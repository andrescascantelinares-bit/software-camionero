import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io
import plotly.express as px

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_conexion()

# --- 1. UTILIDADES ---
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

# --- 2. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 3. PROCESAMIENTO DE DATOS GLOBAL (FUERA DE TABS) ---
u = st.session_state['user']
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# Estilos CSS
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))
st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2.5rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border-left: 6px solid #25D366; margin-bottom: 15px; border-right: 1px solid rgba(37, 211, 102, 0.2); }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)
m_sel = st.selectbox("📅 Seleccione el periodo:", meses, index=datetime.now().month-1)

# CARGA DE DATOS CENTRALIZADA
df_f = pd.DataFrame()
km_actual = 0

try:
    # Gastos
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    df_raw = pd.DataFrame(rg.data)
    if not df_raw.empty:
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        df_f = df_raw[df_raw['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
    
    # Kilometraje
    rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
    km_actual = rk.data[0]['km_actual'] if rk.data else 0
except Exception as e:
    st.error(f"Error de conexión: {e}")

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = c2.number_input("Monto (CRC)", value=None, placeholder="0", step=500)
        km = st.number_input("Kilometraje Actual", value=None, placeholder="0", step=1)
        foto = st.file_uploader("📷 Foto Comprobante", type=['jpg', 'png', 'jpeg'])
        if st.form_submit_button("SINCRONIZAR DATOS"):
            if monto and km:
                f_bytes = procesar_foto(foto) if foto else None
                supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": f_bytes}).execute()
                supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                st.success("✅ Sincronizado")
                st.rerun()

# --- TAB 2: GASTOS (TARJETAS VISIBLES) ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"""
            <div class="gasto-card">
                <div style='color: #888; font-size: 0.8rem;'>{row['fecha'].strftime('%d %b, %Y')}</div>
                <div style='font-size: 1.2rem; font-weight: bold;'>{row['concepto']}</div>
                <div style='color: #25D366; font-size: 1.5rem; font-weight: 900;'>CRC {row['monto']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if row.get('foto_comprobante'):
                with c1.popover("📷 Ver Ticket", use_container_width=True):
                    st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if c2.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute()
                st.rerun()
    else:
        st.info(f"No hay registros en {m_sel}")

# --- TAB 3: DATOS (GRÁFICO CORREGIDO) ---
with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL", f"{km_actual:,} KM")
    st.divider()
    if not df_f.empty:
        st.metric(f"INVERSIÓN TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        
        # Gráfico con Plotly Express
        resumen = df_f.groupby('concepto')['monto'].sum().reset_index()
        fig = px.bar(resumen, x='concepto', y='monto', 
                     color='monto', color_continuous_scale='Greens',
                     labels={'monto': 'Monto', 'concepto': 'Tipo'})
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          font_color="#25D366", height=350, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Agregue datos para generar estadísticas.")