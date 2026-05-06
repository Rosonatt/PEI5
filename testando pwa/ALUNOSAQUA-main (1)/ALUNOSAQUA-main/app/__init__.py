from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.secret_key = 'chave-secreta-do-projeto-alunosaqua'

    socketio.init_app(app)

    with app.app_context():
        from .routes import main_bp, aluno_bp, pais_bp, professor_bp, psicopedagogo_bp
        from .admin_routes import admin_bp
        from . import chat_events 

        app.register_blueprint(main_bp)
        app.register_blueprint(aluno_bp)
        app.register_blueprint(pais_bp)
        app.register_blueprint(professor_bp)
        app.register_blueprint(psicopedagogo_bp)
        app.register_blueprint(admin_bp)

    return app