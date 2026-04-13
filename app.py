import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64

# ==========================================
# 1. データベースの設定（写真対応版）
# ==========================================
DB_NAME = 'our_recipes_v2.db' # 構造が変わるため新しくします

def init_db():
    """データベースとテーブルを作成する"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            ingredients TEXT,
            steps TEXT,
            image_b64 TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_recipe(title, author, ingredients, steps, image_b64):
    """新しいレシピをデータベースに保存する"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO recipes (title, author, ingredients, steps, image_b64, created_at) VALUES (?, ?, ?, ?, ?, ?)',
              (title, author, ingredients, steps, image_b64, now))
    conn.commit()
    conn.close()

def get_all_recipes():
    """保存されたレシピをすべて取得する"""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM recipes ORDER BY id DESC", conn)
    conn.close()
    return df

# ==========================================
# 2. 画面の構築（Streamlit UI）
# ==========================================
st.set_page_config(page_title="ふたりのレシピ帳", page_icon="🍳", layout="centered")

init_db()

st.title("🍳 ふたりのレシピ帳")
st.write("検索機能と写真アップロードに対応しました！")

tab1, tab2 = st.tabs(["📖 レシピを見る", "✍️ 新しく登録する"])

# --- タブ2：レシピ登録画面 ---
with tab2:
    st.subheader("新しいレシピを登録")
    
    with st.form(key='recipe_form', clear_on_submit=True):
        title = st.text_input("レシピ名", placeholder="例：絶品！鶏肉のトマト煮込み")
        author = st.radio("作った人", ["彼氏", "彼女"], horizontal=True)
        ingredients = st.text_area("材料", placeholder="例：\n・鶏もも肉 1枚\n・玉ねぎ 1個", height=100)
        steps = st.text_area("作り方", placeholder="例：\n1. 切る\n2. 炒める", height=100)
        
        # 🌟新機能：写真アップロード
        uploaded_file = st.file_uploader("料理の写真（任意）", type=["jpg", "jpeg", "png"])
        
        submit_button = st.form_submit_button(label="データベースに保存する")
        
        if submit_button:
            if title and ingredients and steps:
                # 画像をテキストデータ(Base64)に変換してデータベースに保存しやすくする
                image_b64 = ""
                if uploaded_file is not None:
                    image_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8")
                
                add_recipe(title, author, ingredients, steps, image_b64)
                st.success(f"「{title}」を保存しました！「レシピを見る」タブを確認してね。")
            else:
                st.error("レシピ名、材料、作り方は必須です！")

# --- タブ1：レシピ一覧画面 ---
with tab1:
    st.subheader("保存されたレシピ一覧")
    
    recipes_df = get_all_recipes()
    
    if recipes_df.empty:
        st.info("まだレシピがありません。「新しく登録する」から追加してください！")
    else:
        # 🌟新機能：検索と絞り込みバー
        with st.container():
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search_query = st.text_input("🔍 レシピ名や材料で検索")
            with col_filter:
                author_filter = st.radio("絞り込み", ["すべて", "彼氏", "彼女"], horizontal=True)
        
        # 検索キーワードと絞り込みの条件でデータを裏側でフィルタリング
        if search_query:
            recipes_df = recipes_df[recipes_df['title'].str.contains(search_query, na=False) | 
                                    recipes_df['ingredients'].str.contains(search_query, na=False)]
        if author_filter != "すべて":
            recipes_df = recipes_df[recipes_df['author'] == author_filter]
            
        st.write(f"**{len(recipes_df)}件** のレシピが見つかりました")

        # 絞り込んだ結果を表示
        for index, row in recipes_df.iterrows():
            with st.expander(f"🍽️ {row['title']} （登録者: {row['author']}）"):
                st.caption(f"登録日時: {row['created_at']}")
                
                # 画像があれば表示する処理
                if row['image_b64']:
                    image_bytes = base64.b64decode(row['image_b64'])
                    st.image(image_bytes, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**【材料】**")
                    st.text(row['ingredients'])
                with col2:
                    st.markdown("**【作り方】**")
                    st.text(row['steps'])
