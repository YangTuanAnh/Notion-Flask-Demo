import streamlit as st
from requests_oauthlib import OAuth2Session
import requests

# Notion OAuth details
client_id = st.secrets['NOTION_OAUTH_CLIENT_ID']
client_secret = st.secrets['NOTION_OAUTH_CLIENT_SECRET']
redirect_uri = st.secrets['REDIRECT_URI']  # Your redirect URI

assert client_id, 'Must specify NOTION_OAUTH_CLIENT_ID environment variable'
assert client_secret, 'Must specify NOTION_OAUTH_CLIENT_SECRET environment variable'

if 'access_token' not in st.session_state:
    st.session_state.access_token = None

# OAuth session
notion_auth_url = 'https://api.notion.com/v1/oauth/authorize'
notion_token_url = 'https://api.notion.com/v1/oauth/token'

# Function to handle authentication
def get_notion_token():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
    authorization_url, state = oauth.authorization_url(notion_auth_url)
    
    # Redirect to Notion's authorization URL
    st.write("Click the link to authenticate with Notion")
    st.write(authorization_url)
    
    # Get token after redirection
    code = st.query_params.get("code", None)
    
    try:
        if code:
            token = oauth.fetch_token(notion_token_url, client_secret=client_secret, code=code)
            st.session_state.access_token = token['access_token']
    except: pass

# Main Streamlit app
def main():
    st.title('Notion Integration with Streamlit')
    
    if st.session_state.access_token is None:
        get_notion_token()
        return
    
    st.write(st.session_state.access_token)
    st.write("Successfully authenticated with Notion!")
    
    # Sidebar for navigation
    page = st.sidebar.selectbox("Select Operation", ["Create", "Read", "Update", "Delete"])

    # Input box for Database ID
    database_id = st.sidebar.text_input("Database ID")
    
    if database_id:
        DATABASE_URL = "https://api.notion.com/v1/databases/{database_id}/query"

        read_response = requests.post(
                DATABASE_URL.format(database_id=database_id),
                headers={"Authorization": f"Bearer {st.session_state.access_token}",
                         "Notion-Version": "2022-06-28"},
            )
        st.write("Read response:", read_response.json())
    # Now you can make requests to the Notion API using the obtained token
    # Example: use requests library to interact with Notion API

if __name__ == "__main__":
    main()