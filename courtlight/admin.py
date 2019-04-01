import os
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy_session import flask_scoped_session

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .highcourts.orm import get_session
from .highcourts.orm import Judgement, Judge, Case

app = Flask(__name__)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

admin = Admin(app, name='courtlight', template_mode='bootstrap3')

db_path = os.environ['DB_PATH']
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker()
Session.configure(bind=engine)
session = flask_scoped_session(Session, app)

class JudgementView(ModelView):
    can_delete = False
    can_edit = False
    can_create = False
    can_view_details = True
    column_filters = ['date', 'judges.name', 'cases.case_number', 'cases.party', 'text_content']
    column_searchable_list = ['text_content']
    can_export = True

    inline_models = (Case, Judge)

    column_list = ['date', 'pdf_link', 'text_content', 'judges', 'cases']
    column_labels = {
        'date': 'Date of Judgement',
        'pdf_link': 'View Judgement',
        'text_content': 'Judgement Text',
        'cases': 'Case Numbers'
    }

admin.add_view(JudgementView(Judgement, session))

if __name__ == '__main__':
    app.run()