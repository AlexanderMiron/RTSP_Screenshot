import os

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SelectField, PasswordField, SubmitField, TimeField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Regexp, Optional, StopValidation

from config import RTSP_STREAMS
from functions import get_stream


def stream_name_check(_, field):
    if get_stream(field.data):
        raise ValidationError(f'This name "{field.data}" already exists.')


def stream_url_check(_, field):
    for stream in RTSP_STREAMS:
        if field.data == stream['url']:
            raise ValidationError(f'This url "{field.data}" already exists.')


def stream_folder_exist(_, field):
    stream_folder = os.path.join('images', field.data)
    if os.path.exists(stream_folder):
        raise ValidationError(f'Folder with name "{field.data}" already exists.')


class RequiredTogether(object):
    def __init__(self, req_field, message=None):
        self.req_field = req_field
        self.message = message if message else f'This field must be filled in the same w' \
                                               f'ay as the "{self.req_field}" field is filled.'

    def __call__(self, form, field):
        if getattr(form, self.req_field).data and not field.data:
            raise StopValidation(self.message)


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


class SaveTimeInterval(StreamForm):
    use_save_time_interval = BooleanField('Use save time interval', default=False)
    save_time_start = TimeField('Save time start', validators=[RequiredTogether('use_save_time_interval'), Optional()])
    save_time_end = TimeField('Save time end', validators=[RequiredTogether('use_save_time_interval'), Optional()])


class EditStreamForm(SaveTimeInterval):
    save_images = BooleanField('Save images', default=True)
    resize = BooleanField('Resize', default=False)
    im_res_width = IntegerField("Image width", validators=[RequiredTogether('resize'), Optional()])
    im_res_height = IntegerField("Image height", validators=[RequiredTogether('resize'), Optional()])
    extension = SelectField("Extension",
                            choices=[('.jpg', 'JPG'), ('.jp2', 'JPEG 2000'), ('.webp', 'WEBP'), ('.png', 'PNG')]
                            )
    use_flags = BooleanField('Use quality flags', default=False)
    jpg_quality = IntegerField('JPG Quality (0-100)', validators=[NumberRange(min=0, max=100)], default=95)
    jpg_optimize = IntegerField('JPG Optimize (0-1)', validators=[NumberRange(min=0, max=1)], default=0)
    jp2_compression = IntegerField('JPEG 2000 Compression (0-1000)',
                                   validators=[NumberRange(min=0, max=1000)], default=1000)
    webp_quality = IntegerField('Webp Quality (1-100)', validators=[NumberRange(min=1, max=100)], default=100)
    png_compression = IntegerField('PNG Compression (0-9)', validators=[NumberRange(min=0, max=9)], default=1)
