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

# --- 0. CONFIGURACIÓN Y ZONA HORARIA ---
st.set_page_config(page_title="RutaMaster - Dani", layout="centered")
ZONA_CR = timezone(timedelta(hours=-6)) # Hora exacta de Costa Rica

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

# --- 2. DISEÑO VISUAL CON LUCES ANIMADAS ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; border-left: 5px solid #25D366; margin-bottom: 10px; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; }}
    
    /* ANIMACIÓN DE PULSO DE NEÓN */
    @keyframes neon-pulse {{
        0% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
        50% {{ border-color: rgba(37, 211, 102, 1); box-shadow: 0 0 20px rgba(37, 211, 102, 0.5); }}
        100% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
    }}

    .shield-box {{ 
        margin: 20px 0; padding: 20px; text-align: center; border: 2px solid #25D366; animation: neon-pulse 2s infinite ease-in-out;
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
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN CON AVISO ANIMADO ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    st.markdown("""<div class='shield-box'><b style='color: #25D366; font-size: 1.2rem;'>⚠️ AVISO DE SEGURIDAD</b><br><span style='color: white;'>Esta aplicación está protegida por <b>Aisaac-Shield</b>.</span><br><small style='color: #25D366;'>Acceso restringido y monitoreado.</small></div>""", unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "padre_andres"})
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. DATA ENGINE ---
u = st.session_state['user']
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy_cr = datetime.now(ZONA_CR)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.upper()}</h2>", unsafe_allow_html=True)
with st.expander(f"📅 PERIODO: {st.session_state.get('m_sel', meses[hoy_cr.month-1])}"):
    m_sel = st.segmented_control("Mes", options=meses, default=meses[hoy_cr.month-1], key="m_sel")

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
    op = st.radio("QUÉ REGISTRAMOS:", ["💸 Gasto Operativo", "🛣️ Finalizar Viaje"])
    if op == "💸 Gasto Operativo":
        with st.form("f_g", clear_on_submit=True):
            f = st.date_input("Fecha", hoy_cr.date())
            tipo = st.selectbox("Tipo", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
            monto = st.number_input("Monto (CRC)", value=None, step=500)
            foto = st.file_uploader("Ticket", type=['jpg','png','jpeg'])
            if st.form_submit_button("GUARDAR GASTO"):
                if monto:
                    supabase.table("gastos").insert({"fecha": str(f), "concepto": tipo, "monto": int(monto), "cliente_id": u, "foto_comprobante": procesar_foto(foto) if foto else None}).execute()
                    st.success("✅ Guardado"); time.sleep(1); st.rerun()
    else:
        with st.form("f_v", clear_on_submit=True):
            f = st.date_input("Fecha", hoy_cr.date())
            c1, c2 = st.columns(2); o = c1.text_input("Origen"); d = c2.text_input("Destino")
            km = st.number_input("KM Llegada", value=None, placeholder=f"Último: {km_actual}")
            cost = st.number_input("Costo Viaje", value=None)
            if st.form_submit_button("FINALIZAR VIAJE"):
                if km and o and d:
                    # Guardado forzando números enteros
                    supabase.table("viajes").insert({"fecha": str(f), "origen": o, "destino": d, "monto": int(cost) if cost else 0, "cliente_id": u, "km_actual": int(km)}).execute()
                    st.success("✅ Viaje Registrado"); st.balloons(); time.sleep(1.5); st.rerun()

# --- TAB 2 Y 3: VISUALIZACIÓN ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><small>{row['fecha'].strftime('%d/%m')}</small><br><b>{row['concepto']}</b><br><span style='color:#25D366;'>CRC {row['monto']:,.0f}</span></div>", unsafe_allow_html=True)
            if row.get('foto_comprobante'):
                with st.popover("📷"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if st.button("🗑️", key=f"d_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute(); st.rerun()
    else: st.info("Sin registros.")

with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL", f"{km_actual:,} KM")
    if not df_f.empty:
        st.metric(f"TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        # Gráfico redondo (Dona)
        fig = px.pie(df_f.groupby('concepto')['monto'].sum().reset_index(), values='monto', names='concepto', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', legend_font_color="#25D366", margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
    
    # SELLO INFERIOR ANIMADO
    st.markdown("<div class='shield-box'><span style='color: #25D366; font-weight: 900;'>🛡️ AISAAC-SHIELD ACTIVATED</span></div>", unsafe_allow_html=True)