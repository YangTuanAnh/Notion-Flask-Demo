from flask import Flask, redirect, url_for, request, jsonify
from flask_dance.consumer import OAuth2ConsumerBlueprint
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import requests
import dotenv
from supabase import create_client, Client
from transformers import AutoTokenizer, AutoModel
from utils import average_pool
from torch import no_grad
import json

dotenv.load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'wombles'

client_id = os.environ.get('NOTION_OAUTH_CLIENT_ID')
client_secret = os.environ.get('NOTION_OAUTH_CLIENT_SECRET')
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
access_token = os.environ.get("ACCESS_TOKEN")

assert client_id, 'Must specify NOTION_OAUTH_CLIENT_ID environment variable'
assert client_secret, 'Must specify NOTION_OAUTH_CLIENT_SECRET environment variable'

supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')

assert supabase_url, 'Must specify SUPABASE_URL environment variable'
assert supabase_key, 'Must specify SUPABASE_KEY environment variable'

awan_key = os.environ.get("AWAN_KEY")

assert awan_key, 'Must specify AWAN_KEY environment variable'

supabase: Client = create_client(supabase_url, supabase_key)

notion_blueprint = OAuth2ConsumerBlueprint(
    "notion",
    __name__,
    client_id=client_id,
    client_secret=client_secret,
    base_url="https://api.notion.com",
    token_url="https://api.notion.com/v1/oauth/token",
    authorization_url="https://api.notion.com/v1/oauth/authorize",
)

app.register_blueprint(notion_blueprint, url_prefix="/login")

@app.route('/logout')
def logout():
    notion_blueprint.session.teardown_session()
    return redirect('/')

@app.route("/")
def index():
    if not notion_blueprint.session.authorized:
        return redirect(url_for("notion.login"))

    session = notion_blueprint.session
    
    print(session.access_token)
    headers = {
            'Authorization': f'Bearer {session.access_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28',
    }
    # see https://developers.notion.com/reference/get-users
    users = requests.get('https://api.notion.com/v1/users', headers=headers)

    return jsonify(users.json()), 200

tokenizer = AutoTokenizer.from_pretrained("Supabase/gte-small")
model = AutoModel.from_pretrained("Supabase/gte-small")

@app.route("/notes", methods=['GET', 'POST', "PATCH", "DELETE"])
def get_resource():
    resource_id = request.args.get('id')
    resource_name = request.args.get('name', "")
    resource_desc = request.args.get('desc', "")
    resource_index = request.args.get('index')
    clear_all = request.args.get("clear_all")
    
    if resource_id is None:
        return jsonify({'error': 'No id parameter provided'}), 400
    
    # if not notion_blueprint.session.authorized:
    #     return redirect(url_for("notion.login"))

    # session = notion_blueprint.session
    
    # access_token = ""
    headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28',
    }
    if request.method=="GET":
        resp = requests.post(f'https://api.notion.com/v1/databases/{resource_id}/query', headers=headers, json={
            "sorts": [
                {
                "property": "Last edited time",
                "direction": "descending"
                }
            ],
        })
        
        data = resp.json()
        queries = data['results']
        
        all_string_values = []
        for q in queries:
            string_values = []
            for key, value in q['properties'].items():
                # Check if the value is a string
                if value['type'] in ['title', 'rich_text']:
                    # Extract the text content from the property
                    text = ''.join([item['plain_text'] for item in value[value['type']]])
                    string_values.append(text)
                    
            all_string_values.append(" ".join(string_values))
        
        batch_dict = tokenizer(all_string_values, max_length=512, padding=True, truncation=True, return_tensors='pt')

        with no_grad():
            outputs = model(**batch_dict)
            embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            
        embeddings = embeddings.tolist()
        
        data = supabase.table("notes").upsert([
            {
                "id": q['id'],
                "parent_id": q['parent']['database_id'],
                "content": content,
                "embedding": emb
            } 
            for q, emb, content in zip(queries, embeddings, all_string_values)]).execute()

        assert len(data.data) > 0
        
    elif request.method=="POST":
        data = {
            "parent" : {"database_id": resource_id},
            "properties": {
                "Name": {
                    "title": [{ "text": { "content": resource_name }}]
                },
                "Description": {
                    "rich_text": [{ "text": { "content": resource_desc }}]
                }
            }
        }
        resp = requests.post('https://api.notion.com/v1/pages', headers=headers, json=data)
        
        batch_dict = tokenizer(resource_name + " " + resource_desc, max_length=512, padding=True, truncation=True, return_tensors='pt')

        with no_grad():
            outputs = model(**batch_dict)
            embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            
        embeddings = embeddings.tolist()
        
        page_content = resp.json()
        print(page_content)
        
        data = supabase.table("notes").upsert(
            {
                "id": page_content['id'],
                "parent_id": page_content['parent']['database_id'],
                "title": resource_name,
                "content": resource_name + " " + resource_desc,
                "embedding": embeddings[0]
            } 
            ).execute()

        assert len(data.data) > 0
        
    elif request.method=="PATCH":
        if resource_index is None:
            return jsonify({'error': 'No index parameter provided'}), 400
        resource_index = int(resource_index)
        
        resp = requests.post(f'https://api.notion.com/v1/databases/{resource_id}/query', headers=headers, json={
            "sorts": [
                {
                "property": "Last edited time",
                "direction": "descending"
                }
            ],
        })
        
        data = resp.json()
        queries = data['results']
        
        if len(queries) <= resource_index:
            return jsonify({'error': 'Index exceeds database length'}), 400
        
        page_id = queries[resource_index]['id']
        
        data = {
            "parent" : {"database_id": resource_id},
            "properties": {
                "Name": {
                    "title": [{ "text": { "content": resource_name }}]
                },
                "Description": {
                    "rich_text": [{ "text": { "content": resource_desc }}]
                }
            }
        }
        
        resp = requests.patch(f'https://api.notion.com/v1/pages/{page_id}', headers=headers, json=data)
        
        batch_dict = tokenizer(resource_name + " " + resource_desc, max_length=512, padding=True, truncation=True, return_tensors='pt')

        with no_grad():
            outputs = model(**batch_dict)
            embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            
        embeddings = embeddings.tolist()
        
        page_content = resp.json()
        
        data = supabase.table("notes").upsert(
            {
                "id": page_content['id'],
                "parent_id": page_content['parent']['database_id'],
                "title": resource_name,
                "content": resource_name + " " + resource_desc,
                "embedding": embeddings[0]
            } 
            ).execute()

        assert len(data.data) > 0
        
    elif request.method=="DELETE":
        if resource_index is None:
            return jsonify({'error': 'No index parameter provided'}), 400
        resource_index = int(resource_index)
        
        resp = requests.post(f'https://api.notion.com/v1/databases/{resource_id}/query', headers=headers, json={
            "sorts": [
                {
                "property": "Last edited time",
                "direction": "descending"
                }
            ],
        })
        
        data = resp.json()
        queries = data['results']
        
        if clear_all == "true":
            for q in queries:
                page_id = q[resource_index]['id']
            
                resp = requests.patch(f'https://api.notion.com/v1/pages/{page_id}', headers=headers, json={
                    "in_trash": True
                })
            
            resp = supabase.table("notes").delete().execute()
            
        else:
            if len(queries) <= resource_index:
                return jsonify({'error': 'Index exceeds database length'}), 400
            
            page_id = queries[resource_index]['id']
            
            resp = requests.patch(f'https://api.notion.com/v1/pages/{page_id}', headers=headers, json={
                "in_trash": True
            })
            
            data = supabase.table("notes").delete().eq("page_id", page_id).execute()
        
    return jsonify(resp.json()), resp.status_code

@app.route("/query", methods=['POST'])
def send_prompt():
    resource_id = request.args.get('id')
    prompt = request.args.get('prompt', "")
    
    if resource_id is None:
        return jsonify({'error': 'No id parameter provided'}), 400
    
    if len(prompt) < 0:
        return jsonify({'error': 'No prompt parameter provided'}), 400
    
    batch_dict = tokenizer(prompt, max_length=512, padding=True, truncation=True, return_tensors='pt')

    with no_grad():
        outputs = model(**batch_dict)
        embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
        
    embeddings = embeddings.tolist()
    
    resp = supabase.rpc('match_documents', {
        "database_id": resource_id,
        "query_embedding": embeddings[0], 
        "match_threshold": 0.78,
        "match_count": 10,
    }).execute()
    
    prompt = f"Please answer this question, provided the question and context here, don't use your own knowledge unless specified\n\nQuestion: {prompt}\n\nContext:\n"
    for query in resp.data:
        prompt+=query['content']+"\n"
    print(prompt)
    
    headers = {
            'Authorization': f'Bearer {awan_key}',
            'Content-Type': 'application/json'
    }
    
    resp = requests.post("https://api.awanllm.com/v1/completions", headers=headers, json={
        "model": "Meta-Llama-3-8B-Instruct",
        "prompt": prompt,
    })
    
    return jsonify(resp.json()), resp.status_code
    
if __name__ == '__main__':
    app.run(debug=True)
    
# parent_id
# page_id [pk]
# vector

# k -> page_id