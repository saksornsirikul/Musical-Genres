import streamlit as st
import pandas as pd
from neo4j import GraphDatabase

# =========================================================
# Page setup
# =========================================================
st.set_page_config(
    page_title="Music Genre Explorer",
    page_icon="🎵",
    layout="wide",
)

st.title("🎵 Music Genre Explorer")
st.caption("Neo4j + Streamlit")

# =========================================================
# Neo4j connection
# =========================================================
@st.cache_resource
def get_driver():
    return GraphDatabase.driver(
        st.secrets["neo4j"]["uri"],
        auth=(
            st.secrets["neo4j"]["username"],
            st.secrets["neo4j"]["password"],
        ),
    )


driver = get_driver()
DATABASE = st.secrets["neo4j"]["database"]


def run_query(query, params=None):
    """Run a Cypher query and return rows as a pandas DataFrame."""
    result = driver.execute_query(
        query,
        database_=DATABASE,
        **(params or {}),
    )
    return pd.DataFrame([record.data() for record in result.records])


# =========================================================
# Data functions
# =========================================================
def get_users(search=""):
    query = """
    MATCH (u:User)
    WHERE toLower(u.name) CONTAINS toLower($search)
       OR toLower(u.uid) CONTAINS toLower($search)
    RETURN u.uid AS uid, u.name AS name
    ORDER BY u.name
    """
    return run_query(query, {"search": search})


def get_all_users():
    return get_users("")


def get_genres(search=""):
    query = """
    MATCH (g:Genre)
    WHERE toLower(g.gid) CONTAINS toLower($search)
       OR toLower(g.name) CONTAINS toLower($search)
    RETURN g.gid AS gid, g.name AS name
    ORDER BY g.name
    """
    return run_query(query, {"search": search})


def get_user_genres(uid):
    query = """
    MATCH (u:User {uid: $uid})-[:LIKE]->(g:Genre)
    RETURN g.gid AS gid, g.name AS name
    ORDER BY g.name
    """
    return run_query(query, {"uid": uid})


def get_user(uid):
    query = """
    MATCH (u:User {uid: $uid})
    RETURN u.uid AS uid, u.name AS name
    """
    df = run_query(query, {"uid": uid})
    return None if df.empty else df.iloc[0].to_dict()


def add_user(uid, name):
    query = """
    CREATE (u:User {uid: $uid, name: $name})
    RETURN u.uid AS uid, u.name AS name
    """
    return run_query(query, {"uid": uid, "name": name})


def update_user(uid, name):
    query = """
    MATCH (u:User {uid: $uid})
    SET u.name = $name
    RETURN u.uid AS uid, u.name AS name
    """
    return run_query(query, {"uid": uid, "name": name})


def delete_user(uid):
    query = """
    MATCH (u:User {uid: $uid})
    DETACH DELETE u
    """
    run_query(query, {"uid": uid})


def add_genre(gid, name):
    query = """
    CREATE (g:Genre {gid: $gid, name: $name})
    RETURN g.gid AS gid, g.name AS name
    """
    return run_query(query, {"gid": gid, "name": name})


def update_genre(gid, name):
    query = """
    MATCH (g:Genre {gid: $gid})
    SET g.name = $name
    RETURN g.gid AS gid, g.name AS name
    """
    return run_query(query, {"gid": gid, "name": name})


def delete_genre(gid):
    query = """
    MATCH (g:Genre {gid: $gid})
    DETACH DELETE g
    """
    run_query(query, {"gid": gid})


def add_like(uid, gid):
    query = """
    MATCH (u:User {uid: $uid})
    MATCH (g:Genre {gid: $gid})
    MERGE (u)-[:LIKE]->(g)
    """
    run_query(query, {"uid": uid, "gid": gid})


def remove_like(uid, gid):
    query = """
    MATCH (u:User {uid: $uid})-[r:LIKE]->(g:Genre {gid: $gid})
    DELETE r
    """
    run_query(query, {"uid": uid, "gid": gid})


def get_genre_popularity():
    query = """
    MATCH (g:Genre)
    OPTIONAL MATCH (u:User)-[:LIKE]->(g)
    RETURN g.name AS genre, count(u) AS users
    ORDER BY users DESC, genre
    """
    return run_query(query)


def get_user_genre_counts():
    query = """
    MATCH (u:User)
    OPTIONAL MATCH (u)-[:LIKE]->(g:Genre)
    RETURN u.name AS user, count(g) AS genres
    ORDER BY genres DESC, user
    """
    return run_query(query)


def get_genre_users(gid):
    query = """
    MATCH (g:Genre {gid: $gid})
    OPTIONAL MATCH (u:User)-[:LIKE]->(g)
    RETURN u.uid AS uid, u.name AS name
    ORDER BY name
    """
    return run_query(query, {"gid": gid})


def get_recommendations(uid):
    """
    Jaccard similarity:
        intersection / union

    Find users with similar taste, then recommend genres
    that the selected user does not already like.
    """
    query = """
    MATCH (target:User {uid: $uid})

    // Genres liked by the target user
    OPTIONAL MATCH (target)-[:LIKE]->(targetGenre:Genre)
    WITH target, collect(DISTINCT targetGenre.gid) AS targetGenres

    // Other users and their genres
    MATCH (other:User)
    WHERE other.uid <> target.uid

    OPTIONAL MATCH (other)-[:LIKE]->(otherGenre:Genre)
    WITH target, targetGenres, other,
         collect(DISTINCT otherGenre.gid) AS otherGenres

    WITH target, targetGenres, other, otherGenres,
         size([x IN otherGenres WHERE x IN targetGenres]) AS intersection,
         size(targetGenres + [x IN otherGenres WHERE NOT x IN targetGenres]) AS unionSize

    WITH target, targetGenres, other, otherGenres, intersection,
         CASE
             WHEN unionSize = 0 THEN 0.0
             ELSE toFloat(intersection) / unionSize
         END AS similarity

    WHERE similarity > 0

    UNWIND otherGenres AS recommendedGid

    WITH target, targetGenres, other, similarity, recommendedGid
    WHERE NOT recommendedGid IN targetGenres

    MATCH (g:Genre {gid: recommendedGid})

    RETURN
        g.gid AS gid,
        g.name AS genre,
        round(max(similarity) * 100, 2) AS similarity,
        collect(DISTINCT other.name) AS from_users
    ORDER BY similarity DESC, genre
    LIMIT 10
    """
    return run_query(query, {"uid": uid})


# =========================================================
# Sidebar: current user
# =========================================================
st.sidebar.header("👤 Current User")

users_df = get_all_users()

if users_df.empty:
    st.warning("ยังไม่มี User ในฐานข้อมูล")
    st.stop()

user_options = {
    f"{row['name']} ({row['uid']})": row["uid"]
    for _, row in users_df.iterrows()
}

selected_label = st.sidebar.selectbox(
    "เลือก User",
    list(user_options.keys()),
)

selected_uid = user_options[selected_label]
selected_user = get_user(selected_uid)

st.sidebar.divider()
st.sidebar.info(
    "User ที่เลือกถือเป็นผู้ใช้งานปัจจุบัน "
    "จึงสามารถเพิ่ม/ลบแนวเพลงที่ตัวเองชอบได้"
)

# =========================================================
# Main profile
# =========================================================
st.subheader(f"👤 {selected_user['name']}")
st.caption(f"User ID: {selected_user['uid']}")

my_genres = get_user_genres(selected_uid)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("แนวเพลงที่ชอบ", len(my_genres))

with col2:
    st.metric("จำนวน Users", len(users_df))

genres_df = get_genres("")
with col3:
    st.metric("จำนวน Genres", len(genres_df))

# =========================================================
# Tabs
# =========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "❤️ My Genres",
        "🔍 Search",
        "⭐ Recommendation",
        "📊 Dashboard",
        "⚙️ Manage Data",
    ]
)

# =========================================================
# Tab 1: My Genres
# =========================================================
with tab1:
    st.subheader(f"❤️ แนวเพลงที่ {selected_user['name']} ชอบ")

    if my_genres.empty:
        st.info("ยังไม่มีแนวเพลงที่ชอบ")
    else:
        for _, row in my_genres.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"🎵 **{row['name']}**")
            with c2:
                if st.button("ลบ", key=f"remove_{selected_uid}_{row['gid']}"):
                    remove_like(selected_uid, row["gid"])
                    st.success(f"ลบ {row['name']} แล้ว")
                    st.rerun()

    st.divider()
    st.subheader("➕ เพิ่มแนวเพลงที่ชอบ")

    all_genres = get_genres("")
    liked_ids = set(my_genres["gid"].tolist()) if not my_genres.empty else set()

    available_genres = all_genres[
        ~all_genres["gid"].isin(liked_ids)
    ] if not all_genres.empty else all_genres

    if available_genres.empty:
        st.info("User นี้ชอบทุก Genre ที่มีในระบบแล้ว")
    else:
        genre_options = {
            f"{row['name']} ({row['gid']})": row["gid"]
            for _, row in available_genres.iterrows()
        }

        add_label = st.selectbox(
            "เลือก Genre",
            list(genre_options.keys()),
            key="add_genre_select",
        )

        if st.button("➕ เพิ่มความชอบ", type="primary"):
            add_like(selected_uid, genre_options[add_label])
            st.success("เพิ่ม Genre แล้ว")
            st.rerun()


# =========================================================
# Tab 2: Search
# =========================================================
with tab2:
    st.subheader("🔍 ค้นหา")

    search_type = st.radio(
        "ค้นหาอะไร?",
        ["Users", "Genres"],
        horizontal=True,
    )

    search_text = st.text_input(
        "พิมพ์ชื่อหรือ ID",
        placeholder="เช่น Ace หรือ Rock",
    )

    if search_type == "Users":
        result = get_users(search_text)

        if result.empty:
            st.info("ไม่พบ User")
        else:
            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("👀 ดู Favorite Genres ของ User")

            view_options = {
                f"{row['name']} ({row['uid']})": row["uid"]
                for _, row in result.iterrows()
            }

            if view_options:
                view_label = st.selectbox(
                    "เลือก User",
                    list(view_options.keys()),
                    key="view_user_select",
                )

                view_uid = view_options[view_label]
                view_user_genres = get_user_genres(view_uid)

                if view_user_genres.empty:
                    st.info("User นี้ยังไม่มี Genre ที่ชอบ")
                else:
                    st.dataframe(
                        view_user_genres,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(
                        "ผู้ใช้คนอื่นดูข้อมูลได้ แต่การเพิ่ม/ลบความชอบ "
                        "จะทำได้เฉพาะ User ที่เลือกเป็น Current User เท่านั้น"
                    )

    else:
        result = get_genres(search_text)

        if result.empty:
            st.info("ไม่พบ Genre")
        else:
            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("👥 Users ที่ชอบ Genre")

            genre_options = {
                f"{row['name']} ({row['gid']})": row["gid"]
                for _, row in result.iterrows()
            }

            selected_genre_label = st.selectbox(
                "เลือก Genre",
                list(genre_options.keys()),
                key="search_genre_select",
            )

            selected_gid = genre_options[selected_genre_label]
            genre_users = get_genre_users(selected_gid)

            if genre_users.empty or pd.isna(genre_users.iloc[0]["uid"]):
                st.info("ยังไม่มี User ที่ชอบ Genre นี้")
            else:
                st.dataframe(
                    genre_users.dropna(subset=["uid"]),
                    use_container_width=True,
                    hide_index=True,
                )


# =========================================================
# Tab 3: Recommendation
# =========================================================
with tab3:
    st.subheader(f"⭐ Recommendation สำหรับ {selected_user['name']}")
    st.caption("คำนวณจากความคล้ายของ Favorite Genres ด้วย Jaccard Similarity")

    try:
        recommendation_df = get_recommendations(selected_uid)

        if recommendation_df.empty:
            st.info(
                "ยังหา Recommendation ไม่ได้ "
                "อาจเป็นเพราะ Users ยังมี Genre ที่ชอบร่วมกันน้อยเกินไป"
            )
        else:
            display_df = recommendation_df.copy()
            display_df["similarity"] = (
                display_df["similarity"].astype(str) + "%"
            )
            display_df["from_users"] = display_df["from_users"].apply(
                lambda x: ", ".join(x)
            )

            st.dataframe(
                display_df[
                    ["genre", "similarity", "from_users"]
                ].rename(
                    columns={
                        "genre": "แนะนำ Genre",
                        "similarity": "Similarity",
                        "from_users": "จาก Users",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as e:
        st.error("เกิดข้อผิดพลาดในการคำนวณ Recommendation")
        st.code(str(e))


# =========================================================
# Tab 4: Dashboard
# =========================================================
with tab4:
    st.subheader("📊 Dashboard")

    popularity = get_genre_popularity()
    user_counts = get_user_genre_counts()

    st.write("### 🎵 ความนิยมของแต่ละ Genre")

    if not popularity.empty:
        popularity_chart = popularity.set_index("genre")[["users"]]
        st.bar_chart(popularity_chart)
    else:
        st.info("ยังไม่มีข้อมูล")

    st.write("### 👥 จำนวน Genre ที่แต่ละ User ชอบ")

    if not user_counts.empty:
        user_chart = user_counts.set_index("user")[["genres"]]
        st.bar_chart(user_chart)
    else:
        st.info("ยังไม่มีข้อมูล")


# =========================================================
# Tab 5: CRUD
# =========================================================
with tab5:
    st.subheader("⚙️ Manage Users")

    crud_user_tab1, crud_user_tab2, crud_user_tab3 = st.tabs(
        ["➕ เพิ่ม User", "✏️ แก้ไข User", "🗑️ ลบ User"]
    )

    with crud_user_tab1:
        new_uid = st.text_input("User ID", key="new_uid")
        new_name = st.text_input("ชื่อ User", key="new_name")

        if st.button("เพิ่ม User", key="create_user", type="primary"):
            if not new_uid.strip() or not new_name.strip():
                st.error("กรุณากรอก User ID และชื่อ")
            elif get_user(new_uid.strip()) is not None:
                st.error("User ID นี้มีอยู่แล้ว")
            else:
                add_user(new_uid.strip(), new_name.strip())
                st.success("เพิ่ม User สำเร็จ")
                st.rerun()

    with crud_user_tab2:
        edit_uid = st.selectbox(
            "เลือก User",
            users_df["uid"].tolist(),
            key="edit_user_uid",
        )
        edit_user = get_user(edit_uid)

        edit_name = st.text_input(
            "ชื่อใหม่",
            value=edit_user["name"],
            key="edit_user_name",
        )

        if st.button("บันทึกการแก้ไข", key="update_user"):
            if not edit_name.strip():
                st.error("ชื่อห้ามว่าง")
            else:
                update_user(edit_uid, edit_name.strip())
                st.success("แก้ไข User สำเร็จ")
                st.rerun()

    with crud_user_tab3:
        delete_uid = st.selectbox(
            "เลือก User ที่ต้องการลบ",
            users_df["uid"].tolist(),
            key="delete_user_uid",
        )

        st.warning(
            "การลบ User จะลบความสัมพันธ์ LIKE ของ User นี้ด้วย"
        )

        confirm_delete_user = st.checkbox(
            "ฉันยืนยันว่าต้องการลบ User นี้",
            key="confirm_delete_user",
        )

        if st.button("ลบ User", key="delete_user", type="secondary"):
            if not confirm_delete_user:
                st.error("กรุณาติ๊กยืนยันก่อน")
            else:
                delete_user(delete_uid)
                st.success("ลบ User สำเร็จ")
                st.rerun()

    st.divider()

    st.subheader("🎵 Manage Genres")

    crud_genre_tab1, crud_genre_tab2, crud_genre_tab3 = st.tabs(
        ["➕ เพิ่ม Genre", "✏️ แก้ไข Genre", "🗑️ ลบ Genre"]
    )

    with crud_genre_tab1:
        new_gid = st.text_input("Genre ID", key="new_gid")
        new_genre_name = st.text_input("ชื่อ Genre", key="new_genre_name")

        if st.button("เพิ่ม Genre", key="create_genre", type="primary"):
            existing = get_genres(new_gid.strip())

            if not new_gid.strip() or not new_genre_name.strip():
                st.error("กรุณากรอก Genre ID และชื่อ")
            elif not existing.empty and (
                existing["gid"] == new_gid.strip()
            ).any():
                st.error("Genre ID นี้มีอยู่แล้ว")
            else:
                add_genre(new_gid.strip(), new_genre_name.strip())
                st.success("เพิ่ม Genre สำเร็จ")
                st.rerun()

    with crud_genre_tab2:
        current_genres = get_genres("")

        if current_genres.empty:
            st.info("ยังไม่มี Genre")
        else:
            edit_gid = st.selectbox(
                "เลือก Genre",
                current_genres["gid"].tolist(),
                key="edit_genre_gid",
            )

            current_row = current_genres[
                current_genres["gid"] == edit_gid
            ].iloc[0]

            edit_genre_name = st.text_input(
                "ชื่อใหม่",
                value=current_row["name"],
                key="edit_genre_name",
            )

            if st.button("บันทึกการแก้ไข", key="update_genre"):
                if not edit_genre_name.strip():
                    st.error("ชื่อห้ามว่าง")
                else:
                    update_genre(edit_gid, edit_genre_name.strip())
                    st.success("แก้ไข Genre สำเร็จ")
                    st.rerun()

    with crud_genre_tab3:
        current_genres = get_genres("")

        if current_genres.empty:
            st.info("ยังไม่มี Genre")
        else:
            delete_gid = st.selectbox(
                "เลือก Genre ที่ต้องการลบ",
                current_genres["gid"].tolist(),
                key="delete_genre_gid",
            )

            st.warning(
                "การลบ Genre จะลบความสัมพันธ์ LIKE ของ Genre นี้ด้วย"
            )

            confirm_delete_genre = st.checkbox(
                "ฉันยืนยันว่าต้องการลบ Genre นี้",
                key="confirm_delete_genre",
            )

            if st.button("ลบ Genre", key="delete_genre"):
                if not confirm_delete_genre:
                    st.error("กรุณาติ๊กยืนยันก่อน")
                else:
                    delete_genre(delete_gid)
                    st.success("ลบ Genre สำเร็จ")
                    st.rerun()


# =========================================================
# Footer
# =========================================================
st.divider()
st.caption("Music Genre Explorer • Powered by Neo4j + Streamlit")
