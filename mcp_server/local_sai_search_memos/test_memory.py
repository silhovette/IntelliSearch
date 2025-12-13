import os
import uuid
import json
import requests
import dotenv

dotenv.load_dotenv(override=True)


def query_memory(query: str, conversation_id: str = None):
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    data = {
        "query": query,
        "user_id": "memos_user_geekcenter",
        "conversation_id": conversation_id,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {os.environ['MEMOS_API_KEY']}",
    }
    url = f"{os.environ['MEMOS_BASE_URL']}/search/memory"
    res = requests.post(url=url, headers=headers, data=json.dumps(data))
    print(f"Result:\n{json.dumps(res.json(), ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    query_memory("上海交通大学 人工智能学院 素拓")
