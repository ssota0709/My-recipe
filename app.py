import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from io import BytesIO
from PIL import Image

# ==========================================
# 1. 接続設定
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DWKGtW5dDD1yUXllV7cJP-xQJJpHwPGAj66lVOtazqk/edit"

def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        secret_dict = json.loads(st.secrets["gcp_secret"])
        credentials = Credentials.from_service_account_info(secret_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except:
        return None

def get_sheet():
    client = get_gspread_client()
    if client:
        return client.open_by_url(SPREADSHEET_URL).sheet1
    return None

def init_db():
    try:
        sheet = get_sheet()
        header = ["id", "title", "author", "ingredients", "steps", "image_b64", "created_at"]
        values = sheet.get_all_values()
        if not values or values[0] != header:
            sheet.clear()
            sheet.append_row(header)
    except:
        pass

def add_recipe(title, author, ingredients, steps, image_b64):
    sheet = get_sheet()
    if sheet:
        now = datetime.now().strftime("%y/%m/%d %H:%M")
        recipe_id = str(int(datetime.now().timestamp()))
        sheet.append_row([recipe_id, title, author, ingredients, steps, image_b64, now])

def update_recipe(recipe_id, title, author, ingredients, steps, image_b64):
    sheet = get_sheet()
    if sheet:
        all_values = sheet.get_all_values()
        for i, row in enumerate(all_values):
            if i > 0 and row[0] == str(recipe_id):
                final_img = image_b64 if image_b64 else row[5]
                updated_row = [recipe_id, title, author, ingredients, steps, final_img, row[6]]
                sheet.update(f"A{i+1}:G{i+1}", [updated_row])
                break

def delete_recipe(recipe_id):
    sheet = get_sheet()
    if sheet:
        all_values = sheet.get_all_values()
        for i, row in enumerate(all_values):
            if i > 0 and row[0] == str(recipe_id):
                sheet.delete_rows(i + 1)
                break

def compress_image(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((400, 400))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=50)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except:
        return ""

def get_all_recipes():
    sheet = get_sheet()
    if not sheet: return pd.DataFrame()
    rows = sheet.get_all_values()
    if len(rows) <= 1: return pd.DataFrame()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df.iloc[::-1].reset_index(drop=True)

# ==========================================
# 2. 認証機能
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.title("🔒 2人の秘密のレシピ帳")
    pwd = st.text_input("合言葉を入れてね", type="password")
    if st.button("ログイン"):
        if pwd == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("合言葉が違うよ！")
    return False

# ==========================================
# 3. 画面構築
# ==========================================
st.set_page_config(page_title="2人のレシピ", page_icon="🍳")

if check_password():
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state['db_initialized'] = True

    st.title("2人のレシピ🍳")
    tab1, tab2 = st.tabs(["📖 レシピを見る", "✍️ 登録する"])

    with tab2:
        st.subheader("新しいレシピを登録")
        with st.form(key='recipe_form', clear_on_submit=True):
            title = st.text_input("レシピ名")
            author = st.radio("作った人", ["にゃんたろ", "ねこちゃん"], horizontal=True, key="new_author")
            ingredients = st.text_area("材料")
            steps = st.text_area("作り方")
            uploaded_file = st.file_uploader("写真", type=["jpg", "jpeg", "png"])
            if st.form_submit_button("保存する"):
                if title and ingredients and steps:
                    img_b64 = compress_image(uploaded_file) if uploaded_file else ""
                    add_recipe(title, author, ingredients, steps, img_b64)
                    st.success("保存したよ！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("入力が足りないよ")

    with tab1:
        try:
            df = get_all_recipes()
            if df.empty:
                st.info("まだレシピがないよ")
            else:
                for i, row in df.iterrows():
                    if not row.get('title'): continue
                    
                    edit_key = f"edit_mode_{row['id']}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    st.markdown(f"### 🍽️ {row['title']}")
                    st.caption(f"👤 {row['author']} | 📅 {row['created_at']}")
                    
                    with st.expander("詳細を見る"):
                        if not st.session_state[edit_key]:
                            if row.get('image_b64'):
                                try:
                                    st.image(base64.b64decode(row['image_b64']), use_container_width=True)
                                except:
                                    st.warning("📷 写真の読み込みに失敗しました")
                            
                            # 🌟 改行を反映させるためにテキストを表示
                            st.write("**【材料】**")
                            st.text(row['ingredients'])
                            st.write("**【作り方】**")
                            st.text(row['steps'])
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📝 編集する", key=f"btn_edit_{row['id']}"):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                            with col2:
                                if st.button("🗑️ 削除する", key=f"btn_del_{row['id']}"):
                                    delete_recipe(row['id'])
                                    st.success("削除しました")
                                    st.rerun()
                        else:
                            st.write("✏️ **レシピを編集中...**")
                            new_title = st.text_input("レシピ名", value=row['title'], key=f"edit_title_{row['id']}")
                            new_author = st.radio("作った人", ["にゃんたろ", "ねこちゃん"], 
                                                index=0 if row['author']=="にゃんたろ" else 1, 
                                                horizontal=True, key=f"edit_auth_{row['id']}")
                            new_ingredients = st.text_area("材料", value=row['ingredients'], key=f"edit_ing_{row['id']}")
                            new_steps = st.text_area("作り方", value=row['steps'], key=f"edit_step_{row['id']}")
                            new_file = st.file_uploader("写真を変更する場合のみ選択", type=["jpg", "jpeg", "png"], key=f"edit_img_{row['id']}")
                            
                            ecol1, ecol2 = st.columns(2)
                            with ecol1:
                                if st.button("✅ 保存", key=f"save_{row['id']}"):
                                    new_img_b64 = compress_image(new_file) if new_file else ""
                                    update_recipe(row['id'], new_title, new_author, new_ingredients, new_steps, new_img_b64)
                                    st.session_state[edit_key] = False
                                    st.rerun()
                            with ecol2:
                                if st.button("❌ キャンセル", key=f"cancel_{row['id']}"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                    st.markdown("---")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
