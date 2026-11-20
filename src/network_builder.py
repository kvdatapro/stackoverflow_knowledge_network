import pandas as pd
import networkx as nx

def build_interactions(questions_df, answers_df):
    if questions_df.empty or answers_df.empty:
        return pd.DataFrame(columns=[
            "answer_user_id", "question_user_id", "answer_user_name",
            "question_user_name", "blooms_level", "question_id", "answer_id"
        ])

    q_name_col = "owner_name" if "owner_name" in questions_df.columns else "owner_display_name"
    a_name_col = "owner_name" if "owner_name" in answers_df.columns else "owner_display_name"

    q_cols = ["question_id", "owner_user_id", "blooms_level"]
    if q_name_col in questions_df.columns:
        q_cols.append(q_name_col)

    q_sub = questions_df[q_cols].copy()
    q_rename = {"owner_user_id": "question_user_id"}
    if q_name_col in q_sub.columns:
        q_rename[q_name_col] = "question_user_name"
    q_sub = q_sub.rename(columns=q_rename)
    if "question_user_name" not in q_sub.columns:
        q_sub["question_user_name"] = "Anonymous"

    a_cols = ["answer_id", "question_id", "owner_user_id"]
    if a_name_col in answers_df.columns:
        a_cols.append(a_name_col)

    a_sub = answers_df[a_cols].copy()
    a_rename = {"owner_user_id": "answer_user_id"}
    if a_name_col in a_sub.columns:
        a_rename[a_name_col] = "answer_user_name"
    a_sub = a_sub.rename(columns=a_rename)
    if "answer_user_name" not in a_sub.columns:
        a_sub["answer_user_name"] = "Anonymous"

    merged = pd.merge(a_sub, q_sub, on="question_id", how="inner")

    merged = merged.dropna(subset=["answer_user_id", "question_user_id"])
    merged["answer_user_id"] = merged["answer_user_id"].astype(int)
    merged["question_user_id"] = merged["question_user_id"].astype(int)

    # Exclude self-answers (User answering own question)
    merged = merged[merged["answer_user_id"] != merged["question_user_id"]]

    # Drop duplicate identical answer records if present
    merged = merged.drop_duplicates(subset=["answer_id"])
    return merged

def build_user_network(interactions_df, users_df=None):
    G = nx.DiGraph()

    name_map = {}
    if users_df is not None and not users_df.empty:
        for _, row in users_df.iterrows():
            if pd.notna(row.get("user_id")):
                uid = int(row["user_id"])
                name_map[uid] = str(row.get("display_name", row.get("owner_name", f"User_{uid}")))

    if interactions_df.empty:
        return G

    #Pairwise aggregation: directed edge Answerer > Asker
    pair_counts = interactions_df.groupby(["answer_user_id", "question_user_id"]).size().reset_index(name="weight")

    # Blooms breakdown per directed pair
    bloom_breakdown = interactions_df.groupby(
        ["answer_user_id", "question_user_id", "blooms_level"]
    ).size().unstack(fill_value=0)

    for _, row in pair_counts.iterrows():
        u = int(row["answer_user_id"])
        v = int(row["question_user_id"])
        w = int(row["weight"])

        u_name = name_map.get(u, f"User_{u}")
        v_name = name_map.get(v, f"User_{v}")

        if not G.has_node(u):
            G.add_node(u, display_name=u_name)
        if not G.has_node(v):
            G.add_node(v, display_name=v_name)

        blooms_dict = {}
        if (u, v) in bloom_breakdown.index:
            blooms_dict = bloom_breakdown.loc[(u, v)].to_dict()

        G.add_edge(u, v, weight=w, blooms=blooms_dict)

    return G

def compute_user_activity(questions_df, answers_df):
    activity = {}

    if not questions_df.empty and "owner_user_id" in questions_df.columns:
        q_counts = questions_df["owner_user_id"].dropna().astype(int).value_counts().to_dict()
        for uid, count in q_counts.items():
            activity[uid] = activity.get(uid, {"questions": 0, "answers": 0})
            activity[uid]["questions"] += count

    if not answers_df.empty and "owner_user_id" in answers_df.columns:
        a_counts = answers_df["owner_user_id"].dropna().astype(int).value_counts().to_dict()
        for uid, count in a_counts.items():
            activity[uid] = activity.get(uid, {"questions": 0, "answers": 0})
            activity[uid]["answers"] += count

    for uid in activity:
        activity[uid]["total_activity"] = activity[uid]["questions"] + activity[uid]["answers"]

    return activity

def filter_network_by_activity(graph, questions_df, answers_df, target_nodes=20):
    if graph.number_of_nodes() <= target_nodes:
        return graph.copy()

    activity = compute_user_activity(questions_df, answers_df)

    scored_nodes = []
    for n in graph.nodes():
        total_act = activity.get(n, {}).get("total_activity", 0)
        q_act = activity.get(n, {}).get("questions", 0)
        a_act = activity.get(n, {}).get("answers", 0)
        scored_nodes.append((n, total_act, a_act, q_act))

    # Sort descending by total activity, then answers, then questions
    scored_nodes.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    top_nodes = [item[0] for item in scored_nodes[:target_nodes]]

    subgraph = graph.subgraph(top_nodes).copy()
    for n in subgraph.nodes():
        act_info = activity.get(n, {"questions": 0, "answers": 0, "total_activity": 0})
        subgraph.nodes[n]["questions"] = act_info["questions"]
        subgraph.nodes[n]["answers"] = act_info["answers"]
        subgraph.nodes[n]["total_activity"] = act_info["total_activity"]

    return subgraph

def get_network_summary(graph):
    total_nodes = graph.number_of_nodes()
    total_unique_directed_pairs = graph.number_of_edges()
    total_answers_exchanged = sum(data.get("weight", 1) for _, _, data in graph.edges(data=True))
    isolated_nodes = len(list(nx.isolates(graph)))
    return {
        "total_nodes": total_nodes,
        "unique_directed_pairs": total_unique_directed_pairs,
        "total_answers_exchanged": total_answers_exchanged,
        "isolated_nodes": isolated_nodes
    }
