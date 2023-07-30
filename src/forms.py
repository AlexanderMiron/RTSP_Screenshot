import os

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Regexp

from config import RTSP_STREAMS
from functions import get_stream


def stream_name_check(form, field):
    if get_stream(field.data):
        raise ValidationError(f'This name "{field.data}" already exists.')


def stream_url_check(form, field):
    for stream in RTSP_STREAMS:
        if field.data == stream['url']:
            raise ValidationError(f'This url "{field.data}" already exists.')


def stream_folder_exist(form, field):
    stream_folder = os.path.join('images', field.data)
    if os.path.exists(stream_folder):
        raise ValidationError(f'Folder with name "{field.data}" already exists.')


class RTSPURLValidator(Regexp):
    def __init__(self, message="Invalid RTSP URL."):
        regex = r'^[a-z]+://[^\s/$.?#].[^\s]*$'
        super().__init__(regex, message=message)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class StreamForm(FlaskForm):
    url = StringField('URL', validators=[DataRequired(), RTSPURLValidator()])
    name = StringField('Name', validators=[DataRequired()])
    interval = IntegerField('Interval', validators=[NumberRange(min=1)])


class AddStreamForm(StreamForm):
    name = StringField('Name', validators=[DataRequired(), stream_name_check, stream_folder_exist])
    url = StringField('URL', validators=[DataRequired(), RTSPURLValidator(), stream_url_check])


class EditStreamForm(StreamForm):
    save_images = BooleanField('Save images', default=True)
    resize = BooleanField('Resize', default=False)
    im_res_width = IntegerField("Image width", default=1920)
    im_res_height = IntegerField("Image height", default=1080)
    extension = SelectField("Extension",
                            choices=[('.jpg', 'JPG'), ('.jp2', 'JPEG 2000'), ('.webp', 'WEBP'), ('.png', 'PNG')])
    use_flags = BooleanField('Use quality flags', default=False)
    jpg_quality = IntegerField('JPG Quality (0-100)', validators=[NumberRange(min=0, max=100)], default=95)
    jpg_optimize = IntegerField('JPG Optimize (0-1)', validators=[NumberRange(min=0, max=1)], default=0)
    jp2_compression = IntegerField('JPEG 2000 Compression (0-1000)',
                                   validators=[NumberRange(min=0, max=1000)], default=1000)
    webp_quality = IntegerField('Webp Quality (1-100)', validators=[NumberRange(min=1, max=100)], default=100)
    png_compression = IntegerField('PNG Compression', validators=[NumberRange(min=0, max=9)], default=1)
