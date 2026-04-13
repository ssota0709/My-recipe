import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
from io import BytesIO
from PIL import Image  # 🌟画像圧縮のために使用

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
    values = sheet.get_all_values()
    if not values or len(values[0]) < 7:
        sheet.clear()
        header = ["id", "title", "author", "ingredients", "steps", "image_b64", "created_at"]
        sheet.append_row(header)

def add_recipe(title, author, ingredients, steps, image_b64):
    sheet = get_sheet()
    now = datetime.now().strftime("%y/%m/%d %H:%M")
    recipe_id = str(int(datetime.now().timestamp()))
    sheet.append_row([recipe_id, title, author, ingredients, steps, image_b64, now])

# 🌟画像を小さく圧縮する関数を追加
def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    # RGB形式に変換（PNGなどの透明度を削除）
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # サイズを最大横幅500pxにリサイズ
    img.thumbnail((500, 500))
    
    # 圧縮してバイトデータに変換
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=60) # 画質を60%に落として軽量化
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

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
                        # 🌟ここで圧縮を実行
                        image_b64 = compress_image(uploaded_file)
                    except Exception as e:
                        st.error(f"画像の処理に失敗しました: {e}")
                
                try:
                    add_recipe(title, author, ingredients, steps, image_b64)
                    st.success(f"「{title}」を保存したよ！")
                except Exception as e:
                    # エラー内容を詳しく表示させる
                    st.error(f"保存に失敗しました。データが大きすぎる可能性があります: {e}")
            else:
                st.error("入力が足りないよ！")

with tab1:
    try:
        recipes_df = get_all_recipes()
        if recipes_df.empty:
            st.info("まだレシピがないよ。")
        else:
            for index, row in recipes_df.iterrows():
                st.markdown(f"### 🍽️ {row['title']}")
                st.caption(f"👤 {row['author']} | 📅 {row['created_at']}")
                
                if "image_b64" in row and row['image_b64']:
                    try:
                        img_data = base64.b64decode(row['image_b64'])
                        st.image(img_data, use_container_width=True)
                    except:
                        pass
                
                with st.expander("詳細を見る"):
                    st.write("**【材料】**\n", row['ingredients'])
                    st.write("**【作り方】**\n", row['steps'])
                    if st.button("🗑️ 削除", key=f"del_{row['id']}"):
                        delete_recipe(row['id'])
                        st.rerun()
                st.markdown("---")
    except Exception as e:
        st.error(f"表示エラー: {e}")
