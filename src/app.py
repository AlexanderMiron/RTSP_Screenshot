import datetime
import logging
import os
import shutil
import zipfile
from io import BytesIO
from logging.handlers import RotatingFileHandler

from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, abort, flash, send_from_directory, send_file, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from config import RTSP_STREAMS, SECRET_KEY, USERS
from forms import AddStreamForm, EditStreamForm, LoginForm
from functions import (get_stream, load_state, save_state,
                       get_index_context, save_image_from_stream,
                       load_scheduler, add_scheduler_job,
                       get_folder_by_stream_name, check_disk_space)

app = Flask(__name__)
app.secret_key = SECRET_KEY
login_manager = LoginManager(app)
scheduler = BackgroundScheduler()
scheduler.start()


class User(UserMixin):
    def __init__(self, username, password):
        self.id = username
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    user_data = USERS.get(user_id)
    if user_data:
        return User(user_id, user_data['password'])


@app.template_filter('ternary')
def ternary(value, true_value, false_value):
    return true_value if value else false_value


@app.template_filter('format_timestamp')
def format_timestamp(value):
    try:
        dt = datetime.datetime.fromtimestamp(value)
        formatted = dt.strftime('%Y-%m-%d %H:%M:%S')  # Форматирование как в примере
        return formatted
    except Exception as e:
        return value


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


@app.route('/<stream_name>/list_files')
@login_required
def list_files(stream_name):
    folder = get_folder_by_stream_name(stream_name)
    folder_size = 0
    for file in os.scandir(folder):
        folder_size += os.path.getsize(file)
    files = os.scandir(folder)
    files = sorted(files, key=lambda e: e.name)
    return render_template('list_files.html', files=files, stream_name=stream_name, folder_size=folder_size)


@app.route('/<stream_name>/<filename>')
@login_required
def download_file(stream_name, filename):
    return send_from_directory(get_folder_by_stream_name(stream_name), filename, as_attachment=True)


@app.route('/<stream_name>/download_all')
@login_required
def download_all(stream_name):
    zip_filename = f'{stream_name}.zip'
    image_folder = get_folder_by_stream_name(stream_name)
    temp_zip_path = 'temp'
    os.makedirs(temp_zip_path, exist_ok=True)
    temp_zip_filename = os.path.join(temp_zip_path, zip_filename)
    folder = get_folder_by_stream_name(stream_name)
    folder_size = 0
    for file in os.scandir(folder):
        folder_size += os.path.getsize(file)
    check_disk_space(temp_zip_path, required_space=((folder_size * 1024 ** 3) + 1))

    with zipfile.ZipFile(temp_zip_filename, 'w') as zipf:
        for file in os.listdir(image_folder):
            file_path = os.path.join(image_folder, file)
            zipf.write(file_path, file)

    return send_from_directory(temp_zip_path, zip_filename)


@app.route('/<stream_name>/thumbnail/<filename>')
@login_required
def thumbnail(stream_name, filename):
    file_path = os.path.join(get_folder_by_stream_name(stream_name), filename)
    try:
        img_io = BytesIO()
        image = Image.open(file_path)
        image.thumbnail((80, 80))
        image.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except (OSError, IOError):
        return 'Ошибка обработки изображения', 500


@app.route('/<stream_name>/clear_folder')
@login_required
def clear_folder(stream_name):
    folder = get_folder_by_stream_name(stream_name)
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            pass
    return redirect(url_for('list_files', stream_name=stream_name))


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
