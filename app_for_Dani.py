import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import base64
import os
from PIL import Image
import io
import plotly.express as px # <--- Nuevo motor para gráficos lindos

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

# --- 3. ESTILOS VISUALES MEJORADOS ---
u = st.session_state['user']
fondo_b64 = get_base64(st.secrets.get("APP_BACKGROUND_PATH"))

st.markdown(f"""
<style>
    [data-testid="stHeader"], .stDeployButton, footer {{ visibility: hidden; display: none !important; }}
    .stApp {{ background-color: #000; {f"background-image: url(data:image/png;base64,{fondo_b64});" if fondo_b64 else ""} background-size: cover; }}
    
    /* Contenedor Principal con Neón Sutil */
    [data-testid="stAppViewBlockContainer"] {{ 
        background-color: rgba(5, 5, 5, 0.95); 
        padding: 2.5rem; 
        border-radius: 30px; 
        border: 1px solid rgba(37, 211, 102, 0.4); 
        box-shadow: 0px 0px 40px rgba(37, 211, 102, 0.15); 
    }}
    
    /* Tarjetas de Gastos Estilo Premium */
    .gasto-card {{
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        padding: 20px;
        border-radius: 18px;
        border-left: 6px solid #25D366;
        margin-bottom: 15px;
        box-shadow: 4px 4px 15px rgba(0,0,0,0.3);
    }}
    
    .stButton>button {{ 
        width: 100%; 
        background: linear-gradient(90deg, #107C41, #25D366); 
        color: white; 
        border-radius: 15px; 
        font-weight: 900; 
        border: none; 
        height: 3.2rem;
        transition: 0.3s;
    }}
    .stButton>button:hover {{ transform: scale(1.02); }}
    
    h1, h2, h3, label, .stMetric {{ color: #25D366 !important; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='text-align: center;'>🚚 RUTAMASTER - {u.replace('_', ' ')}</h2>", unsafe_allow_html=True)

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
m_sel = st.selectbox("📅 Seleccione el periodo de visualización:", meses, index=datetime.now().month-1)

tabs = st.tabs(["📝 REGISTRO", "📉 GASTOS", "📊 DATOS"])

# --- TAB 1: REGISTRO ---
with tabs[0]:
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Concepto de Gasto", ["Diesel", "Peaje", "Aceite", "Repuesto", "Otros"])
        monto = col2.number_input("Monto en Colones", value=None, placeholder="Ingrese el monto...", step=500)
        km = st.number_input("Kilometraje Actual", value=None, placeholder="Ingrese los KM...", step=1)
        foto = st.file_uploader("📷 Subir Comprobante (Opcional)", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("GUARDAR Y SINCRONIZAR"):
            if monto and km:
                try:
                    f_bytes = procesar_foto(foto) if foto else None
                    supabase.table("gastos").insert({"fecha": str(datetime.now().date()), "concepto": tipo, "monto": monto, "cliente_id": u, "foto_comprobante": f_bytes}).execute()
                    supabase.table("viajes").insert({"fecha": str(datetime.now().date()), "km_actual": km, "cliente_id": u}).execute()
                    st.success("✅ Datos guardados con éxito")
                    st.balloons()
                except: st.error("Error al conectar con la nube")
            else: st.warning("Por favor complete todos los datos")

# --- TAB 2: GASTOS (DISEÑO DE TARJETAS LINDAS) ---
with tabs[1]:
    st.subheader(f"Movimientos Detallados: {m_sel}")
    try:
        rg = supabase.table("gastos").select("*").eq("cliente_id", u).execute()
        df_raw = pd.DataFrame(rg.data)
        if not df_raw.empty:
            df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
            df_f = df_raw[df_raw['fecha'].dt.month == (meses.index(m_sel)+1)].sort_values(by='fecha', ascending=False)
            
            if not df_f.empty:
                for i, row in df_f.iterrows():
                    # Tarjeta con diseño visual mejorado
                    st.markdown(f"""
                    <div class="gasto-card">
                        <div style='display: flex; justify-content: space-between;'>
                            <span style='color: #888; font-size: 0.85rem;'>{row['fecha'].strftime('%d de %B, %Y')}</span>
                        </div>
                        <div style='margin-top: 5px;'>
                            <span style='font-size: 1.15rem; font-weight: bold;'>{row['concepto']}</span><br>
                            <span style='color: #25D366; font-size: 1.4rem; font-weight: 900;'>CRC {row['monto']:,.0f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([0.5, 0.5])
                    if row.get('foto_comprobante'):
                        with c1.popover("📷 Ver Recibo", use_container_width=True):
                            st.image(f"data:image/jpeg;base64,{row['foto_comprobante']}", use_column_width=True)
                            st.caption("Toque fuera de la imagen para cerrar")
                    
                    if c2.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                        supabase.table("gastos").delete().eq("id", row['id']).execute()
                        st.rerun()
                    st.write("") # Espacio entre tarjetas
            else: st.info(f"No hay registros para {m_sel}")
    except: st.error("Error al cargar la lista de gastos")

# --- TAB 3: DATOS (GRÁFICO PROFESIONAL PLOTLY) ---
with tabs[2]:
    st.subheader("Análisis de Operación")
    try:
        # Kilometraje Actual
        rk = supabase.table("viajes").select("km_actual").eq("cliente_id", u).order("created_at", desc=True).limit(1).execute()
        kh = rk.data[0]['km_actual'] if rk.data else 0
        st.metric("KILOMETRAJE TOTAL FLOTA", f"{kh:,} KM")
        st.divider()
        
        if not df_f.empty:
            # Gasto Total
            total_mes = df_f['monto'].sum()
            st.metric(f"INVERSIÓN TOTAL EN {m_sel.upper()}", f"CRC {total_mes:,.0f}")
            
            # Gráfico de Plotly Interactivo
            st.write("📊 Distribución de Gastos")
            resumen = df_f.groupby('concepto')['monto'].sum().reset_index()
            
            fig = px.bar(resumen, x='concepto', y='monto', 
                         color='monto', 
                         color_continuous_scale=['#107C41', '#25D366'], # Degradado verde
                         labels={'monto': 'Monto (CRC)', 'concepto': 'Categoría'},
                         text_auto='.2s')
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color="#25D366",
                showlegend=False,
                xaxis={'title': ''},
                yaxis={'showticklabels': False, 'title': ''},
                margin=dict(l=10, r=10, t=10, b=10),
                height=300
            )
            fig.update_traces(marker_line_width=0, marker_color='#25D366')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            with st.expander("📂 Ver Detalles en Tabla"):
                st.dataframe(df_f[['fecha', 'concepto', 'monto']], hide_index=True, use_container_width=True)
    except: pass