from flask import request, session
from flask_socketio import emit, join_room
from . import socketio
from .models import CHAT_MESSAGES, salvar_banco
from datetime import datetime

@socketio.on('join')
def on_join(data):
    room = f"{session.get('escola_id')}_{data['room']}"
    join_room(room)
    
    if room in CHAT_MESSAGES:
        emit('history', CHAT_MESSAGES[room], to=request.sid)

@socketio.on('send_message')
def handle_message(data):
    room = f"{session.get('escola_id')}_{data['room']}"
    msg_data = {
        'sender': session.get('display_name'),
        'msg': data['message'],
        'is_psico': data.get('is_psico', False),
        'timestamp': datetime.now().strftime('%H:%M')
    }
    
    if room not in CHAT_MESSAGES:
        CHAT_MESSAGES[room] = []
    
    CHAT_MESSAGES[room].append(msg_data)
    salvar_banco()
    
    emit('receive_message', msg_data, room=room)