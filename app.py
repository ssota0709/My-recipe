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
# 1. スプレッドシート接続設定
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DWKGtW5dDD1yUXllV7cJP-xQJJpHwPGAj66lVOtazqk/edit"

def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    secret_dict = json.loads(st.secrets["gcp_secret"])
    credentials = Credentials.from_service_account_info(secret_dict, scopes=scopes)
    return gspread.authorize(credentials)

def get_sheet():
    client = get_gspread_client()
    sh = client.open_by_url(SPREADSHEET_URL)
    return sh.sheet1

def init_db():
    """スプレッドシートの1行目を強制的に正しくセットする"""
    sheet = get_sheet()
    header = ["id", "title", "author", "ingredients", "steps", "image_b64", "created_at"]
    
    # 1行目を取得して、正しくなければ上書き
    values = sheet.get_all_values()
    if not values or values[0] != header:
        sheet.clear()
        sheet.append_row(header)

def add_recipe(title, author, ingredients, steps, image_b64):
    sheet = get_sheet()
    now = datetime.now().strftime("%y/%m/%d %H:%M")
    recipe_id = str(int(datetime.now().timestamp()))
    sheet.append_row([recipe_id, title, author, ingredients, steps, image_b64, now])

def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.thumbnail((400, 400)) # 少し小さめにして安定性を高める
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=50) # 圧縮率を少し上げる
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def get_all_recipes():
    sheet = get_sheet()
    # 🌟 get_all_values で取得してから DataFrame にすることで「titleが見つからない」エラーを防ぐ
    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return pd.DataFrame()
    
    header = rows[0]
    data = rows[1:]
    df = pd.DataFrame(data, columns=header)
    
    # 新しい順に並び替え
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
st.set_page_config(page_title="2人のレシピ", page_icon="🍳")

init_db()

st.title("2人のレシピ🍳")
st.write("今日も料理してえらいね！")

tab1, tab2 = st.tabs(["📖 レシピを見る", "✍️ 登録する"])

with tab2:
    st.subheader("新しいレシピを登録")
    with st.form(key='recipe_form', clear_on_submit=True):
        title = st.text_input("レシピ名")
        author = st.radio("作った人", ["にゃんたろ", "ねこちゃん"], horizontal=True)
        ingredients = st.text_area("材料")
        steps = st.text_area("作り方")
        uploaded_file = st.file_uploader("写真", type=["jpg", "jpeg", "png"])
        submit_button = st.form_submit_button(label="保存する")
        
        if submit_button:
            if title and ingredients and steps:
                image_b64 = ""
                if uploaded_file is not None:
                    try:
                        image_b64 = compress_image(uploaded_file)
                    except Exception as e:
                        st.error(f"写真の処理でエラー: {e}")
                
                try:
                    add_recipe(title, author, ingredients, steps, image_b64)
                    st.success(f"「{title}」を保存したよ！")
                except Exception as e:
                    st.error(f"保存エラー: {e}")
            else:
                st.error("入力を完成させてね！")

with tab1:
    try:
        df = get_all_recipes()
        if df.empty:
