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


def job_print(text):
    print(text)


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


def save_state():
    for stream in RTSP_STREAMS:
        stream_folder = os.path.join(IMAGE_FOLDER, stream['name'])
        if not os.path.exists(stream_folder):
            os.makedirs(stream_folder)
    with open('state.json', 'w') as file:
        json.dump(RTSP_STREAMS, file, indent=4, sort_keys=True)


def load_state():
    try:
        with open('state.json', 'r') as file:
            RTSP_STREAMS.extend(json.load(file))
    except FileNotFoundError:
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


def save_image_from_stream(stream):
    if 'save_images' not in stream or stream['save_images']:
        save_folder = os.path.join(IMAGE_FOLDER, stream['name'])
        os.makedirs(save_folder, exist_ok=True)
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        cap = cv2.VideoCapture(stream['url'])
        ret, frame = cap.read()
        if not ret:
            return False

        if 'resize' in stream and stream['resize']:
            if 'im_res_width' in stream and 'im_res_height' in stream:
                frame = cv2.resize(frame, (stream['im_res_width'], stream['im_res_height']))
        cap.release()

        extension = stream['extension'] if 'extension' in stream else '.jpg'
        flags = []
        if 'use_flags' in stream and stream['use_flags']:
            match stream['extension']:

                case '.png':
                    flags.append(int(cv2.IMWRITE_PNG_COMPRESSION)) if 'png_compression' in stream else None
                    flags.append(stream['png_compression']) if 'png_compression' in stream else None
                case '.webp':
                    flags.append(int(cv2.IMWRITE_WEBP_QUALITY)) if 'webp_quality' in stream else None
                    flags.append(stream['webp_quality']) if 'webp_quality' in stream else None
                case '.jp2':
                    flags.append(int(cv2.IMWRITE_JPEG2000_COMPRESSION_X1000)) if 'jp2_compression' in stream else None
                    flags.append(stream['jp2_compression']) if 'jp2_compression' in stream else None
                case '.jpg':
                    flags.append(int(cv2.IMWRITE_JPEG_QUALITY)) if 'jpg_quality' in stream else None
                    flags.append(stream['jpg_quality']) if 'jpg_quality' in stream else None
                    flags.append(int(cv2.IMWRITE_JPEG_OPTIMIZE)) if 'jpg_optimize' in stream else None
                    flags.append(stream['jpg_optimize']) if 'jpg_optimize' in stream else None

        filename = f'{stream["name"]}_{current_datetime}{extension}'
        save_path = os.path.join(save_folder, filename)
        save_path = os.path.abspath(save_path)
        return cv2.imwrite(save_path, frame, flags)
