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

# --- 2. DISEÑO VISUAL GLOBAL ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH") if "APP_BACKGROUND_PATH" in st.secrets else None)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2.5rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border-left: 6px solid #25D366; margin-bottom: 15px; border-right: 1px solid rgba(37, 211, 102, 0.2); }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; }}
    /* Ajuste para que el segmented control se vea bien en móvil */
    div[data-testid="stHorizontalBlock"] {{ overflow-x: auto; }}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN ---
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

# --- 4. CARGA DE DATOS Y NAVEGACIÓN DESPLEGABLE ---
u = st.session_state['user']
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

# CREAMOS EL DESPLEGABLE QUE NO ACTIVA EL TECLADO
with st.expander(f" {st.session_state.get('mes_f', meses_nombres[datetime.now().month-1])}", expanded=False):
    m_sel = st.segmented_control(
        "Seleccione el mes para ver los datos:", 
        options=meses_nombres, 
        default=meses_nombres[datetime.now().month-1],
        label_visibility="collapsed",
        key="mes_f" # Guardamos la elección en el estado
    )
    st.write("*(Gracias por trabajar con nosotros )*")

# CARGA DE DATOS CENTRALIZADA
df_f = pd.DataFrame()
km_actual = 0
try:
    rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
    if rg.data:
        df_raw = pd.DataFrame(rg.data)
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        # Filtramos por el mes que el usuario tocó en el desplegable
        df_f = df_raw[df_raw['fecha'].dt.month == (meses_nombres.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
    
    rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("id", desc=True).limit(1).execute()
    km_actual = rk.data[0]['km_actual'] if rk.data else 0
except: pass

# --- PESTAÑAS DE TRABAJO ---
tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO SEPARADO ---
with tabs[0]:
    opcion_registro = st.radio("SELECCIONE QUÉ DESEA REGISTRAR:", ["💸 Gasto Operativo", "🛣️ Finalizar Viaje"])
    st.write("")
    
    if opcion_registro == "💸 Gasto Operativo":
        with st.form("f_gasto", clear_on_submit=True):
            st.subheader("Registrar Gasto de Ruta")
            fecha_gasto = st.date_input("📅 Fecha Inteligente", datetime.now().date())
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
            monto = c2.number_input("Monto (CRC)", value=None, placeholder="0", step=500)
            foto = st.file_uploader("📁 Buscar imagen en galería", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("GUARDAR GASTO"):
                if monto:
                    f_bytes = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({"fecha": str(fecha_gasto), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": f_bytes}).execute()
                    st.success("✅ Gasto guardado")
                    st.rerun()
                else: st.warning("Ingrese un Monto.")
                    
    elif opcion_registro == "🛣️ Finalizar Viaje":
        with st.form("f_viaje", clear_on_submit=True):
            st.subheader("Reporte de Viaje Realizado")
            fecha_viaje = st.date_input("📅 Fecha Inteligente", datetime.now().date())
            cliente = st.text_input("👤 Cliente / Empresa")
            c3, c4 = st.columns(2)
            origen = c3.text_input("📍 Origen")
            destino = c4.text_input("🏁 Destino")
            c5, c6 = st.columns(2)
            costo_viaje = c5.number_input("💰 Costo (CRC)", value=None, step=500)
            km = c6.number_input("🚗 KM Actual", value=None, placeholder=f"Último: {km_actual}", step=1)
            notas = st.text_area("📝 Notas")
            if st.form_submit_button("GUARDAR VIAJE"):
                if km and origen and destino:
                    supabase.table("viajes").insert({"fecha": str(fecha_viaje), "cliente": cliente, "origen": origen, "destino": destino, "monto": costo_viaje, "notas": notas, "cliente_id": u, "km_actual": km}).execute()
                    st.success("✅ Viaje guardado")
                    st.balloons()
                    st.rerun()
                else: st.warning("Complete Origen, Destino y KM.")

# --- TAB 2: GASTOS ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><small>{row['fecha'].strftime('%d %b, %Y')}</small><br><b>{row['concepto']}</b><br><span style='color:#25D366; font-size:1.5rem; font-weight:900;'>CRC {row['monto']:,.0f}</span></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if row.get('foto_comprobante'):
                with c1.popover("📷 Ver Ticket", use_container_width=True):
                    st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if c2.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute()
                st.rerun()
    else: st.info(f"No hay gastos en {m_sel}")

# --- TAB 3: DATOS ---
with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL FLOTA", f"{km_actual:,} KM")
    if not df_f.empty:
        st.metric(f"INVERSIÓN TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        fig = px.bar(df_f.groupby('concepto')['monto'].sum().reset_index(), x='concepto', y='monto', color='monto', color_continuous_scale='Greens')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#25D366")
        st.plotly_chart(fig, use_container_width=True)