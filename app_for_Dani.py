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

# --- 2. DISEÑO VISUAL GLOBAL ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH") if "APP_BACKGROUND_PATH" in st.secrets else None)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; border-left: 5px solid #25D366; margin-bottom: 10px; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; }}
    
    /* ESTILO PARA LOS LETREROS DE AISAAC-SHIELD */
    .shield-box {{ 
        margin: 20px 0; 
        padding: 15px; 
        text-align: center; 
        background: 
            linear-gradient(to right, #25D366 3px, transparent 3px) 0 0,
            linear-gradient(to bottom, #25D366 3px, transparent 3px) 0 0,
            linear-gradient(to left, #25D366 3px, transparent 3px) 100% 0,
            linear-gradient(to bottom, #25D366 3px, transparent 3px) 100% 0,
            linear-gradient(to right, #25D366 3px, transparent 3px) 0 100%,
            linear-gradient(to top, #25D366 3px, transparent 3px) 0 100%,
            linear-gradient(to left, #25D366 3px, transparent 3px) 100% 100%,
            linear-gradient(to top, #25D366 3px, transparent 3px) 100% 100%;
        background-repeat: no-repeat;
        background-size: 15px 15px;
        background-color: rgba(37, 211, 102, 0.05);
        border: 1px solid rgba(37, 211, 102, 0.1);
    }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN CON AVISO DE SEGURIDAD ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    
    # EL AVISO AL PRINCIPIO DE LA APP
    st.markdown("""
    <div class='shield-box'>
        <b style='color: #25D366;'>⚠️ AVISO DE SEGURIDAD</b><br>
        <small style='color: white;'>Esta aplicación está protegida por <b>Aisaac-Shield</b>.<br>
        El acceso no autorizado será registrado.</small>
    </div>
    """, unsafe_allow_html=True)

    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
    if st.button("ENTRAR"):
        if pin == "8715": st.session_state.update({'autenticado': True, 'user': "Dany"})
        elif pin == "8742": st.session_state.update({'autenticado': True, 'user': "Padre_Andres"})
        else: st.error("PIN Incorrecto")
        if st.session_state['autenticado']: st.rerun()
    st.stop()

# --- 4. CARGA DE DATOS ---
u = st.session_state['user']
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
hoy_cr_dt = datetime.now(ZONA_CR)
mes_actual_cr = hoy_cr_dt.month

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

with st.expander(f"📅 PERIODO: {st.session_state.get('mes_f', meses_nombres[mes_actual_cr-1])}", expanded=False):
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

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    opcion = st.radio("QUÉ REGISTRAMOS:", ["💸 Gasto Operativo", "🛣️ Finalizar Viaje"])
    hoy_cr = hoy_cr_dt.date()
    
    if opcion == "💸 Gasto Operativo":
        with st.form("f_gasto", clear_on_submit=True):
            fecha = st.date_input("Fecha", hoy_cr)
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
            monto = c2.number_input("Monto (CRC)", value=None, step=500)
            foto = st.file_uploader("Foto", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("GUARDAR GASTO"):
                if monto:
                    supabase.table("gastos").insert({"fecha": str(fecha), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": procesar_foto(foto) if foto else None}).execute()
                    st.success("✅ Guardado"); time.sleep(1); st.rerun()
                    
    elif opcion == "🛣️ Finalizar Viaje":
        with st.form("f_viaje", clear_on_submit=True):
            fecha = st.date_input("Fecha", hoy_cr)
            cli = st.text_input("Cliente")
            c1, c2 = st.columns(2)
            orig = c1.text_input("Origen")
            dest = c2.text_input("Destino")
            c3, c4 = st.columns(2)
            cost = c3.number_input("Costo (CRC)", value=None)
            km = c4.number_input("KM Actual", value=None, placeholder=f"Llevas: {km_actual}")
            if st.form_submit_button("GUARDAR VIAJE"):
                if km and orig and dest:
                    supabase.table("viajes").insert({"fecha": str(fecha), "cliente": cli, "origen": orig, "destino": dest, "monto": cost, "cliente_id": u, "km_actual": km}).execute()
                    st.success("✅ Viaje Registrado"); st.balloons(); time.sleep(1.5); st.rerun()

# --- TAB 2: GASTOS ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><small>{row['fecha'].strftime('%d %b')}</small><br><b>{row['concepto']}</b><br><span style='color:#25D366;'>CRC {row['monto']:,.0f}</span></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if row.get('foto_comprobante'):
                with c1.popover("📷 Foto"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if c2.button("🗑️ Borrar", key=f"d_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute(); st.rerun()
    else: st.info("Sin gastos.")

# --- TAB 3: DATOS ---
with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL", f"{km_actual:,} KM")
    st.divider()
    
    if not df_f.empty:
        st.metric(f"TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        
        # Gráfico de Dona
        df_pie = df_f.groupby('concepto')['monto'].sum().reset_index()
        fig = px.pie(df_pie, values='monto', names='concepto', hole=0.5, 
                     color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', legend_font_color="#25D366", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Tabla de Gastos
        st.subheader("📋 Resumen del Mes")
        df_tabla = df_f[['fecha', 'concepto', 'monto']].copy()
        df_tabla['fecha'] = df_tabla['fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_tabla, hide_index=True, use_container_width=True)
    else:
        st.info("No hay datos este mes.")

    # EL SELLO DE ABAJO (También con esquinas)
    st.markdown("""
    <div class='shield-box'>
        <span style='color: #25D366; font-weight: 900; letter-spacing: 1px;'>🛡️ AISAAC-SHIELD ACTIVATED</span><br>
        <small style='color: #A0A0A0;'>Licencia Verificada para RutaMaster</small>
    </div>
    """, unsafe_allow_html=True)