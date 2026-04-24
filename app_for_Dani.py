import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io
import plotly.express as px # <--- Motor de gráficos premium

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

# --- 3. ESTILOS CSS PARA "CARDS" LINDAS ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(10, 10, 10, 0.94); padding: 2rem; border-radius: 25px; border: 1px solid #25D366; box-shadow: 0px 0px 25px rgba(37, 211, 102, 0.2); }}
    
    /* Estilo de Tarjeta para Gastos */
    .gasto-card {{
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 15px;
        border-left: 5px solid #25D366;
        margin-bottom: 10px;
    }}
    
    .stButton>button {{ width: 100%; background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; height: 3rem; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
m_sel = st.selectbox("📅 Seleccionar periodo:", meses, index=datetime.now().month-1)

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = col2.number_input("Monto (CRC)", value=None, placeholder="0", step=500)
        km = st.number_input("Kilometraje Actual", value=None, placeholder="0", step=1)
        foto = st.file_uploader("📷 Foto del Comprobante", type=['jpg', 'png', 'jpeg'])
        if st.form_submit_button("SINCRONIZAR DATOS"):
            if monto and km:
                try:
                    f_bytes = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": f_bytes}).execute()
                    supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                    st.success("✅ Sincronizado")
                except: st.error("Error al guardar")
            else: st.warning("Completa los campos")

# --- TAB 2: GASTOS (LISTA MÁS LINDA) ---
with tabs[1]:
    st.subheader(f"Movimientos de {m_sel}")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df_raw = pd.DataFrame(rg.data)
        if not df_raw.empty:
            df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
            df_f = df_raw[df_raw['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                for i, row in df_f.iterrows():
                    # Contenedor tipo tarjeta
                    with st.container():
                        st.markdown(f"""
                        <div class="gasto-card">
                            <span style='font-size: 0.8rem; color: #888;'>{row['fecha'].strftime('%d de %B, %Y')}</span><br>
                            <b style='font-size: 1.1rem;'>{row['concepto']}</b><br>
                            <span style='color: #25D366; font-size: 1.2rem; font-family: monospace;'>CRC {row['monto']:,.0f}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns([0.5, 0.5])
                        if row.get('foto_comprobante'):
                            with c1.popover("📷 Ver Ticket", use_container_width=True):
                                st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                        if c2.button("🗑️ Borrar", key=f"del_{row['id']}"):
                            supabase.table("gastos").delete().eq("id", row['id']).execute()
                            st.rerun()
                        st.write("") # Espacio entre tarjetas
            else: st.info(f"No hay registros en {m_sel}")
    except: st.error("Error cargando gastos")

# --- TAB 3: DATOS (GRÁFICO PROFESIONAL PLOTLY) ---
with tabs[2]:
    st.subheader("Análisis de Operación")
    try:
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("Kilometraje Actual Flota", f"{kh:,} km")
        st.divider()
        
        if not df_f.empty:
            st.metric(f"Total Invertido en {m_sel}", f"CRC {df_f['monto'].sum():,.0f}")
            
            # Gráfico de Plotly mucho más lindo
            st.write("📊 Distribución de Gastos")
            resumen = df_f.groupby('concepto')['monto'].sum().reset_index()
            fig = px.bar(resumen, x='concepto', y='monto', 
                         color='monto', 
                         color_continuous_scale='Greens',
                         text_auto='.2s',
                         labels={'monto': 'Monto (CRC)', 'concepto': 'Categoría'})
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#25D366",
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Ver Tabla Detallada"):
                st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
    except: pass