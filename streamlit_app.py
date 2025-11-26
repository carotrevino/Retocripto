# streamlit_app.py
import streamlit as st
import pandas as pd
import os
import secrets
from datetime import datetime, date
from app_core import (
    USERS, verify_password, make_user,
    lista_estudios, list_folios, get_order_summary,
    save_order, save_results, read_csv, decrypt_view, filter_df, export_excel
)

# Detectar logo en la raíz y usarlo como page_icon si existe
logo_path = None
for _name in ("logo.png", "logo.jpg", "logo.jpeg"):
    if os.path.exists(_name):
        logo_path = _name
        break

st.set_page_config(page_title="LABZA | Laboratorio de Análisis Clínicos", page_icon=logo_path or None, layout="wide")

# --- Auth (simple en memoria) ---
if "user" not in st.session_state:
    st.session_state.user = None

def login_view():
    # Mostrar sólo el encabezado con el logo; no duplicar aquí.
    st.subheader("Iniciar sesión")
    email = st.text_input("Correo", value="recep@lab.local")
    pwd   = st.text_input("Contraseña", type="password", value="recep123")
    if st.button("Entrar", type="primary"):
        rec = USERS.get(email)
        if rec and verify_password(pwd, rec["salt"], rec["hash"]):
            st.session_state.user = {"email": email, "role": rec["role"]}
            st.success(f"Bienvenida/o: {email} — rol: {rec['role']}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

def logout_button():
    st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update(user=None))
    if st.session_state.user:
        st.sidebar.success(f"👋 {st.session_state.user['email']} ({st.session_state.user['role']})")

# --- Layout principal ---
if logo_path:
    hcol1, hcol2 = st.columns([1, 8])
    with hcol1:
        st.image(logo_path, width=96)
    with hcol2:
        st.markdown("## LABZA | Laboratorio de Análisis Clínicos")
else:
    st.title("LABZA | Laboratorio de Análisis Clínicos")

if not st.session_state.user:
    login_view()
    st.stop()
else:
    logout_button()

# Tabs por rol
tabs = st.tabs(["Recepción", "Laboratorio", "Consultas/Reportes", "Admin"])

# ========== Recepción ==========
with tabs[0]:
    if st.session_state.user["role"] not in ("recepcion", "admin"):
        st.info("No tienes permisos para esta sección.")
    else:
        st.subheader("➕ Alta de paciente / solicitud")
        with st.form("form_recepcion", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                from app_core import folio_auto
                if "folio_actual" not in st.session_state:
                    st.session_state["folio_actual"] = folio_auto()
                folio = st.text_input("Folio (auto)", value=st.session_state["folio_actual"], disabled=True)
                fecha_prog = st.date_input("Fecha programada", value=date.today())
                costo = st.number_input("Costo (MXN)", min_value=0.0, step=50.0)
            with col2:
                nombre = st.text_input("Nombre del paciente")
                edad   = st.number_input("Edad", min_value=0, max_value=120, step=1)
                genero = st.selectbox("Género", ["F","M","Otro","No especifica"])
            with col3:
                telefono   = st.text_input("Teléfono")
                direccion  = st.text_input("Dirección")
                emails_raw = st.text_area("Correos electrónicos (uno por línea o separados por coma)")
                tipo       = st.multiselect("Estudios", lista_estudios(), default=[])
            auto_cost = st.checkbox("Calcular costo automático desde catálogo")
            observaciones = st.text_area("Observaciones", height=90)
            submitted = st.form_submit_button("Guardar paciente + solicitud")
        if submitted:
            try:
                # Si el checkbox está activo, ignoramos costo manual
                if auto_cost:
                    from app_core import costo_total_desde_catalogo
                    costo = costo_total_desde_catalogo(tipo)
                # Procesar emails
                if emails_raw:
                    emails = [e.strip() for e in emails_raw.replace("\n", ",").split(",") if e.strip()]
                else:
                    emails = []
                folio_final = save_order(
                    folio, str(fecha_prog), costo, nombre, edad, genero, telefono, direccion, tipo, observaciones, emails
                )
                st.success(f"Guardado folio: {folio_final}")
                # Generar nuevo folio para el siguiente paciente
                from app_core import folio_auto
                st.session_state["folio_actual"] = folio_auto()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ========== Laboratorio ==========
with tabs[1]:
    if st.session_state.user["role"] not in ("lab","medico","admin"):
        st.info("No tienes permisos para esta sección.")
    else:
        st.subheader("🧪 Captura de resultados")
        cols = st.columns([2,1])
        with cols[0]:
            folios = list_folios()  # puedes filtrar por estado si deseas
            folio_sel = st.selectbox("Selecciona folio", ["—"] + folios, index=0)
            if st.button("Cargar orden"):
                st.session_state["folio_loaded"] = folio_sel if folio_sel != "—" else None

            folio_loaded = st.session_state.get("folio_loaded")
            if folio_loaded:
                info = get_order_summary(folio_loaded)
                if info:
                    st.markdown(f"**Paciente:** {info['Nombre']} — **Estado:** {info['Estado']}")
                    st.markdown(f"**Estudios:** {info['Tipo_Estudio']}")
                else:
                    st.warning("Folio no encontrado")
        with cols[1]:
            st.write(" ")
            
        # Opciones de descargar/subir formato PDF de resultados
        st.markdown("---")
        st.subheader("📄 Formato de Resultados (PDF)")
        pdf_cols = st.columns([2, 2, 2])
        
        # Botón descargar formato
        with pdf_cols[0]:
            if os.path.exists("Formato Resultados.pdf"):
                with open("Formato Resultados.pdf", "rb") as f:
                    st.download_button(
                        label="📥 Descargar Formato",
                        data=f.read(),
                        file_name="Formato Resultados.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("Archivo de formato no disponible")
        
        # Uploader para cargar PDF completado
        with pdf_cols[1]:
            pdf_file = st.file_uploader("📤 Cargar PDF de resultados", type=["pdf"], key="pdf_uploader")
            if pdf_file is not None and st.session_state.get("folio_loaded"):
                if st.button("Guardar PDF", key="save_pdf_btn"):
                    try:
                        os.makedirs("resultados_pdf", exist_ok=True)
                        folio_loaded = st.session_state.get("folio_loaded")
                        pdf_path = os.path.join("resultados_pdf", f"{folio_loaded}.pdf")
                        with open(pdf_path, "wb") as f:
                            f.write(pdf_file.getbuffer())
                        st.success(f"PDF guardado para folio {folio_loaded}")
                    except Exception as e:
                        st.error(f"Error al guardar PDF: {e}")
            elif pdf_file is not None and not st.session_state.get("folio_loaded"):
                st.warning("Carga primero un folio para asociar el PDF")
        
        # Mostrar PDF cargado si existe
        with pdf_cols[2]:
            folio_loaded = st.session_state.get("folio_loaded")
            if folio_loaded:
                pdf_path = os.path.join("resultados_pdf", f"{folio_loaded}.pdf")
                if os.path.exists(pdf_path):
                    st.success("✅ PDF cargado para este folio")
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📥 Descargar PDF guardado",
                            data=f.read(),
                            file_name=f"{folio_loaded}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.info("No hay PDF cargado para este folio")
        
        st.markdown("---")

        resultados = st.text_area("Resultados (texto o JSON)", height=200, placeholder='{"glucosa": 90, "obs":"ayuno 8h"}')
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Guardar resultados"):
                try:
                    ok = save_results(st.session_state.get("folio_loaded",""), resultados, liberar=False)
                    if ok: st.success("Resultados guardados (estado: capturado)")
                except Exception as e:
                    st.error(f"Error: {e}")
        with c2:
            if st.button("Firmar y liberar"):
                try:
                    ok = save_results(st.session_state.get("folio_loaded",""), resultados, liberar=True)
                    if ok: st.success("Orden firmada (estado: firmado)")
                except Exception as e:
                    st.error(f"Error: {e}")

# ========== Consultas / Reportes ==========
with tabs[2]:
    st.subheader("🔎 Búsqueda y exportación")
    q = st.text_input("Buscar por nombre, folio u otro campo")
    df = decrypt_view(read_csv())
    df_f = filter_df(df, q) if q else df
    st.dataframe(df_f, use_container_width=True, height=300)
    if st.button("Exportar a Excel"):
        path, msg = export_excel(df_f)
        st.success(f"{msg}. Archivo: {path}")

# ========== Admin ==========
with tabs[3]:
    if st.session_state.user["role"] != "admin":
        st.info("Solo admin puede gestionar usuarios.")
    else:
        st.subheader("👤 Gestión de usuarios (demo en memoria)")
        with st.form("form_new_user"):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Nombre (solo referencia local)")
            with col2:
                email = st.text_input("Correo")
            with col3:
                role = st.selectbox("Rol", ["recepcion","lab","medico","admin"])
            pwd = st.text_input("Contraseña", type="password")
            submitted_u = st.form_submit_button("Crear/Actualizar usuario")
        if submitted_u:
            if email and pwd and role:
                USERS[email] = make_user(pwd, role)
                st.success(f"Usuario {email} creado/actualizado")
            else:
                st.error("Completa correo, rol y contraseña")

        # Tabla simple: mostrar email y permitir establecer/crear contraseña
        st.markdown("**Usuarios actuales (solo memoria de ejecución):**")
        users = sorted(USERS.keys())
        if users:
            for u in users:
                safe = u.replace("@","_at_").replace(".","_")
                cols = st.columns([3,2,6])
                cols[0].markdown(f"**{u}**")
                # Mostrar rol en pequeño para referencia
                cols[1].markdown(f"{USERS[u]['role']}")
                with cols[2]:
                    pwd_in = st.text_input("Nueva contraseña", type="password", key=f"pwd_in_{safe}")
                    pwd_conf = st.text_input("Confirmar contraseña", type="password", key=f"pwd_conf_{safe}")
                    set_key = f"set_{safe}"
                    gen_key = f"gen_{safe}"
                    c1, c2 = st.columns([1,1])
                    with c1:
                        if st.button("Establecer contraseña", key=set_key):
                            # Validaciones
                            if not pwd_in:
                                st.error("Introduce la nueva contraseña.")
                            elif len(pwd_in) < 6:
                                st.error("La contraseña debe tener al menos 6 caracteres.")
                            elif pwd_in != pwd_conf:
                                st.error("Las contraseñas no coinciden.")
                            else:
                                USERS[u] = make_user(pwd_in, USERS[u]["role"])
                                st.success(f"Contraseña actualizada para {u}")
                                st.code(pwd_in)
                    with c2:
                        if st.button("Generar contraseña temporal", key=gen_key):
                            temp_pwd = secrets.token_urlsafe(6)
                            USERS[u] = make_user(temp_pwd, USERS[u]["role"])
                            st.success(f"Contraseña temporal para {u}:")
                            st.code(temp_pwd)
        else:
            st.write("No hay usuarios creados.")

