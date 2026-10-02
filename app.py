import streamlit as st
import pandas as pd
from neo4j import GraphDatabase


# =========================
# Page
# =========================

st.set_page_config(
    page_title="Neo4j Music Recommendation",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 Music Genre Explorer")
st.write("Neo4j + Streamlit")


# =========================
# Neo4j Connection
# =========================

@st.cache_resource
def get_driver():

    return GraphDatabase.driver(
        st.secrets["neo4j"]["uri"],
        auth=(
            st.secrets["neo4j"]["username"],
            st.secrets["neo4j"]["password"]
        )
    )


driver = get_driver()

DATABASE = st.secrets["neo4j"]["database"]


# =========================
# Query Function
# =========================

def run_query(query, params=None):

    result = driver.execute_query(
        query,
        database_=DATABASE,
        **(params or {})
    )

    data = [record.data() for record in result.records]

    return pd.DataFrame(data)


# =========================
# Users
# =========================

st.header("Users")

query_users = """
MATCH (u:Users)
RETURN
    u.uid AS UID,
    u.name AS Name
ORDER BY u.uid
"""

df_users = run_query(query_users)

st.dataframe(
    df_users,
    use_container_width=True
)


# =========================
# User Selection
# =========================

st.header("User Likes")

selected_user = st.selectbox(
    "เลือก User",
    df_users["Name"].tolist()
)


query_likes = """
MATCH (u:Users {name: $name})-[:LIKE]->(g:Genres)
RETURN
    u.uid AS UID,
    u.name AS Name,
    g.gid AS Genre_ID,
    g.genre AS Genre
ORDER BY Genre
"""

df_likes = run_query(
    query_likes,
    {
        "name": selected_user
    }
)

st.dataframe(
    df_likes,
    use_container_width=True
)


# =========================
# Similarity
# =========================

st.header("User Similarity")

query_similarity = """
MATCH (u1:Users {name: $name})-[:LIKE]->(g:Genres)
MATCH (u2:Users)-[:LIKE]->(g)
WHERE u1 <> u2

WITH u1, u2, COUNT(DISTINCT g) AS intersection

MATCH (u1)-[:LIKE]->(g1:Genres)
WITH
    u1,
    u2,
    intersection,
    COUNT(DISTINCT g1) AS set1_size

MATCH (u2)-[:LIKE]->(g2:Genres)

WITH
    u2.name AS OtherUser,
    intersection,
    set1_size,
    COUNT(DISTINCT g2) AS set2_size

WITH
    OtherUser,
    intersection,
    (set1_size + set2_size - intersection) AS union

RETURN
    OtherUser,
    ROUND(
        (toFloat(intersection) / union) * 100,
        2
    ) AS MatchRatePercent

ORDER BY MatchRatePercent DESC
"""

df_similarity = run_query(
    query_similarity,
    {
        "name": selected_user
    }
)

st.dataframe(
    df_similarity,
    use_container_width=True
)