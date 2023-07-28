from flask import Flask
from flask_cors import *
from routes.api import api
from chatServer import ChatServer
'''attach the flask REST API'''
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.register_blueprint(api, url_prefix='/api')

# to run mongodb: `brew services start mongodb-community@6.0`

@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    '''run the chat server'''
    server = ChatServer(port=8088)
    server.start()
    app.run(host='127.0.0.1', port=8000, debug=False)