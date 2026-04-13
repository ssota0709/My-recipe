import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# 1. データベース設定
# ==========================================
DB_NAME = 'our_recipes_v2.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # ※後方互換性のため image_b64 の列は残しています
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

def add_recipe(title, author, ingredients, steps):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%y/%m/%d %H:%M")
    # 写真データは空文字("")として保存します
    c.execute('INSERT INTO recipes (title, author, ingredients, steps, image_b64, created_at) VALUES (?, ?, ?, ?, ?, ?)',
              (title, author, ingredients, steps, "", now))
    conn.commit()
    conn.close()

def get_all_recipes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM recipes ORDER BY id DESC", conn)
    conn.close()
    return df

def delete_recipe(recipe_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
    conn.commit()
    conn.close()

# ==========================================
# 2. 画面構築
# ==========================================
st.set_page_config(page_title="2人のレシピ", page_icon="🍳", layout="centered")

init_db()

st.title("2人のレシピ🍳")
st.write("今日も料理してえらいね！")

tab1, tab2 = st.tabs(["📖 レシピを見る", "✍️ 登録する"])

# --- タブ2：登録画面 ---
with tab2:
    st.subheader("新しいレシピを登録")
    with st.form(key='recipe_form', clear_on_submit=True):
        title = st.text_input("レシピ名", placeholder="例：絶品カレー")
        author = st.radio("作った人", ["にゃんたろ", "ねこちゃん"], horizontal=True)
        ingredients = st.text_area("材料", height=100)
        steps = st.text_area("作り方", height=100)
        
        submit_button = st.form_submit_button(label="保存する")
        
        if submit_button:
            if title and ingredients and steps:
                add_recipe(title, author, ingredients, steps)
                st.success(f"「{title}」を保存したよ！")
            else:
                st.error("入力が足りないよ！")

# --- タブ1：一覧画面 ---
with tab1:
    recipes_df = get_all_recipes()
    
    if recipes_df.empty:
        st.info("まだレシピがないよ。登録してみてね！")
    else:
        # 検索・フィルター
        search_query = st.text_input("🔍 検索（名前や材料）")
        author_filter = st.radio("絞り込み", ["すべて", "にゃんたろ", "ねこちゃん"], horizontal=True)
        
        if search_query:
            recipes_df = recipes_df[recipes_df['title'].str.contains(search_query, na=False) | 
                                    recipes_df['ingredients'].str.contains(search_query, na=False)]
        if author_filter != "すべて":
            recipes_df = recipes_df[recipes_df['author'] == author_filter]

        st.markdown("---")

        # レシピ表示ループ（写真なしのシンプルレイアウト）
        for index, row in recipes_df.iterrows():
            st.markdown(f"### 🍽️ {row['title']}")
            st.caption(f"👤 {row['author']} | 📅 {row['created_at']}")
            
            with st.expander("材料・作り方を見る"):
                st.markdown("**【材料】**")
                st.write(row['ingredients'])
                st.markdown("**【作り方】**")
                st.write(row['steps'])
                
                # 削除ボタン
                st.markdown("---")
                if st.button("🗑️ 削除する", key=f"del_{row['id']}"):
                    delete_recipe(row['id'])
                    st.rerun()
            
            st.markdown("---")

