import os
import json
import datetime
import requests
import pandas as pd

STACK_API_BASE = "https://api.stackexchange.com/2.3"

def fetch_questions(tag="python", page_size=30):
    url = f"{STACK_API_BASE}/questions"
    params = {
        "order": "desc",
        "sort": "activity",
        "tagged": tag,
        "site": "stackoverflow",
        "pagesize": page_size,
        "filter": "withbody"
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])

def fetch_answers_for_questions(question_ids, max_pages=3):
    if not question_ids:
        return []
    ids_str = ";".join(str(qid) for qid in question_ids[:100])
    url = f"{STACK_API_BASE}/questions/{ids_str}/answers"
    all_answers = []
    
    for page in range(1, max_pages + 1):
        params = {
            "order": "desc",
            "sort": "activity",
            "site": "stackoverflow",
            "pagesize": 100,
            "page": page,
            "filter": "withbody"
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        all_answers.extend(items)
        if not data.get("has_more", False):
            break
            
    return all_answers

def parse_and_export_data(questions, answers, output_dir="data/raw", tag="python"):
    os.makedirs(output_dir, exist_ok=True)
    
    q_rows = []
    users_dict = {}
    
    for q in questions:
        owner = q.get("owner", {})
        uid = owner.get("user_id")
        display_name = owner.get("display_name", "Anonymous")
        reputation = owner.get("reputation", 0)
        
        if uid:
            users_dict[uid] = {
                "user_id": uid,
                "display_name": display_name,
                "reputation": reputation,
                "user_type": owner.get("user_type", "registered")
            }
            
        q_rows.append({
            "question_id": q.get("question_id"),
            "title": q.get("title", ""),
            "body": q.get("body", ""),
            "owner_user_id": uid,
            "owner_name": display_name,
            "score": q.get("score", 0),
            "view_count": q.get("view_count", 0),
            "answer_count": q.get("answer_count", 0),
            "tags": ";".join(q.get("tags", [])),
            "creation_date": q.get("creation_date", 0)
        })
        
    a_rows = []
    for a in answers:
        owner = a.get("owner", {})
        uid = owner.get("user_id")
        display_name = owner.get("display_name", "Anonymous")
        reputation = owner.get("reputation", 0)
        
        if uid:
            if uid not in users_dict:
                users_dict[uid] = {
                    "user_id": uid,
                    "display_name": display_name,
                    "reputation": reputation,
                    "user_type": owner.get("user_type", "registered")
                }
                
        a_rows.append({
            "answer_id": a.get("answer_id"),
            "question_id": a.get("question_id"),
            "owner_user_id": uid,
            "owner_name": display_name,
            "score": a.get("score", 0),
            "is_accepted": a.get("is_accepted", False),
            "creation_date": a.get("creation_date", 0)
        })
        
    q_df = pd.DataFrame(q_rows)
    a_df = pd.DataFrame(a_rows)
    u_df = pd.DataFrame(list(users_dict.values()))
    
    q_path = os.path.join(output_dir, "questions.csv")
    a_path = os.path.join(output_dir, "answers.csv")
    u_path = os.path.join(output_dir, "users.csv")
    
    q_df.to_csv(q_path, index=False)
    a_df.to_csv(a_path, index=False)
    u_df.to_csv(u_path, index=False)
    
    metadata = {
        "collection_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "selected_tag": tag,
        "total_questions": len(q_df),
        "total_answers": len(a_df),
        "total_users": len(u_df),
        "api_endpoint": STACK_API_BASE,
        "status": "actual_api_data"
    }
    meta_path = os.path.join(output_dir, "collection_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Exported {len(q_df)} questions, {len(a_df)} answers, and {len(u_df)} users to {output_dir}")
    return q_df, a_df, u_df

def run_collection(tag="python", output_dir="data/raw", offline=False):
    os.makedirs(output_dir, exist_ok=True)
    q_path = os.path.join(output_dir, "questions.csv")
    a_path = os.path.join(output_dir, "answers.csv")
    u_path = os.path.join(output_dir, "users.csv")

    if offline:
        if os.path.exists(q_path) and os.path.exists(a_path) and os.path.exists(u_path):
            print(f"[Offline Mode] Loading existing raw dataset from {output_dir}...")
            q_df = pd.read_csv(q_path)
            a_df = pd.read_csv(a_path)
            u_df = pd.read_csv(u_path)
            return q_df, a_df, u_df
        else:
            raise FileNotFoundError(
                f"Raw dataset missing in {output_dir}. Run live extraction first without --offline."
            )

    print(f"Extracting StackOverflow questions for tag: '{tag}' via API...")
    try:
        questions = fetch_questions(tag=tag, page_size=30)
        q_ids = [q["question_id"] for q in questions if "question_id" in q]
        answers = fetch_answers_for_questions(q_ids, max_pages=3)
        return parse_and_export_data(questions, answers, output_dir=output_dir, tag=tag)
    except Exception as e:
        print(f"API extraction failed: {e}")
        if os.path.exists(q_path) and os.path.exists(a_path) and os.path.exists(u_path):
            print(f"Falling back to existing local dataset in {output_dir}...")
            q_df = pd.read_csv(q_path)
            a_df = pd.read_csv(a_path)
            u_df = pd.read_csv(u_path)
            return q_df, a_df, u_df
        raise
