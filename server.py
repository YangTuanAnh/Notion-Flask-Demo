from flask import Flask, jsonify, redirect, url_for
from flask_dance.consumer import OAuth2ConsumerBlueprint
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import requests

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'wombles'

client_id = os.environ.get('NOTION_OAUTH_CLIENT_ID')
client_secret = os.environ.get('NOTION_OAUTH_CLIENT_SECRET')

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
    
    # headers = {
    #         'Authorization': f'Bearer {session.access_token}',
    #         'Content-Type': 'application/json',
    #         'Notion-Version': '2022-06-28',
    # }
    # # see https://developers.notion.com/reference/get-users
    # users = requests.get('https://api.notion.com/v1/users', headers=headers)

    return session.access_token

if __name__ == '__main__':
    app.run(debug=True)