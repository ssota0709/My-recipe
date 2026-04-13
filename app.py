import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import base64  # 🌟写真データを扱うために追加

# ==========================================
# 1. スプレッドシート接続設定
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DWKGtW5dDD1yUXllV7cJP-xQJJpHwPGAj66lVOtazqk/edit"

def get_gspread_client():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    secret_dict = json.loads(st.secrets["gcp_secret"])
    credentials = Credentials.from_service_account_info(secret_dict, scopes=scopes)
    return gspread.authorize(credentials)

def get_sheet():
    client = get_gspread_client()
    sh = client.open_by_url(SPREADSHEET_URL)
    return sh.sheet1

def init_db():
    sheet = get_sheet()
    if not sheet.get_all_values():
        # ヘッダーに image_b64 を追加
        header = ["id", "title", "author", "ingredients", "steps", "image_b64", "created_at"]
        sheet.append_row(header)

def add_recipe(title, author, ingredients, steps, image_b64):
    sheet = get_sheet()
    now = datetime.now().strftime("%y/%m/%d %H:%M")
    recipe_id = str(int(datetime.now().timestamp()))
    # スプレッドシートに保存
    sheet.append_row([recipe_id, title, author, ingredients, steps, image_b64, now])

def get_all_recipes():
    sheet = get_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.iloc[::-1].reset_index(drop=True)
    return df

def delete_recipe(recipe_id):
    sheet = get_sheet()
    all_values = sheet.get_all_values()
    for i, row in enumerate(all_values):
        if i == 0: continue
        if row[0] == str(recipe_id):
            sheet.delete_rows(i + 1)
            break

# ==========================================
# 2. 画面構築
# ==========================================
st.set_page_config(page_title="2人のレシピ", page_icon="🍳", layout="centered")

try:
    init_db()
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

st.title("2人のレシピ🍳")
st.write("今日も料理してえらいね！")

tab1, tab2 = st.tabs(["📖 レシピを見る", "✍️ 登録する"])

# --- タブ2：登録画面（写真アップロード復活） ---
with tab2:
    st.subheader("新しいレシピを登録")
    with st.form(key='recipe_form', clear_on_submit=True):
        title = st.text_input("レシピ名", placeholder="例：絶品カレー")
        author = st.radio("作った人", ["にゃんたろ", "ねこちゃん"], horizontal=True)
        ingredients = st.text_area("材料", placeholder="例：\n・鶏肉 200g", height=100)
        steps = st.text_area("作り方", placeholder="例：\n1. 炒める", height=100)
        
        # 🌟写真アップロードを復活
        uploaded_file = st.file_uploader("料理の写真（任意）", type=["jpg", "jpeg", "png"])
        
        submit_button = st.form_submit_button(label="保存する")
        
        if submit_button:
            if title and ingredients and steps:
                # 画像をテキストに変換
                image_b64 = ""
                if uploaded_file is not None:
                    image_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
                
                add_recipe(title, author, ingredients, steps, image_b64)
                st.success(f"「{title}」を保存したよ！")
            else:
                st.error("入力が足りないよ！")

# --- タブ1：一覧画面（写真表示を復活） ---
with tab1:
    recipes_df = get_all_recipes()
    
    if recipes_df.empty:
        st.info("まだレシピがないよ。登録してみてね！")
    else:
        search_query = st.text_input("🔍 検索")
        author_filter = st.radio("絞り込み", ["すべて", "にゃんたろ", "ねこちゃん"], horizontal=True)
        
        if search_query:
            recipes_df = recipes_df[recipes_df['title'].astype(str).str.contains(search_query, na=False) | 
                                    recipes_df['ingredients'].astype(str).str.contains(search_query, na=False)]
        if author_filter != "すべて":
            recipes_df = recipes_df[recipes_df['author'] == author_filter]

        st.markdown("---")

        for index, row in recipes_df.iterrows():
            # 🌟スマホで見やすいように「タイトル」の下に「写真」が出る形式にします
            st.markdown(f"### 🍽️ {row['title']}")
            st.caption(f"👤 {row['author']} | 📅 {row['created_at']}")
            
            # 写真があれば表示
            if "image_b64" in row and row['image_b64']:
                try:
                    img_data = base64.b64decode(row['image_b64'])
                    st.image(img_data, use_container_width=True)
                except:
                    pass
            
            with st.expander("材料・作り方を見る"):
                st.markdown("**【材料】**")
                st.write(row['ingredients'])
                st.markdown("**【作り方】**")
                st.write(row['steps'])
                
                st.markdown("---")
                if st.button("🗑️ 削除する", key=f"del_{row['id']}"):
                    delete_recipe(row['id'])
                    st.rerun()
            st.markdown("---")
