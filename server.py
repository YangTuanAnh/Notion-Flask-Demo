from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/create', methods=['POST'])
def create_item():
    data = request.json
    # Make a request to Notion API to create a new item in the database
    response = requests.post(
        f'https://api.notion.com/v1/pages',
        headers={
            'Authorization': f'Bearer {data["token"]}',
            'Content-Type': 'application/json',
            'Notion-Version': '2021-05-13',
        },
        json={
            'parent': {'database_id': data["database_id"]},
            'properties': {
                'Name': {'title': [{'text': {'content': data['name']}}]},
                'Description': {'rich_text': [{'text': {'content': data['description']}}]},
            }
        }
    )
    return response.json(), response.status_code

@app.route('/read')
def read_items():
    # Make a request to Notion API to retrieve all items from the database
    response = requests.get(
        f'https://api.notion.com/v1/databases/{request.args.get("database_id")}/query',
        headers={'Authorization': f'Bearer {request.args.get("token")}', 'Notion-Version': '2021-05-13'}
    )
    return response.json(), response.status_code

@app.route('/update/<item_id>', methods=['PATCH'])
def update_item(item_id):
    data = request.json
    # Make a request to Notion API to update the item
    response = requests.patch(
        f'https://api.notion.com/v1/pages/{item_id}',
        headers={
            'Authorization': f'Bearer {data["token"]}',
            'Content-Type': 'application/json',
            'Notion-Version': '2021-05-13',
        },
        json={
            'properties': {
                'Name': {'title': [{'text': {'content': data['name']}}]},
                'Description': {'rich_text': [{'text': {'content': data['description']}}]},
            }
        }
    )
    return response.json(), response.status_code

@app.route('/delete/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    # Make a request to Notion API to delete the item
    response = requests.delete(
        f'https://api.notion.com/v1/pages/{item_id}',
        headers={'Authorization': f'Bearer {request.args.get("token")}', 'Notion-Version': '2021-05-13'}
    )
    return response.json(), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
