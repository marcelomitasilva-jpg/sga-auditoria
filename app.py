import streamlit as st
import google.generativeai as genai
import sqlite3
import pandas as pd
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SGA Pro v65.0", layout="wide", page_icon="🛡️")

# --- 2. CONEXIÓN A LA IA (SEGURA) ---
ia_conectada = False
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        ia_conectada = True
    except Exception as e:
        st.sidebar.error(f"Error de Configuración IA: {e}")

# --- 3. BASE DE DATOS LOCAL ---
def conectar():
    return sqlite3.connect('sga_sistema_v65.db', check_same_thread=False)

def inicializar_db():
    conn = conectar()
    c = conn.cursor()
    # Tabla de Auditoría (Escáner)
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)''')
    # Tabla de Personal
    c.execute('''CREATE TABLE IF NOT EXISTS personal 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)''')
    # Tabla de Vales (Comillas revisadas y corregidas)
    c.execute('''CREATE TABLE IF NOT EXISTS vales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)''')
    conn.commit()
    conn.close()

inicializar_db()

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛡️ SGA BOLIVIA")
    if ia_conectada:
        st.success("✅ IA Conectada (v1)")
    else:
        st.error("❌ IA Desconectada")
    
    menu = st.radio("MÓDULOS DEL SISTEMA:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "📖 5. Libro Diario Central"
    ])
    st.caption("Marcelo | Gestión 2026")

# --- 5. LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    try:
        conn = conectar()
        col1, col2 = st.columns(2)
        with col1:
            total_socios = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conn).iloc[0]['t']
            st.metric("Socios Registrados", total_socios)
        with col2:
            total_bs = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conn).iloc[0]['t']
            st.metric("Producción Total (Bs)", f"{total_bs or 0:,.2f}")
        conn.close()
    except:
        st.info("Inicia el registro de datos para ver estadísticas.")

elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Socios y Personal")
    with st.form("form_personal"):
        nombre = st.text_input("Nombre Completo").upper()
        ci = st.text_input("Cédula de Identidad (CI)")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Contador", "Seguridad"])
        if st.form_submit_button("Guardar Socio"):
            if nombre and ci:
                try:
                    conn = conectar()
                    conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (nombre, ci, cargo))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {nombre} registrado correctamente.")
                except:
                    st.error("Error: El CI ya existe en la base de datos.")
            else:
                st.warning("Por favor completa los campos.")
    
    st.subheader("Lista de Personal")
    df_p = pd.read_sql_query("SELECT nombre, ci, cargo FROM personal", conectar())
    st.dataframe(df_p, use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos")
    st.info("Sube una foto clara del cuaderno de notas para procesar los datos automáticamente.")
    
    archivo = st.file_uploader("Seleccionar imagen...", type=['png', 'jpg', 'jpeg'])
    
    if archivo:
        img = Image.open(archivo)
        st.image(img, caption="Imagen cargada", width=500)
        
        if st.button("🚀 PROCESAR Y GUARDAR"):
            if not ia_conectada:
                st.error("La IA no está configurada. Revisa tus Secrets.")
            else:
                with st.spinner("Analizando con Inteligencia Artificial..."):
                    try:
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG')
                        
                        instruccion = "Extract the table from the image. Return ONLY a JSON list of objects with keys: fecha, tujo, mina, bs, obs. Do not include markdown formatting or extra text."
                        
                        # Parche explícito v1 para evitar el error 404
                        from google.generativeai.types import RequestOptions
                        response = model.generate_content(
                            contents=[instruccion, {'mime_type': 'image/jpeg', 'data': img_byte_arr.getvalue()}],
                            request_options=RequestOptions(api_version='v1')
                        )
                        
                        texto_limpio = re.search(r'\[.*\]', response.text, re.DOTALL).group()
                        datos_df = pd.read_json(io.StringIO(texto_limpio))
                        
                        conn = conectar()
                        datos_df.to_sql('auditoria', conn, if_exists='append', index=False)
                        conn.close()
                        
                        st.success(f"✅ Se han procesado y guardado {len(datos_df)} filas.")
                        st.dataframe(datos_df)
                    except Exception as e:
                        st.error(f"Error al procesar: {e}")

elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Registro de Vales")
    with st.form("form_vales"):
        res_p = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        lista_socios = res_p['nombre'].tolist() if not res_p.empty else ["No hay socios registrados"]
        socio = st.selectbox("Seleccionar Socio", lista_socios)
        monto = st.number_input("Monto en Bs", min_value=0.0)
        fecha = st.date_input("Fecha del Vale")
        concepto = st.text_input("Concepto (ej: Adelanto, Repuestos)")
        if st.form_submit_button("Registrar Vale"):
            if socio != "No hay socios registrados":
                conn = conectar()
                # CORREGIDO: Sintaxis limpia y blindada en la inserción de vales
                conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (socio, monto, str(fecha), concepto))
                conn.commit()
                conn.close()
                st.success("Vale registrado con éxito.")
            else:
                st.error("No puedes registrar un vale sin un socio válido.")

elif menu == "📖 5. Libro Diario Central":
    st.title("📖 Libro Diario Central")
    st.subheader("Registros del Escáner (Auditoría)")
    df_aud = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df_aud, use_container_width=True)
    
    st.subheader("Registros de Vales")
    df_val = pd.read_sql_query("SELECT * FROM vales", conectar())
    st.dataframe(df_val, use_container_width=True)
