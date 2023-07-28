from flask import Blueprint
from flask import jsonify, request
#from chatServer import global_clients
import json
import pymongo
from bson.objectid import ObjectId
import uuid

api = Blueprint('api', __name__)

online_user = []

client = pymongo.MongoClient("localhost", 27017)
db = client["chatApp"]
# test database connectivity
try:
    print(client.server_info())
except Exception:
    print("Unable to connect to mongodb")
'''
{
    username: String
    password: String
    session: List of session id
}
'''
users = db['user']
for u in users.find():
    print('users:', u)
'''
{
    id: String
    members: List of username
    history: 
    List of {
        content: String
        sender: username
        time: datatime
    }
}
'''
chat_sessions = db['chatSession']
for s in chat_sessions.find():
    print('chat session:', s)

@api.route("/account/login/", methods=['GET'])
def login():
    '''process login requests'''
    req_body = request.args
    username = req_body['user']
    password = req_body['pass']
    print('u&p', username, password)
    if username is None:
        return jsonify({'message': "Missing username"}), 400
    elif password is None:
        return jsonify({'message': "Missing password"}), 400
    elif username in online_user:
        return jsonify({'message': "user already logged in"}), 400
    else:
        user = users.find_one({"username": username})
        if user is None:
            return jsonify({'message': "User does not exist"}), 404
        elif user['password'] != password:
            return jsonify({'message': "Password incorrect"}), 400
        else:
            online_user.append(user['username'])
            res = jsonify({
                'username': user['username'],
                '_id': str(user['_id'])
            })
            return res, 200


@api.route("/account/register/", methods=["GET"])
def register():
    '''process register requests'''
    req_body = request.args
    username = req_body['user']
    password = req_body['pass']
    #print('abc:', username, password)
    if username is None:
        return jsonify({'message': "Missing username"}), 400
    elif password is None:
        return jsonify({'message': "Missing password"}), 400
    elif username in online_user:
        return jsonify({'message': "Username already exists"}), 400
    else:
        user = users.find_one({"username": username})
        if user:
            return jsonify({'message': "Username already exists"}), 400
        else:
            id = users.insert_one({'username': username, 'password': password, 'session': []}).inserted_id
            res = jsonify({
                'username': username,
                '_id': str(id)
            })
            return res, 200


@api.route("/session/join/", methods=["GET"])
def join():
    '''process join requests for session'''
    req_body = request.args
    uId = req_body['user']
    sessionId = req_body['sessionId']
    print("uidsession:", uId,sessionId)
    # first verify the user
    user = users.find_one({'_id': ObjectId(uId)})
    if not user:
        print('User credentials incorrect, please log in again')
        return jsonify({'message': "User credentials incorrect"}), 400
    session = chat_sessions.find_one({'id': sessionId})
    if session: # session already exists
        new = {"$set": {'members': list(session['members'])+[uId]}}
        chat_sessions.update_one({'members': session['members']}, new)
        print(chat_sessions.find_one({'id': sessionId}))
        return jsonify({'message': 'success'}), 200
    else: 
        session = {
            'id': sessionId,
            'members': [uId],
            'history': []
        }
        chat_sessions.insert_one(session)
        return jsonify({'message': 'success'}), 200
