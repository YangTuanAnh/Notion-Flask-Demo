import streamlit as st
import requests

st.title('Notion Database CRUD')

# Input fields for Notion token and database ID
notion_token = st.text_input('Enter Notion Integration Token:')
database_id = st.text_input('Enter Notion Database ID:')

# Create
st.subheader('Create Item')
name = st.text_input('Name')
description = st.text_area('Description')
if st.button('Create'):
    response = requests.post(
        f'https://api.notion.com/v1/pages',
        headers={
            'Authorization': f'Bearer {notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2021-05-13',
        },
        json={
            'parent': {'database_id': database_id},
            'properties': {
                'Name': {'title': [{'text': {'content': name}}]},
                'Description': {'rich_text': [{'text': {'content': description}}]},
            }
        }
    )
    st.write(response.text)

# Read
st.subheader('Read Items')
if st.button('Fetch Items'):
    response = requests.get(
        f'https://api.notion.com/v1/databases/{database_id}/query',
        headers={'Authorization': f'Bearer {notion_token}', 'Notion-Version': '2021-05-13'}
    )
    items = response.json().get('results', [])
    for item in items:
        st.write(item['properties']['Name']['title'][0]['text']['content'])

# Update
st.subheader('Update Item')
update_name = st.text_input('New Name')
update_description = st.text_area('New Description')
update_id = st.text_input('Enter ID of item to update')
if st.button('Update'):
    response = requests.patch(
        f'https://api.notion.com/v1/pages/{update_id}',
        headers={
            'Authorization': f'Bearer {notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2021-05-13',
        },
        json={
            'properties': {
                'Name': {'title': [{'text': {'content': update_name}}]},
                'Description': {'rich_text': [{'text': {'content': update_description}}]},
            }
        }
    )
    st.write(response.text)

# Delete
st.subheader('Delete Item')
delete_id = st.text_input('Enter ID of item to delete')
if st.button('Delete'):
    response = requests.delete(
        f'https://api.notion.com/v1/pages/{delete_id}',
        headers={'Authorization': f'Bearer {notion_token}', 'Notion-Version': '2021-05-13'}
    )
    st.write(response.text)
