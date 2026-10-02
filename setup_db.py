from neo4j import GraphDatabase

URI = "neo4j+s://..."
USERNAME = "..."
PASSWORD = "..."

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

driver.verify_connectivity()

DATABASE = "neo4j"


# =========================
# Constraint
# =========================

driver.execute_query(
    """
    CREATE CONSTRAINT user_id_unique
    IF NOT EXISTS
    FOR (u:Users)
    REQUIRE u.uid IS UNIQUE
    """,
    database_=DATABASE
)

driver.execute_query(
    """
    CREATE CONSTRAINT genre_id_unique
    IF NOT EXISTS
    FOR (g:Genres)
    REQUIRE g.gid IS UNIQUE
    """,
    database_=DATABASE
)


# =========================
# Users
# =========================

Users = [
    {"uid": "u001", "name": "Ace"},
    {"uid": "u002", "name": "Blaze"},
    {"uid": "u003", "name": "Cipher"},
    {"uid": "u004", "name": "Drift"},
    {"uid": "u005", "name": "Echo"},
    {"uid": "u006", "name": "Apex"},
    {"uid": "u007", "name": "Bolt"},
    {"uid": "u008", "name": "Cyra"},
    {"uid": "u009", "name": "Dante"},
    {"uid": "u010", "name": "Enzo"}
]

driver.execute_query(
    """
    UNWIND $Users AS row

    MERGE (u:Users {uid: row.uid})
    SET u.name = row.name
    """,
    Users=Users,
    database_=DATABASE
)


# =========================
# Genres
# =========================

Genres = [
    {"gid":"g001", "genre":"Pop"},
    {"gid":"g002", "genre":"Rock"},
    {"gid":"g003", "genre":"Jazz"},
    {"gid":"g004", "genre":"Classical"},
    {"gid":"g005", "genre":"Electronic"},
    {"gid":"g006", "genre":"Hip Hop"},
    {"gid":"g007", "genre":"R&B"},
    {"gid":"g008", "genre":"Lo-Fi"},
    {"gid":"g009", "genre":"Phonk"},
    {"gid":"g010", "genre":"Funk"},
    {"gid":"g011", "genre":"Soul"},
    {"gid":"g012", "genre":"Metal"},
    {"gid":"g013", "genre":"Reggae"}
]

driver.execute_query(
    """
    UNWIND $Genres AS row

    MERGE (g:Genres {gid: row.gid})
    SET g.genre = row.genre
    """,
    Genres=Genres,
    database_=DATABASE
)


# =========================
# Likes
# =========================

Likes = [
    {"uid": "u001", "gid": "g001"},
    {"uid": "u001", "gid": "g013"},
    {"uid": "u001", "gid": "g005"},
    {"uid": "u002", "gid": "g002"},
    {"uid": "u002", "gid": "g003"},
    {"uid": "u002", "gid": "g006"},
    {"uid": "u003", "gid": "g003"},
    {"uid": "u003", "gid": "g004"},
    {"uid": "u003", "gid": "g007"},
    {"uid": "u004", "gid": "g004"},
    {"uid": "u004", "gid": "g005"},
    {"uid": "u004", "gid": "g006"},
    {"uid": "u004", "gid": "g013"},
    {"uid": "u005", "gid": "g006"},
    {"uid": "u005", "gid": "g009"},
    {"uid": "u005", "gid": "g001"},
    {"uid": "u006", "gid": "g003"},
    {"uid": "u006", "gid": "g008"},
    {"uid": "u007", "gid": "g002"},
    {"uid": "u007", "gid": "g005"},
    {"uid": "u007", "gid": "g010"},
    {"uid": "u007", "gid": "g012"},
    {"uid": "u008", "gid": "g001"},
    {"uid": "u008", "gid": "g007"},
    {"uid": "u008", "gid": "g011"},
    {"uid": "u009", "gid": "g004"},
    {"uid": "u009", "gid": "g009"},
    {"uid": "u009", "gid": "g010"},
    {"uid": "u010", "gid": "g002"},
    {"uid": "u010", "gid": "g006"},
    {"uid": "u010", "gid": "g008"},
    {"uid": "u010", "gid": "g012"}
]

driver.execute_query(
    """
    UNWIND $Likes AS row

    MATCH (u:Users {uid: row.uid})
    MATCH (g:Genres {gid: row.gid})

    MERGE (u)-[:LIKE]->(g)
    """,
    Likes=Likes,
    database_=DATABASE
)

print("Database setup complete")

driver.close()