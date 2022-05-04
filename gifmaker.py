#!/usr/bin/env python

import imageio.v3 as iio
import argparse
import logging

from datetime import timedelta
from pathlib import Path


logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def get_fps(path: Path) -> int:
    metadata = iio.immeta(path, exclude_applied=False)
    fps = metadata['fps']
    return fps


def get_frame(timestamp: str, fps: float) -> int:
    if timestamp.count(':') == 2:
        hours, minutes, secs = timestamp.split(':')
    else:
        hours = 0
        minutes, secs = timestamp.split(':')
    return int(timedelta(hours=int(hours), minutes=int(minutes), seconds=int(secs)).total_seconds() * fps)


def add_hour_if_needed(timestamp: str) -> str:
    if timestamp.count(':') == 1:
        timestamp = f'00:{timestamp}'
    return timestamp


def run(path: Path, out_file_name: str, intervals: list[str]):
    logger.info('Gathering frames from %s', path)
    fps = get_fps(path)
    logger.info('FPS of %s is %s', path, fps)
    write = False
    parent_dir = path.parent.absolute() / "gifmaker"
    parent_dir.mkdir(exist_ok=True)
    full_out_path = (parent_dir / out_file_name).with_suffix(".gif")
    images = []
    duration = (1 / fps) * 1000
    interval_index = 0
    first_frame = None
    last_frame = None

    start_time = add_hour_if_needed(intervals[0].split('-')[0])
    end_time = add_hour_if_needed(intervals[-1].split('-')[-1])

    ffmpeg_args = ['-ss', start_time, '-to', end_time]

    skipped_frames = get_frame(start_time, fps)
    logger.info('Opening %s with ffmpeg args: %s', path, ffmpeg_args)

    for i, frame in enumerate(iio.imiter(path, ffmpeg_params=ffmpeg_args)):
        frame_no = i + skipped_frames
        if not first_frame or not last_frame:
            try:
                interval = intervals[interval_index]
            except IndexError:
                break
            interval_index += 1
            start, end = interval.split('-')
            first_frame = get_frame(start, fps)
            last_frame = get_frame(end, fps)
            logger.info('Looking for frames between %s and %s', first_frame, last_frame)
        if frame_no and not frame_no % 100:
            logger.debug('Checking frame %s', frame_no)
        if frame_no == first_frame:
            logger.info('Writing begins')
            write = True
        elif frame_no > last_frame:
            logger.info('Writing ends')
            write = False
            first_frame = None
            last_frame = None
        if write:
            images.append(frame)
    logger.info('Collected %s frames', len(images))
    with iio.imopen(full_out_path, "w") as outfile:
        outfile.write(images, duration=duration)
    logger.info('Wrote to %s', full_out_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path, help="Path to input video")
    parser.add_argument('output', type=str,
                        help="Output file name without gif extension, will be stored in gifmaker subdirectory in parent directory of the input file ")
    parser.add_argument('intervals', nargs="+", type=str,
                        help="One or more intervals in format mm:ss-mm:ss, e.g. 0:00-0:20 10:00-10:20")
    args = parser.parse_args()
    run(args.input, args.output, args.intervals)
