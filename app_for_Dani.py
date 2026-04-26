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
ZONA_CR = timezone(timedelta(hours=-6)) 

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

# --- 2. DISEÑO VISUAL Y LUCES NEÓN ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH") if "APP_BACKGROUND_PATH" in st.secrets else None)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.92); padding: 1.5rem; border-radius: 25px; border: 1px solid #25D366; }}
    
    .header-shield {{
        background: rgba(0, 0, 0, 0.8);
        padding: 15px;
        border-radius: 15px;
        border-bottom: 3px solid #25D366;
        text-align: center;
        margin-bottom: 20px;
    }}

    /* EFECTO DE LUCES NEÓN FINAL */
    .neon-shield {{
        text-align: center;
        color: #25D366 !important;
        font-weight: bold;
        letter-spacing: 3px;
        padding: 15px;
        margin-top: 40px;
        border: 2px solid #25D366;
        border-radius: 15px;
        background: rgba(37, 211, 102, 0.1);
        box-shadow: 0 0 20px rgba(37, 211, 102, 0.6), inset 0 0 10px rgba(37, 211, 102, 0.4);
        text-shadow: 0 0 12px rgba(37, 211, 102, 1);
        animation: pulse-neon 2s infinite alternate;
    }}

    @keyframes pulse-neon {{
        from {{ box-shadow: 0 0 10px rgba(37, 211, 102, 0.4); }}
        to {{ box-shadow: 0 0 25px rgba(37, 211, 102, 0.8); }}
    }}

    .gasto-card {{ 
        background: rgba(0, 0, 0, 0.95) !important; 
        padding: 20px; border-radius: 15px; border: 1px solid #25D366; 
        margin-bottom: 10px;
    }}

    /* BOTONES DE EXPORTACIÓN CON COLORES OFICIALES */
    div[data-testid="stColumn"]:nth-of-type(2) [data-testid="stDownloadButton"] button {{
        background: rgba(0, 50, 0, 0.8) !important;
        border: 2px solid #217346 !important;
        color: #217346 !important;
    }}
    div[data-testid="stColumn"]:nth-of-type(3) [data-testid="stDownloadButton"] button {{
        background: rgba(50, 0, 0, 0.8) !important;
        border: 2px solid #FF0000 !important;
        color: #FF0000 !important;
    }}

    h1, h2, h3, label {{ color: #25D366 !important; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; width: 100%; }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<div class='header-shield'><h1>RUTAMASTER</h1></div>", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "padre_andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. CARGA DE DATOS ---
u = st.session_state['user']
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy_cr_dt = datetime.now(ZONA_CR)
mes_actual_cr = hoy_cr_dt.month

st.markdown(f"<div class='header-shield'><h2>{u.upper()}</h2></div>", unsafe_allow_html=True)

with st.expander(f"PERIODO: {st.session_state.get('mes_f', meses_nombres[mes_actual_cr-1])}", expanded=False):
    m_sel = st.segmented_control("Mes:", options=meses_nombres, default=meses_nombres[mes_actual_cr-1], key="mes_f")

df_f = pd.DataFrame()
km_actual = 0
try:
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    if rg.data:
        df_raw = pd.DataFrame(rg.data)
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        df_f = df_raw[df_raw['fecha'].dt.month == (meses_nombres.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
    
    rv = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("id", desc=True).limit(1).execute()
    km_actual = rv.data[0]['km_actual'] if rv.data else 0
except: pass

tabs = st.tabs(["REGISTRO", "GASTOS", "DATOS"])

# --- TAB 1: REGISTRO (CON ESCRITURA INTELIGENTE) ---
with tabs[0]:
    st.markdown("### Finalizar Viaje")
    with st.form("f_viaje", clear_on_submit=True):
        fecha = st.date_input("Fecha", hoy_cr_dt.date())
        cli = st.text_input("Cliente / Empresa")
        c3, c4 = st.columns(2)
        orig = c3.text_input("Origen")
        dest = c4.text_input("Destino")
        c5, c6 = st.columns(2)
        
        cost = c5.number_input("Costo (CRC)", min_value=0, value=None, placeholder="Monto...")
        km = c6.number_input("KM Llegada", min_value=km_actual, value=None, placeholder=f"Min: {km_actual}")
        
        if st.form_submit_button("REGISTRAR VIAJE"):
            if cli and orig and dest and km is not None:
                supabase.table("viajes").insert({
                    "fecha": str(fecha), "cliente": cli, "origen": orig, "destino": dest, 
                    "monto": int(cost) if cost else 0, "cliente_id": u, "km_actual": int(km)
                }).execute()
                st.success("VIAJE GUARDADO")
                time.sleep(1.5); st.rerun()

# --- TAB 2: GASTOS ---
with tabs[1]:
    with st.expander("AGREGAR GASTO", expanded=False):
        with st.form("f_gasto_nuevo", clear_on_submit=True):
            f_gasto = st.date_input("Fecha", hoy_cr_dt.date())
            tipo = st.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
            monto = st.number_input("Monto (CRC)", min_value=0, value=None, placeholder="Monto...")
            foto = st.file_uploader("Foto", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("GUARDAR GASTO"):
                if monto:
                    foto_b64 = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({
                        "fecha": str(f_gasto), "concepto": tipo, "monto": int(monto), 
                        "cliente_id": u, "foto_comprobante": foto_b64
                    }).execute()
                    st.rerun()

    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><b>{row['fecha'].strftime('%d %b')}</b> | {row['concepto']} - ₡{row['monto']:,}</div>", unsafe_allow_html=True)
            if st.button("Borrar", key=f"del_{row['id']}", use_container_width=True):
                supabase.table("gastos").delete().eq("id", row['id']).execute(); st.rerun()

# --- TAB 3: DATOS (CON EXPORTACIÓN A LA DERECHA) ---
with tabs[2]:
    c_metrics, c_btn_excel, c_btn_pdf = st.columns([2, 1, 1])
    with c_metrics:
        st.metric("KM ACTUAL", f"{km_actual:,} KM")
        if not df_f.empty:
            st.metric(f"TOTAL {m_sel.upper()}", f"₡{df_f['monto'].sum():,}")
    
    if not df_f.empty:
        df_export = df_f[['fecha', 'concepto', 'monto']].copy()
        df_export['fecha'] = df_export['fecha'].dt.strftime('%Y-%m-%d')
        
        with c_btn_excel:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(label="EXCEL", data=df_export.to_csv(index=False).encode('utf-8'), 
                               file_name=f"Gastos_{u}.csv", mime="text/csv", use_container_width=True)
        with c_btn_pdf:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(label="PDF", data=df_export.to_string(), 
                               file_name=f"Reporte_{u}.txt", mime="text/plain", use_container_width=True)
        st.dataframe(df_export, hide_index=True, use_container_width=True)

# --- CIERRE DE APLICACIÓN CON LUCES NEÓN ---
st.markdown("<div class='neon-shield'>🛡️ AISAAC-SHIELD PROTECTED</div>", unsafe_allow_html=True)