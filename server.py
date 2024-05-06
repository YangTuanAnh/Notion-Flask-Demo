from flask import Flask, redirect, url_for, request, jsonify
from flask_dance.consumer import OAuth2ConsumerBlueprint
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import requests
import  dotenv

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

@app.route("/note", methods=['GET', 'POST', "PATCH"])
def get_resource():
    resource_id = request.args.get('id')
    resource_name = request.args.get('name')
    resource_index = request.args.get('index')
    
    if resource_id is None:
        return jsonify({'error': 'No id parameter provided'}), 400
    
    # if not notion_blueprint.session.authorized:
    #     return redirect(url_for("notion.login"))

    # session = notion_blueprint.session
    
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
        
    elif request.method=="POST":
        data = {
            "parent" : {"database_id": resource_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": resource_name
                            }
                        }
                    ]
                }
            }
        }
        resp = requests.post('https://api.notion.com/v1/pages', headers=headers, json=data)
        
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
                    "title": [
                        {
                            "text": {
                                "content": resource_name
                            }
                        }
                    ]
                }
            }
        }
        
        resp = requests.patch(f'https://api.notion.com/v1/pages/{page_id}', headers=headers, json=data)
        
    return jsonify(resp.json()), resp.status_code

if __name__ == '__main__':
    app.run(debug=True)