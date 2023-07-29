from flask import Flask, render_template, request, redirect, abort, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import logging
from logging.handlers import RotatingFileHandler
from forms import AddStreamForm, EditStreamForm, LoginForm
from config import RTSP_STREAMS, SECRET_KEY, USERS
from functions import (get_stream, load_state, save_state,
                       get_index_context, save_image_from_stream,
                       load_scheduler, add_scheduler_job)
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.secret_key = SECRET_KEY
login_manager = LoginManager(app)
scheduler = BackgroundScheduler()
scheduler.start()


class User(UserMixin):
    def __init__(self, username, password):
        self.id = username
        self.password = password


@app.template_filter('ternary')
def ternary(value, true_value, false_value):
    return true_value if value else false_value


@login_manager.user_loader
def load_user(user_id):
    user_data = USERS.get(user_id)
    if user_data:
        return User(user_id, user_data['password'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user_data = USERS.get(username)
        if user_data and user_data['password'] == password:
            user = User(username, password)
            login_user(user)
            return redirect('/')
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/')
@login_required
def index():
    return render_template('index.html', streams=get_index_context(), form=AddStreamForm())


@app.route('/add_stream', methods=['POST'])
@login_required
def add_stream():
    form = AddStreamForm()
    if form.validate_on_submit():
        data = form.data
        data.pop('csrf_token')
        RTSP_STREAMS.append(data)
        save_state()
        add_scheduler_job(scheduler, data)
        app.logger.info(f"Added new stream: {data['name']} (URL: {data['url']}, Interval: {data['interval']}s)")
        return redirect('/')
    return render_template('add_stream.html', form=form)


@app.route('/edit_stream/<stream_name>', methods=['GET', 'POST'])
@login_required
def edit_stream(stream_name):
    stream = get_stream(stream_name)
    if not stream:
        abort(404)

    if request.method == 'GET':
        form = EditStreamForm(data=stream)
        return render_template('edit_page.html', stream=stream, form=form)
    else:
        form = EditStreamForm()
        if form.validate_on_submit():
            data = form.data
            data.pop('csrf_token')
            stream.update(data)
            scheduler.remove_job(stream_name)
            add_scheduler_job(scheduler, stream)
            app.logger.info(f"Edited stream: {stream_name}")
            save_state()
            return redirect('/')
        return render_template('edit_page.html', stream=stream, form=form)


@app.route('/delete_stream', methods=['POST'])
@login_required
def delete_stream():
    stream_name = request.json['stream_name']
    stream = get_stream(stream_name)
    if not stream:
        abort(404)
    scheduler.remove_job(stream_name)
    RTSP_STREAMS.remove(stream)
    app.logger.info(f"Deleted stream: {stream_name}")
    save_state()
    return redirect('/')


@app.route('/save_image/<stream_name>')
@login_required
def save_image_route(stream_name):
    stream = get_stream(stream_name)
    save_result = save_image_from_stream(stream)
    return redirect('/')


def create_app():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler = RotatingFileHandler('app.log', maxBytes=1024 * 1024, backupCount=5)
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    load_state()
    load_scheduler(scheduler)
    return app


if __name__ == '__main__':
    create_app()
    app.run()
