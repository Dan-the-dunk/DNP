#!/usr/bin/env python

import cv2
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Producer
import time

from config import *


class VideoProducer:
    def __init__(self, topic, video_path, bootstrap_servers=BOOTSTRAP_SERVERS):

        self.producer_config = {
            'bootstrap.servers': bootstrap_servers
        }
        
        self.producer = Producer(self.producer_config)
        self.topic = topic
        self.video_path = video_path
    
    def produce_frame(self):
        def delivery_callback(err, msg):
            if err:
                print('ERROR: Message failed delivery: {}'.format(err))
            else:
                print("Produced event to topic {topic}, offset = {offset} ".format(
                    topic=msg.topic(), offset=msg.offset()))

        vidCap = cv2.VideoCapture(self.video_path)
        frame_id = 0
        while vidCap.isOpened():
            ret, frame = vidCap.read()
            if ret == True:
                ret, buffer = cv2.imencode('.jpg', frame)
                self.producer.produce(self.topic, buffer.tobytes(), callback=delivery_callback)
                frame_id += 1
                self.producer.poll(10000)
                print("Frame {}".format(frame_id))
                time.sleep(1/10)
            else:
                break
        self.flush()

    def flush(self):
        print("Flushing the stuff")
        self.producer.flush()




if __name__ == '__main__':
    """# Parse the command line.
    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    args = parser.parse_args()

    # Parse the configuration.
    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])"""

    # Create videoProd instance
    videoProd = VideoProducer("frames", "videos/demo_iai_2.mp4")

    videoProd.produce_frame()

    # Block until the messages are sent.
    