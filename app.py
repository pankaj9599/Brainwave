import time
from flask import Flask, redirect, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room
import uuid


app = Flask(__name__)
socketio = SocketIO(app, 
                    cors_allowed_origins="*",
                    #max_http_buffer_size=9999999999
                    )

rooms = {}  # For simplicity, store rooms in-memory


    

@app.route('/create_room', methods=['POST'])
def create_room():
    room_id = uuid.uuid4().hex[:8] # short unique id for room
    if room_id in rooms:
        return jsonify(success=False, message="Room already exists"), 400
    rooms[room_id] = {"participants": []}
    return jsonify({
        "success": True,
        "room_id": room_id
    })

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    return jsonify(list(rooms.keys()))

@app.route('/delete_room/<room_id>', methods=['GET'])
def delete_room(room_id):
    del rooms[room_id]
    return jsonify({
        "success": True,
        "message": "Room deleted"
    })

@socketio.on('join')
def on_join(data):
    username = data['username']
    room_id = data['room_id']
    if room_id not in rooms:
        return {"success": False, "message": "Room not found"}
    join_room(room_id)
    rooms[room_id]["participants"].append(username)

    # Notify other users in the room about the new user
    for participant in rooms[room_id]["participants"]:
        if participant != username:
            socketio.emit('user_joined', {"username": username, "userId": request.sid}, room=participant)
            time.sleep(5)

    print(f"User {username} has joined room {room_id}")

    # Notify other users in the room about the new user
    socketio.emit('user_joined', {"username": username, "userId": request.sid}, room=room_id)
    

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room_id = data['room_id']
    if room_id not in rooms:
        return {"success": False, "message": "Room not found"}
    leave_room(room_id)
    rooms[room_id]["participants"].remove(username)

    socketio.emit('user_left', {"username": username, "userId": request.sid}, room=room_id)

@socketio.on('signal')
def on_signal(data):
    target_user = data['userId']
    room_id = data['room_id']
    signal = data['signal']

    print(f"Signal from {request.sid} to {target_user}")
    # Send the signal to the specified user in the room
    socketio.emit('signal', {"userId": request.sid, "signal": signal}, room=target_user)


@socketio.on('request_new_stream')
def on_request_new_stream(data):
    target_user = data['userId']
    room_id = data['room_id']

    socketio.emit('create_new_offer', {'fromUserId': request.sid}, room=target_user)

@socketio.on('transcript_message')
def handle_transcript_message(data):
    username = data['username']
    transcript = data['transcript']
    room_id = data['room_id']
    socketio.emit('broadcast_transcript', {'username': username, 'transcript': transcript}, room=room_id)


@socketio.on('new_message')
def handle_new_message(data):
    message = data['message']
    username = data['username']
    room_id = data['room_id']  

    socketio.emit('message_received', {'message': message, 'username': username}, room=room_id, include_self=False)

@app.route('/room_join/<room_id>')
def room_join(room_id):
    if room_id in rooms.keys():
        return render_template('second_page.html', room_id=room_id)
    
    return redirect('/')

@app.route('/')
def index():
    return render_template('first_page.html')

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5001, debug=True)
