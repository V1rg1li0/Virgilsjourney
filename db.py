from __future__ import annotations
import streamlit as st
from supabase import create_client, Client


def configured() -> bool:
    return bool(st.secrets.get("SUPABASE_URL", "") and st.secrets.get("SUPABASE_ANON_KEY", ""))


def _clear_session_state():
    for key in ["access_token", "refresh_token", "user_id", "email", "auth_provider"]:
        st.session_state.pop(key, None)


def client() -> Client:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    access = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if access and refresh:
        try:
            res = sb.auth.set_session(access, refresh)
            if getattr(res, "session", None):
                st.session_state.access_token = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                if getattr(res, "user", None):
                    st.session_state.user_id = res.user.id
                    st.session_state.email = res.user.email
        except Exception:
            _clear_session_state()
    return sb


def sign_in(email: str, password: str):
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    res = sb.auth.sign_in_with_password({"email": email, "password": password})
    if res.session:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.email = res.user.email
        st.session_state.auth_provider = "password"
    return res


def sign_up(email: str, password: str):
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return sb.auth.sign_up({"email": email, "password": password})



def sign_in_with_google_tokens(id_token: str, access_token: str | None = None):
    """
    Intercambia los tokens OIDC de Google obtenidos por Streamlit por una
    sesión Supabase. Así se mantienen RLS y auth.uid() para todos los datos.
    """
    if not id_token:
        raise ValueError("Google no entregó un ID token.")

    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

    credentials = {
        "provider": "google",
        "token": id_token,
    }
    if access_token:
        credentials["access_token"] = access_token

    res = sb.auth.sign_in_with_id_token(credentials)

    if not getattr(res, "session", None) or not getattr(res, "user", None):
        raise RuntimeError("Supabase no pudo crear una sesión desde Google.")

    st.session_state.access_token = res.session.access_token
    st.session_state.refresh_token = res.session.refresh_token
    st.session_state.user_id = res.user.id
    st.session_state.email = res.user.email
    st.session_state.auth_provider = "google"
    return res


def sign_out():
    try:
        client().auth.sign_out()
    except Exception:
        pass
    _clear_session_state()
