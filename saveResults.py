#!/usr/bin/env python

from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, Producer, OFFSET_BEGINNING, OFFSET_END
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import json
from datetime import datetime
import base64


def serialize_tensor(tensor):
    """
    Converts a PyTorch tensor to a JSON-serializable dictionary.
    Args:
        tensor: PyTorch tensor.

    Returns:
        A dictionary containing tensor information:
        - shape: List representing the tensor shape.
        - dtype: String representing the data type.
        - data: List of numeric values representing the tensor elements.
    """
    data = tensor.detach().numpy().tolist()  # Detach and convert to NumPy array
    return {
        "shape": tensor.shape,
        "dtype": str(tensor.dtype),
        "data": data
    }



class SaveResultsProcess:
    def __init__(self, result_topic, config):
        self.producer = Producer(config)
        self.result_topic = result_topic
        self.consumer = Consumer(config)
        self.consumer.subscribe([self.result_topic], on_assign=self.reset_offset)

        self.frame_list = []
        self.log_list = []

        self.output_video = 'output_video_1.avi'
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(self.output_video, self.fourcc, 10.0, (1280, 720))
 
    def reset_offset(self, consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    def drop_offset(self, consumer, partitions):
        # Assign the consumer to the offset of the last message (Frame drop).
        print("Dropping the offset")
        for p in partitions:
            p.offset = OFFSET_END
            print(f"The offset of {p.offset}")
        consumer.assign(partitions)       

    def saveVideo(self):
        # Save the video
        print("Saving the video")
        # Define the codec and create VideoWriter object
    
    def saveLog(self, offset, data):
        # Save the log
        print("Saving the log")
    
    def saveResultsToDisk(self):
        # Save the results to disk
        print("Saving the results to disk")
        print(f"Length frame list: {len(self.frame_list)}")
        for frame in self.frame_list:
            self.video_writer.write(frame)

        self.video_writer.release()
        print("Video saved")
        # Save the logs

        print("Saving the logs")
        with open('logs.json', 'w') as f:
            json.dump(self.log_list, f)
        print("Logs saved")
    
    def saveResults(self):
        def delivery_callback(err, msg):
            if err:
                print('ERROR: Message failed delivery: {}'.format(err))
            else:
                print("Produced event to topic {topic}: offset = {offset}".format(
                    topic=msg.topic(), offset=msg.  offset()))
                
        try:
            while True:       
                msg = self.consumer.poll(1.0)
                if msg is None:
                    # Initial message consumption may take up to
                    # `session.timeout.ms` for the consumer group to
                    # rebalance and start consuming
                    print("Waiting...")
                elif msg.error():
                    print("ERROR: %s".format(msg.error()))
                else:
                    # Extract the offset and value, and print.
                    print("Consumed event from topic {topic}: offset={offset}".format(
                            topic=msg.topic(), offset=msg.offset()))
                    
                    # Load the msg
                    msg_dict = json.loads(msg.value())

                    # Decode the frame
                    frame_b64 = msg_dict['frame']
                    frame_bytes = frame_b64.encode()
                    content = base64.b64decode(frame_bytes)
                    frame = cv2.imdecode(np.frombuffer(content, 'u1'), cv2.IMREAD_UNCHANGED)

                    print(f"Frame shape {frame.shape}")

                    self.frame_list.append(frame)

                    # Save the logs.
                    logs_dict = dict(list(msg_dict.items())[2:])
                    print(f"Log {logs_dict}")
                    self.log_list.append(logs_dict)
                   
        except KeyboardInterrupt:
            pass
        finally:
            # Leave group and commit final offsets
            print("Closed consumer and producer")
            self.producer.flush()
            self.consumer.close()
                
if __name__ == '__main__':
    # Parse the command line.
    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    # Parse the configuration.
    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser['consumer'])

    # Create Save Process instance
 
    bbox = SaveResultsProcess("results", config)
    bbox.saveResults()
    bbox.saveResultsToDisk()

   