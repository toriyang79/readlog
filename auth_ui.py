# ============================
# auth_ui.py
# (강제 재배포를 위한 주석 추가)
# ============================
import os
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

from utils import hash_password
from models import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    unread_notifications_count,
    mark_all_notifications_read,
)

def _cookie_password() -> str:
    """쿠키 암호를 환경변수 > secrets.toml > 기본값 순으로 결정.
    secrets.toml 이 없을 때 Streamlit이 FileNotFoundError 를 던지므로 안전 처리.
    """
    env_pw = os.getenv("COOKIE_PASSWORD")
    if env_pw:
        return env_pw
    try:
        secrets_obj = getattr(st, "secrets", None)
        if secrets_obj:
            val = secrets_obj.get("COOKIE_PASSWORD", None)
            if val:
                return val
    except Exception:
        # secrets.toml 이 없거나 접근 실패해도 기본값 사용
        pass
    return "readlog_dev_secret"

def _set_session_user(row):
    st.session_state.user = {
        "id": row["id"],
        "email": row["email"],
        "nickname": row["nickname"],
        "profile_image": row["profile_image"],
    }

def ui_auth():
    # ✅ 쿠키 매니저 준비 (세션당 1회만 초기화)
    if "cookies" not in st.session_state:
        st.session_state.cookies = EncryptedCookieManager(prefix="readlog_", password=_cookie_password())
    cookies = st.session_state.cookies

    if not cookies.ready():
        st.warning("쿠키를 준비 중입니다. 잠시 후 새로고침 해주세요.")
        st.stop()

    # 기본 세션 키
    # st.session_state.setdefault("user", None) # Moved to app.py
    # st.session_state.setdefault("unread_count", 0) # Moved to app.py

    # 🔁 쿠키(user_id)로 자동 로그인 복원
    if st.session_state.user is None:
        uid = st.session_state.cookies.get("user_id")
        if uid:
            try:
                uid = str(uid).strip()
                if uid.isdigit():  # 숫자인 경우만 처리
                    row = get_user_by_id(int(uid))
                    if row:
                        _set_session_user(row)
            except Exception:
                pass

    # 로그인된 상태
    if st.session_state.user:
        me = st.session_state.user
        st.sidebar.success(f"안녕하세요, {me['nickname']}님!")

        try:
            st.session_state.unread_count = unread_notifications_count(me["id"]) or 0
        except Exception:
            st.session_state.unread_count = 0

        if st.session_state.unread_count:
            if st.sidebar.button(f"🔔 알림({st.session_state.unread_count}) 확인"):
                mark_all_notifications_read(me["id"])
                st.session_state.unread_count = 0
                st.rerun()

        # (로그아웃 버튼 핸들러)
        if st.sidebar.button("로그아웃"):
            # 1) 세션 사용자 비우기
            st.session_state.user = None
            st.session_state.unread_count = 0

            # 2) 쿠키 확실히 비우기
            st.session_state.cookies["user_id"] = ""        # 빈 값으로 덮어쓰기
            if "user_id" in st.session_state.cookies:       # 키 자체 삭제
                del st.session_state.cookies["user_id"]
            st.session_state.cookies.save()

            st.success("로그아웃되었습니다.")
            st.rerun()

        st.sidebar.divider()
        return

    # 비로그인 → 로그인/회원가입 탭
    st.sidebar.header("🔐 로그인/회원가입")
    tab_login, tab_signup = st.sidebar.tabs(["로그인", "회원가입"])

    with tab_login:
        email = st.text_input("이메일", key="login_email")
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", type="primary"):
            row = get_user_by_email(email)
            if row and row["password_hash"] == hash_password(pw):
                _set_session_user(row)
                st.session_state.cookies["user_id"] = str(row["id"])  # ✅ 쿠키 저장
                st.session_state.cookies.save()
                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("이메일 또는 비밀번호가 올바르지 않습니다.")

    with tab_signup:
        email_s = st.text_input("이메일", key="signup_email")
        nickname_s = st.text_input("닉네임", key="signup_nick")
        pw_s = st.text_input("비밀번호", type="password", key="signup_pw")
        if st.button("회원가입"):
            if not email_s or not nickname_s or not pw_s:
                st.warning("모든 칸을 입력해주세요.")
            elif get_user_by_email(email_s):
                st.error("이미 가입된 이메일입니다.")
            else:
                try:
                    create_user(email_s, pw_s, nickname_s)
                    st.success("회원가입 성공! 이제 로그인 해주세요.")
                except Exception as e:
                    st.error(f"회원가입 실패: {e}")
