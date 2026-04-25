import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io
import plotly.express as px
import time

# --- 0. CONFIGURACIÓN ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")
ZONA_CR = timezone(timedelta(hours=-6)) # Ajuste Costa Rica

@st.cache_resource
def init_conexion():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_conexion()
except Exception as e:
    st.error("Error de configuración en Secrets.")

# --- 1. UTILIDADES ---
def procesar_foto(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800)) 
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=70)
    return base64.b64encode(output.getvalue()).decode()

# --- 2. DISEÑO VISUAL CON LUCES DE NEÓN ANIMADAS ---
st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2rem; border-radius: 30px; border: 1px solid #25D366; }}
    
    /* ANIMACIÓN DE ESCANEO LÁSER AISAAC-SHIELD */
    @keyframes neon-scan {{
        0% {{ box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); border-color: rgba(37, 211, 102, 0.2); }}
        50% {{ box-shadow: 0 0 25px rgba(37, 211, 102, 0.8); border-color: rgba(37, 211, 102, 1); }}
        100% {{ box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); border-color: rgba(37, 211, 102, 0.2); }}
    }}

    .shield-box {{ 
        margin: 20px 0; padding: 20px; text-align: center; border: 2px solid #25D366;
        animation: neon-scan 2s infinite ease-in-out;
        background: 
            linear-gradient(to right, #25D366 4px, transparent 4px) 0 0,
            linear-gradient(to bottom, #25D366 4px, transparent 4px) 0 0,
            linear-gradient(to left, #25D366 4px, transparent 4px) 100% 0,
            linear-gradient(to bottom, #25D366 4px, transparent 4px) 100% 0,
            linear-gradient(to right, #25D366 4px, transparent 4px) 0 100%,
            linear-gradient(to top, #25D366 4px, transparent 4px) 0 100%,
            linear-gradient(to left, #25D366 4px, transparent 4px) 100% 100%,
            linear-gradient(to top, #25D366 4px, transparent 4px) 100% 100%;
        background-repeat: no-repeat; background-size: 20px 20px;
        background-color: rgba(37, 211, 102, 0.05);
    }}
    .stMetric {{ color: #25D366 !important; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN CON AVISO ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    st.markdown("<div class='shield-box'><b style='color:#25D366;'>🛡️ AISAAC-SHIELD ACTIVE</b><br><small style='color:white;'>Verificando integridad del sistema...</small></div>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "padre_andres"})
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. DATA ENGINE ---
u = st.session_state['user']
hoy = datetime.now(ZONA_CR)
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.upper()}</h2>", unsafe_allow_html=True)
m_sel = st.selectbox("Mes", meses, index=hoy.month-1)

df_f = pd.DataFrame()
km_actual = 0
try:
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    if rg.data:
        df_raw = pd.DataFrame(rg.data)
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        df_f = df_raw[df_raw['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
    rv = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("id", desc=True).limit(1).execute()
    km_actual = rv.data[0]['km_actual'] if rv.data else 0
except: pass

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    op = st.radio("ACCION:", ["💸 Gasto Operativo", "🛣️ Finalizar Viaje"])
    with st.form("f_registro", clear_on_submit=True):
        f_in = st.date_input("Fecha", hoy.date())
        if op == "💸 Gasto Operativo":
            cat = st.selectbox("Tipo", ["Diesel", "Peaje", "Aceite", "Otros"])
            mon = st.number_input("Monto (CRC)", value=None)
            if st.form_submit_button("GUARDAR"):
                if mon:
                    supabase.table("gastos").insert({"fecha": str(f_in), "concepto": cat, "monto": int(mon), "cliente_id": u}).execute()
                    st.success("✅ Gasto guardado"); time.sleep(1); st.rerun()
        else:
            c1, c2 = st.columns(2); o = c1.text_input("Origen"); d = c2.text_input("Destino")
            km = st.number_input("KM Llegada", value=None, placeholder=f"Último: {km_actual}")
            if st.form_submit_button("FINALIZAR VIAJE"):
                if km and o and d:
                    supabase.table("viajes").insert({"fecha": str(f_in), "origen": o, "destino": d, "cliente_id": u, "km_actual": int(km)}).execute()
                    st.success("✅ Viaje guardado"); st.balloons(); time.sleep(1.5); st.rerun()

# --- TAB 3: DATOS ---
with tabs[2]:
    st.metric("KM ACTUAL", f"{km_actual:,} KM")
    if not df_f.empty:
        st.metric(f"TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        fig = px.pie(df_f.groupby('concepto')['monto'].sum().reset_index(), values='monto', names='concepto', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', legend_font_color="#25D366")
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<div class='shield-box'><span style='color:#25D366; font-weight:900;'>🛡️ AISAAC-SHIELD ACTIVATED</span></div>", unsafe_allow_html=True)