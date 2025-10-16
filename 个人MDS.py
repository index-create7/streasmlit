# multiuser_mds.py
import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from io import BytesIO
from datetime import datetime
import re
import sqlite3

# -------- 配置 --------
st.set_page_config(page_title="多用户个人MDS（完整版）", page_icon="🍂", layout="wide")
BASE_DIR = Path(__file__).resolve().parent
#
DATA_DIR = BASE_DIR / "personal_info.db"
#
USERS_PATH = DATA_DIR / "users.json"         # 存放用户账号信息（明文密码，便于测试）
SETTINGS_PATH = DATA_DIR / "settings.json"   # 存放管理员设置
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {"admin_password": "admin111", "auto_refresh": True}
DEFAULT_TABLES = ["个人基本信息", "个人荣誉信息", "个人日程信息"]
MAX_CUSTOM_TABLES = 7
COMMON_COLUMNS = ["id", "category", "created_at"]
DEFAULT_SPEC_FIELDS = ["title", "notes", "school", "degree", "platform"]
#
DEFAULT_ADMIN_PWD = "admin111"
#

# -------- 数据库核心操作（SQL封装） --------
def get_db_connection():
    """建立并返回SQLite数据库连接"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 支持按列名访问数据
    return conn


def init_database():
    """初始化数据库表结构（首次运行自动创建）"""
    conn = get_db_connection()
    cursor = conn.cursor()


# -------- 工具：文件与ID --------
def safe_user_id(username: str, sex: str) -> str:
    uid = f"{username.strip()}_{sex.strip()}"
    return re.sub(r"[^\w\-_.]", "_", uid)

def user_csv_path(uid: str) -> Path:
    return DATA_DIR / f"{uid}_records.csv"

def load_json(p: Path, default):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# -------- 用户与设置读写 --------
def load_users():
    return load_json(USERS_PATH, {})

def save_users(users: dict):
    save_json(USERS_PATH, users)

def load_settings():
    s = load_json(SETTINGS_PATH, None)
    if not s:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    return s

def save_settings(s: dict):
    save_json(SETTINGS_PATH, s)


# -------- 数据读写（按用户） --------
def load_user_df(uid: str) -> pd.DataFrame:
    p = user_csv_path(uid)
    if p.exists():
        df = pd.read_csv(p)
        for c in COMMON_COLUMNS + DEFAULT_SPEC_FIELDS:
            if c not in df.columns:
                df[c] = ""
        return df
    else:
        cols = COMMON_COLUMNS + DEFAULT_SPEC_FIELDS
        return pd.DataFrame(columns=cols)

def save_user_df(uid: str, df: pd.DataFrame):
    p = user_csv_path(uid)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)


# -------- 会话初始化 --------
def init_state():
    ss = st.session_state
    if "user_uid" not in ss: ss.user_uid = None
    if "user_name" not in ss: ss.user_name = ""
    if "user_sex" not in ss: ss.user_sex = ""
    if "is_admin" not in ss: ss.is_admin = False
    if "settings" not in ss: ss.settings = load_settings()
    if "page" not in ss: ss.page = "首页"
    if "just_refreshed" not in ss: ss.just_refreshed = False
    if "users" not in ss: ss.users = load_users()
init_state()


# -------- 辅助 UI 与行为 --------
def admin_check():
    ss = st.session_state
    if not ss.is_admin:
        st.error("需要管理员权限")
        return False
    return True

def show_topbar():
    ss = st.session_state
    st.markdown(f"**当前用户：** {ss.user_name or '未登录'}  {'(管理员)' if ss.is_admin else ''}")
    if ss.user_uid and not ss.is_admin:
        st.caption(f"Data file: {user_csv_path(ss.user_uid).name}")


# -------- 页面：登录与注册 --------
def page_auth():
    st.title("登录 / 注册")
    ss = st.session_state
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("用户登录")
        name = st.text_input("姓名", value=ss.user_name)
        sex = st.selectbox("性别", ["男", "女", "其他"], index=0 if ss.user_sex=="" else ["男","女","其他"].index(ss.user_sex))
        pwd = st.text_input("密码", type="password", key="login_pwd")
        if st.button("登录"):
            if not name.strip():
                st.error("请输入姓名")
            else:
                uid = safe_user_id(name, sex)
                users = load_users()
                if uid in users and users[uid]["password"] == pwd:
                    ss.user_uid = uid
                    ss.user_name = name
                    ss.user_sex = sex
                    ss.is_admin = False
                    ss.page = "用户主页"
                    ss.users = users
                    st.success("登录成功")
                    st.rerun()
                else:
                    st.error("账号不存在或密码错误")

    with col2:
        st.subheader("用户注册（首次登录会自动注册）")
        r_name = st.text_input("注册姓名", value="")
        r_sex = st.selectbox("注册性别", ["男","女","其他"], index=0, key="reg_sex")
        r_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
        r_pwd2 = st.text_input("重复密码", type="password", key="reg_pwd2")
        if st.button("注册并登录"):
            if not r_name.strip():
                st.error("请输入姓名")
            elif not r_pwd:
                st.error("请输入密码")
            elif r_pwd != r_pwd2:
                st.error("两次密码不一致")
            else:
                uid = safe_user_id(r_name, r_sex)
                users = load_users()
                if uid in users:
                    st.error("该用户名已存在，请直接登录或更换姓名/性别")
                else:
                    users[uid] = {"name": r_name, "sex": r_sex, "password": r_pwd}
                    save_users(users)
                    ss.user_uid = uid
                    ss.user_name = r_name
                    ss.user_sex = r_sex
                    ss.is_admin = False
                    ss.page = "用户主页"
                    ss.users = users
                    st.success("注册并登录成功")
                    st.rerun()

    st.markdown("---")
    st.subheader("管理员登录(初始密码admin111)")
    apw = st.text_input("管理员密码", type="password", key="adm_in")
    if st.button("管理员登录"):
        cur = ss.settings.get("admin_password", DEFAULT_SETTINGS["admin_password"])
        if apw == cur:
            ss.is_admin = True
            ss.page = "管理面板"
            st.success("管理员已登录")
            st.rerun()
        else:
            st.error("管理员密码错误")


# -------- 页面：用户主页 --------
def page_user_home():
    ss = st.session_state
    show_topbar()
    st.title(f"欢迎，{ss.user_name}")
    st.markdown("导航：左侧选择功能或顶部按钮")
    col1, col2, col3 = st.columns(3)

    if col1.button("📥 数据录入"):
        ss.page = "数据录入"
        st.rerun()
    if col2.button("📚 查看与编辑"):
        ss.page = "查看与编辑"
        st.rerun()
    if col3.button("📊 筛选与导出"):
        ss.page = "筛选与导出"
        st.rerun()


# -------- 页面：数据录入 --------
def page_data_input(uid):
    show_topbar()
    st.title("数据录入")
    df = load_user_df(uid)

    with st.form("add_form", clear_on_submit=True):
        new = {}
        new["id"] = 0 if df.empty else int(df["id"].max()) + 1
        new["title"] = st.text_input("标题", placeholder="例如：三好学生")
        CATEGORIES = ["荣誉", "教育经历", "竞赛", "证书", "账号", "其他"]
        new["category"] = st.selectbox("类别", CATEGORIES, index=0)
        new["notes"] = st.text_area("备注（可选）", placeholder="关键信息或链接…", height=100)
        submitted = st.form_submit_button("保存")

    if submitted:
        new["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_new = pd.DataFrame([new])
        df = pd.concat([df, df_new], ignore_index=True)
        save_user_df(uid, df)
        st.success("已保存")
        if st.session_state.settings.get("auto_refresh", True):
            time.sleep(1)
            st.session_state.just_refreshed = True
            st.rerun()

    if st.button("🔄 刷新"):
        st.session_state.just_refreshed = True
        st.rerun()


# -------- 页面：查看与编辑 --------
def page_view_edit(uid):
    show_topbar()
    st.title("查看与编辑")
    df = load_user_df(uid)
    if df.empty:
        st.info("暂无数据，请先录入")
        return
    if st.session_state.just_refreshed:
        st.success("刷新成功")
        st.session_state.just_refreshed = False

    st.dataframe(df, use_container_width=True)
    st.subheader("编辑或删除记录")
    selected_id = st.selectbox("选择记录ID", df["id"].tolist())
    selected_row = df[df["id"] == selected_id].iloc[0]

    with st.form("edit_form"):
        new_title = st.text_input("标题", selected_row.get("title", ""))
        new_category = st.text_input("类别", selected_row.get("category", ""))
        new_notes = st.text_area("备注", selected_row.get("notes", ""), height=120)
        col1, col2 = st.columns(2)
        update_btn = col1.form_submit_button("更新")
        delete_btn = col2.form_submit_button("删除")

    if update_btn:
        df.loc[df["id"] == selected_id, ["title", "category", "notes"]] = [new_title, new_category, new_notes]
        save_user_df(uid, df)
        st.success("更新成功")
        if st.session_state.settings.get("auto_refresh", True):
            time.sleep(1)
            st.session_state.just_refreshed = True
            st.rerun()

    if delete_btn:
        df = df[df["id"] != selected_id]
        save_user_df(uid, df)
        st.warning("已删除")
        if st.session_state.settings.get("auto_refresh", True):
            time.sleep(1)
            st.session_state.just_refreshed = True
            st.rerun()


# -------- 页面：筛选与导出 --------
def page_filter_export(uid):
    show_topbar()
    st.title("数据筛选与导出")
    df = load_user_df(uid)
    if df.empty:
        st.info("暂无数据")
        return

    st.subheader("筛选条件")
    c1, c2, c3 = st.columns(3)
    with c1:
        category_filter = st.selectbox("按类别筛选", ["全部"] + sorted(df["category"].dropna().unique().tolist()))
    with c2:
        keyword = st.text_input("关键字（标题或备注）")
    with c3:
        date_range = st.date_input("日期范围（可选）", [])

    filtered = df.copy()
    if category_filter != "全部":
        filtered = filtered[filtered["category"] == category_filter]
    if keyword:
        filtered = filtered[filtered["title"].fillna("").astype(str).str.contains(keyword, case=False) | filtered["notes"].fillna("").astype(str).str.contains(keyword, case=False)]
    if len(date_range) == 2:
        s, e = pd.to_datetime(date_range)
        filtered["created_at"] = pd.to_datetime(filtered["created_at"])
        filtered = filtered[(filtered["created_at"] >= s) & (filtered["created_at"] <= e)]

    st.dataframe(filtered, use_container_width=True)
    st.info(f"共 {len(filtered)} 条")

    st.subheader("导出")
    if not filtered.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            csv_bytes = filtered.to_csv(index=False).encode("utf-8")
            st.download_button("下载 CSV", csv_bytes, file_name="export.csv", mime="text/csv")
        with col2:
            out = BytesIO()
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                filtered.to_excel(writer, index=False, sheet_name="data")
            st.download_button("下载 Excel", out.getvalue(), file_name="export.xlsx")
        with col3:
            json_str = filtered.to_json(orient="records", force_ascii=False)
            st.download_button("下载 JSON", json_str, file_name="export.json", mime="application/json")
    else:
        st.warning("无数据可导出")


# -------- 页面：用户设置（仅用户自身可见） --------
def page_user_settings(uid):
    show_topbar()
    st.title("用户设置")
    users = load_users()
    if uid not in users:
        st.error("用户信息缺失")
        return
    user = users[uid]
    st.write(f"姓名：{user['name']}  性别：{user['sex']}")
    st.subheader("修改密码")
    old = st.text_input("当前密码", type="password", key="old_pwd")
    new = st.text_input("新密码", type="password", key="new_pwd")
    new2 = st.text_input("重复新密码", type="password", key="new_pwd2")
    if st.button("修改密码"):
        if old != user["password"]:
            st.error("当前密码不正确")
        elif not new:
            st.error("新密码不能为空")
        elif new != new2:
            st.error("两次密码不一致")
        else:
            users[uid]["password"] = new
            save_users(users)
            st.success("密码已修改，请记住新密码")


# -------- 页面：管理员面板 --------
def page_admin_panel():
    show_topbar()
    st.title("管理员面板")
    ss = st.session_state
    if not admin_check(): return

    users = load_users()
    st.subheader("用户列表（点击选择以管理）")
    if not users:
        st.info("暂无注册用户")
    else:
        uid_list = list(users.keys())
        sel = st.selectbox("选择用户", ["(选择)"] + uid_list)
        if sel != "(选择)":
            user = users[sel]
            st.markdown(f"**{user['name']}**  性别：{user['sex']}  文件：{user_csv_path(sel).name}")
            col1, col2, col3 = st.columns(3)
            if col1.button("查看/编辑用户数据"):
                st.session_state.impersonate = sel
                st.rerun()
            if col2.button("重置用户密码为 '123456'"):
                users[sel]["password"] = "123456"
                save_users(users)
                st.success("已重置为 123456")
            if col3.button("删除用户（含数据文件）"):
                # 删除数据文件和用户条目
                p = user_csv_path(sel)
                if p.exists(): p.unlink()
                users.pop(sel, None)
                save_users(users)
                st.success("用户及数据已删除")
                st.rerun()

    st.markdown("---")
    st.subheader("系统设置")
    settings = load_settings()
    new_admin_pw = st.text_input("修改管理员密码", type="password", key="adm_change")
    auto_refresh = st.checkbox("操作后自动刷新", value=settings.get("auto_refresh", True))
    if st.button("保存设置"):
        settings["admin_password"] = new_admin_pw or settings.get("admin_password", DEFAULT_SETTINGS["admin_password"])
        settings["auto_refresh"] = auto_refresh
        save_settings(settings)
        st.session_state.settings = settings
        st.success("设置已保存")


# -------- 主渲染 --------
def main():
    ss = st.session_state
    st.sidebar.title("导航")
    if ss.is_admin:
        side_pages = ["管理面板", "模拟用户视图", "退出登录"]
    else:
        side_pages = ["用户主页", "数据录入", "查看与编辑", "筛选与导出", "设置", "退出登录"]

    # 根据 page 状态设置 sidebar 默认选择
    if "page" not in ss:
        ss.page = "用户主页"
    choice = st.sidebar.radio("页面", side_pages, index=side_pages.index(ss.page) if ss.page in side_pages else 0, key="nav_choice")

    # 当 sidebar 切换时同步 page
    if choice != ss.page:
        ss.page = choice

    # 退出按钮
    if choice == "退出登录":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.page = "用户主页"
        st.rerun()

    # 管理员模拟用户视图
    if ss.is_admin and choice == "模拟用户视图":
        st.header("管理员模拟用户视图")
        users = load_users()
        uid_list = list(users.keys())
        if not uid_list:
            st.info("无用户可模拟")
        else:
            sel = st.selectbox("选择用户模拟", ["(选择)"] + uid_list)
            if sel != "(选择)":
                ss.impersonate = sel
                st.write(f"已切换为模拟用户：{sel}")
                if st.button("退出模拟"):
                    ss.impersonate = None
                    st.rerun()
                page_view_edit(sel)
        return

    # 管理员页面
    if ss.is_admin and choice == "管理面板":
        page_admin_panel()
        return

    # 未登录用户
    if not ss.user_uid:
        page_auth()
        return

    # 已登录用户页面路由
    current_uid = ss.user_uid
    if ss.is_admin and getattr(ss, "impersonate", None):
        current_uid = ss.impersonate

    # 根据 page 显示页面
    if ss.page == "用户主页":
        page_user_home()
    elif ss.page == "数据录入":
        page_data_input(current_uid)
    elif ss.page == "查看与编辑":
        page_view_edit(current_uid)
    elif ss.page == "筛选与导出":
        page_filter_export(current_uid)
    elif ss.page == "设置":
        page_user_settings(current_uid)
    else:
        page_user_home()


if __name__ == "__main__":
    main()
