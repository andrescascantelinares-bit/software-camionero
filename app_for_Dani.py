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
ZONA_CR = timezone(timedelta(hours=-6)) # Ajuste estricto para Costa Rica

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

# --- 2. DISEÑO VISUAL CON LUCES DE NEÓN ANIMADAS ---
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH") if "APP_BACKGROUND_PATH" in st.secrets else None)

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000 !important; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    [data-testid="stAppViewBlockContainer"] {{ background-color: rgba(5, 5, 5, 0.95); padding: 2rem; border-radius: 30px; border: 1px solid #25D366; }}
    .gasto-card {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; border-left: 5px solid #25D366; margin-bottom: 10px; }}
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
    .stButton>button {{ background: linear-gradient(90deg, #107C41, #25D366); color: white; border-radius: 12px; font-weight: bold; border: none; }}
    
    /* ANIMACIÓN DE PULSO DE NEÓN AISAAC-SHIELD */
    @keyframes neon-glow {{
        0% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
        50% {{ border-color: rgba(37, 211, 102, 1); box-shadow: 0 0 20px rgba(37, 211, 102, 0.6); }}
        100% {{ border-color: rgba(37, 211, 102, 0.3); box-shadow: 0 0 5px rgba(37, 211, 102, 0.2); }}
    }}

    .shield-box {{ 
        margin: 20px 0; padding: 20px; text-align: center; border: 2px solid #25D366;
        animation: neon-glow 2s infinite ease-in-out;
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

# --- 3. LOGIN CON AVISO DE SEGURIDAD ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #25D366;'>🚚 RUTAMASTER</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='shield-box'>
        <b style='color: #25D366; font-size: 1.1rem;'>⚠️ AVISO DE SEGURIDAD</b><br>
        <span style='color: white;'>Esta aplicación está protegida por <b>Aisaac-Shield</b>.</span><br>
        <small style='color: #25D366;'>El acceso no autorizado será registrado.</small>
    </div>
    """, unsafe_allow_html=True)
    pin = st.text_input("PIN DE ACCESO", type="password", placeholder="****")
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

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.upper()}</h2>", unsafe_allow_html=True)

# Filtro desplegable para evitar el teclado en móviles
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

# --- TAB 1: REGISTRO (Ahora enfocada en Viajes) ---
with tabs[0]:
    st.markdown("### Finalizar Viaje")
    with st.form("f_viaje", clear_on_submit=True):
        fecha = st.date_input("Fecha", hoy_cr_dt.date())
        cli = st.text_input("Cliente / Empresa")
        
        c3, c4 = st.columns(2)
        orig = c3.text_input("Origen")
        dest = c4.text_input("Destino")
        
        c5, c6 = st.columns(2)
        cost = c5.number_input("Costo del Viaje (CRC)", min_value=0, step=1000)
        km = c6.number_input("Kilometraje de Llegada", min_value=km_actual, step=1, placeholder=f"Actual: {km_actual}")
        
        if st.form_submit_button("REGISTRAR VIAJE"):
            if cli and orig and dest and km > 0:
                try:
                    supabase.table("viajes").insert({
                        "fecha": str(fecha), "cliente": cli, "origen": orig, "destino": dest, 
                        "monto": int(cost) if cost else 0, "cliente_id": u, "km_actual": int(km)
                    }).execute()
                    st.success("Viaje registrado con éxito")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Completa los datos del viaje.")

# --- TAB 2: GASTOS (Registro y Visualización) ---
with tabs[1]:
    # Sección para agregar nuevo gasto arriba
    with st.expander("AGREGAR NUEVO GASTO", expanded=False):
        with st.form("f_gasto_rapido", clear_on_submit=True):
            f_gasto = st.date_input("Fecha", hoy_cr_dt.date())
            tipo = st.selectbox("Concepto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
            monto = st.number_input("Monto (CRC)", min_value=0, step=500)
            foto = st.file_uploader("Comprobante", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("GUARDAR GASTO"):
                if monto > 0:
                    foto_b64 = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({
                        "fecha": str(f_gasto), "concepto": tipo, "monto": int(monto), 
                        "cliente_id": u, "foto_comprobante": foto_b64
                    }).execute()
                    st.success("Gasto guardado")
                    time.sleep(1)
                    st.rerun()

    st.divider()

    # Visualización de gastos existentes
    if not df_f.empty:
        for i, row in df_f.iterrows():
            with st.container():
                st.markdown(f"""
                <div class='gasto-card'>
                    <small>{row['fecha'].strftime('%d %b')}</small><br>
                    <b>{row['concepto']}</b><br>
                    <span style='color:#25D366; font-size:1.2rem;'>CRC {row['monto']:,.0f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns([1, 1])
                if row.get('foto_comprobante'):
                    with col_btn1:
                        with st.popover("📷 Ver"): 
                            st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
                with col_btn2:
                    if st.button("Borrar", key=f"del_{row['id']}"):
                        supabase.table("gastos").delete().eq("id", row['id']).execute()
                        st.rerun()
    else:
        st.info(f"No hay gastos registrados en {m_sel}.")
# --- TAB 2: GASTOS ---
with tabs[1]:
    if not df_f.empty:
        for i, row in df_f.iterrows():
            st.markdown(f"<div class='gasto-card'><small>{row['fecha'].strftime('%d %b')}</small><br><b>{row['concepto']}</b><br><span style='color:#25D366; font-size:1.2rem;'>CRC {row['monto']:,.0f}</span></div>", unsafe_allow_html=True)
            if row.get('foto_comprobante'):
                with st.popover("📷 Ver Ticket"): st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}")
            if st.button("🗑️ Borrar", key=f"d_{row['id']}"):
                supabase.table("gastos").delete().eq("id", row['id']).execute(); st.rerun()
    else: st.info("Sin registros.")

# --- TAB 3: DATOS ---
with tabs[2]:
    st.metric("KILOMETRAJE ACTUAL", f"{km_actual:,} KM")
    st.divider()
    
    if not df_f.empty:
        st.metric(f"TOTAL {m_sel.upper()}", f"CRC {df_f['monto'].sum():,.0f}")
        
        # Gráfico redondo tipo Dona
        fig = px.pie(df_f.groupby('concepto')['monto'].sum().reset_index(), 
                     values='monto', names='concepto', hole=0.5, 
                     color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', legend_font_color="#25D366", margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Resumen de Gastos")
        df_tabla = df_f[['fecha', 'concepto', 'monto']].copy()
        df_tabla['fecha'] = df_tabla['fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_tabla, hide_index=True, use_container_width=True)
    
    # SELLO INFERIOR SIEMPRE VISIBLE
    st.markdown("""
    <div class='shield-box'>
        <span style='color: #25D366; font-weight: 900; letter-spacing: 1px;'>🛡️ AISAAC-SHIELD ACTIVATED</span><br>
        <small style='color: #A0A0A0;'>Sistema de Protección de Datos en Tiempo Real</small>
    </div>
    """, unsafe_allow_html=True)