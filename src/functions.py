import datetime
import json
import os

import cv2

from config import RTSP_STREAMS, IMAGE_FOLDER


def add_scheduler_job(scheduler, stream):
    scheduler.add_job(
        save_image_from_stream,
        'interval',
        [stream],
        minutes=stream['interval'],
        id=stream['name']
    )


def load_scheduler(scheduler):
    for stream in RTSP_STREAMS:
        if 'save_images' not in stream or stream['save_images']:
            add_scheduler_job(scheduler, stream)


def get_folder_by_stream_name(stream_name):
    return os.path.join(IMAGE_FOLDER, get_stream(stream_name)['name'])


def get_index_context():
    context = []
    for cam in RTSP_STREAMS:
        context.append(cam.copy())
        try:
            context[-1].update({"screenshots": len(os.listdir(os.path.join(IMAGE_FOLDER, cam['name'])))})
        except FileNotFoundError:
            context[-1].update({"screenshots": 0})
        context[-1].update({'info': get_stream_info(cam['url'])})
    return context


def get_stream(stream_name):
    for stream in RTSP_STREAMS:
        if stream['name'] == stream_name:
            return stream
    return None


def load_with_datetime(pairs):
    d = {}
    converters = [
        datetime.datetime.fromisoformat,
        datetime.date.fromisoformat,
        datetime.time.fromisoformat
    ]
    for k, v in pairs:
        if isinstance(v, str):
            for converter in converters:
                try:
                    d[k] = converter(v)
                    break
                except ValueError:
                    pass
            else:
                d[k] = v
        else:
            d[k] = v
    return d


def save_state():
    for stream in RTSP_STREAMS:
        stream_folder = os.path.join(IMAGE_FOLDER, stream['name'])
        if not os.path.exists(stream_folder):
            os.makedirs(stream_folder)
    with open('state.json', 'w') as file:
        json.dump(RTSP_STREAMS, file, indent=4, sort_keys=True,
                  default=lambda obj: obj.isoformat() if hasattr(obj, 'isoformat') else obj)


def load_state():
    try:
        with open('state.json', 'r') as file:
            RTSP_STREAMS.extend(json.load(file, object_pairs_hook=load_with_datetime))
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        pass


def get_stream_info(stream_url):
    cap = cv2.VideoCapture(stream_url)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = round(cap.get(cv2.CAP_PROP_FPS))
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = chr(fourcc & 0xFF) + chr((fourcc >> 8) & 0xFF) + chr((fourcc >> 16) & 0xFF) + chr((fourcc >> 24) & 0xFF)
    is_stream_opened = cap.isOpened()
    cap.release()

    return {
        "work": is_stream_opened,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec
    }


def get_flags(stream, extension):
    flags = []

    if stream.get('use_flags'):
        match extension:
            case '.png':
                if stream.get('png_compression'):
                    flags.append(int(cv2.IMWRITE_PNG_COMPRESSION))
                    flags.append(stream['png_compression'])
            case '.webp':
                if stream.get('webp_quality'):
                    flags.append(int(cv2.IMWRITE_WEBP_QUALITY))
                    flags.append(stream['webp_quality'])
            case '.jp2':
                if stream.get('jp2_compression'):
                    flags.append(int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000))
                    flags.append(stream['jp2_compression'])
            case '.jpg':
                if stream.get('jpg_quality'):
                    flags.append(int(cv2.IMWRITE_JPEG_QUALITY))
                    flags.append(stream['jpg_quality'])
                if stream.get('jpg_optimize'):
                    flags.append(int(cv2.IMWRITE_JPEG_OPTIMIZE))
                    flags.append(stream['jpg_optimize'])
    return flags


def save_image_from_stream(stream):
    if not stream.get('save_images', True):
        return None
    if stream.get('use_save_time_interval'):
        start_time = stream.get('save_time_start')
        end_time = stream.get('save_time_end')
        current_time = datetime.datetime.now().time()
        if start_time and end_time and not start_time <= current_time <= end_time:
            return None
        elif not (start_time and end_time):
            raise ValueError('')

    save_folder = os.path.join(IMAGE_FOLDER, stream['name'])
    os.makedirs(save_folder, exist_ok=True)
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    cap = cv2.VideoCapture(stream['url'])
    ret, frame = cap.read()
    if not ret:
        return False

    if stream.get('resize'):
        if isinstance(stream.get('im_res_width'), int) and isinstance(stream.get('im_res_height'), int):
            frame = cv2.resize(frame, (stream.get('im_res_width'), stream.get('im_res_height')))
    cap.release()

    extension = stream.get('extension', '.jpg')
    flags = get_flags(stream, extension)

    filename = f'{stream["name"]}_{current_datetime}{extension}'
    save_path = os.path.abspath(os.path.join(save_folder, filename))

    return cv2.imwrite(save_path, frame, flags)
