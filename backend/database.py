from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """
    configure and initialize the application database
    :param app: flask application instance
    :returns: none
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()
