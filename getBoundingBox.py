from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, Producer, OFFSET_BEGINNING, OFFSET_END
import cv2
import numpy as np
from PIL import Image
import json
import matplotlib.pyplot as plt

from mmpose.evaluation.functional import nms
from ultralytics import YOLO
import cv2
import numpy as np

from boxmot import OCSORT


def serialize_tensor(bbox_list, offset):
    """
    Converts a numpy to a JSON-serializable dictionary.
    Args:
        bbox_list: Numpy array containing bounding box information.
        offset: The offset of the message.
    Returns:
        A dictionary containing tensor information:
        - shape: List representing the tensor shape.
        - data: List of dictionaries representing the bounding boxes.
        - offset: The offset of the message.
    """
    bbox_list = bbox_list.tolist()  # Convert numpy array to list
    #bbox_list = [{'bbox': bbox} for bbox in bbox_list]  # Convert each bounding box to a dictionary
    return {
        "shape": len(bbox_list),
        "data": bbox_list,
        "offset": offset,
    }

def visualize_bbox(image, bboxes):
    # The bounding box is getting overlapped from previous frames, save with PIL Image instead
    plt.gca().set_axis_off()
    for bbox in bboxes:
        plt.gca().add_patch(plt.Rectangle((bbox[0], bbox[1]), bbox[2]-bbox[0], bbox[3]-bbox[1], fill=False, edgecolor='red', linewidth=2))
    plt.savefig('box_n_id.png')
    plt.close()
  

def predict_bbox(image_cv2, detector, tracker):
    # Get bounding box and tracking id
    detect_result = detector(image_cv2, classes=[0]) # Bbox for human only
    for r in detect_result:
        img_arr = r.plot(labels=False)
    pred_instance = detect_result[0].boxes.cpu().numpy()
    bbox = pred_instance.data[:,:6] # (x, y, x, y, conf, cls)
    results = tracker.update(bbox, image_cv2) # --> M X (x, y, x, y, id, conf, cls, ind)
    #tracker.plot_results(image_cv2, show_trajectories=True)
    cv2.imwrite('box_n_id.png', img_arr)


    return results

class BoundingBoxProcess:
    def __init__(self, topic, config):
        self.producer = Producer(config)
        self.topic = topic
        self.consumer = Consumer(config)
        self.consumer.subscribe([topic], on_assign=self.reset_offset)
        self.bbox = None
        self.msg_offset = None
        self.tracker = OCSORT()
        self.detector = YOLO('yolov8n.pt')


    def reset_offset(self, consumer, partitions):
        # Only call when a consumer first subscribe to a topic
        print(f"Length of partitions: {len(partitions)}")
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)
    
    def drop_offset(self, consumer, partitions):
        print(f"Dropping the offset, length of the partitions: {len(partitions)}")
        for p in partitions:
            p.offset = OFFSET_END
            print(f"The offset of {p.offset}")
        consumer.assign(partitions)        

    def sendBoundingBox(self, offset, bbox_list):
        def delivery_callback(err, msg):
            if err:
                print('ERROR: Message failed delivery: {}'.format(err))
            else:
                print("Produced event to topic {topic}: offset={offset}".format(
                    topic=msg.topic(), offset=msg.offset()))
        
        self.drop_offset(self.consumer, self.consumer.assignment())

        self.producer.produce('bbox', json.dumps(serialize_tensor(bbox_list, offset=offset)), callback=delivery_callback)
        self.producer.poll(10000)

    def getBoundingBox(self):
        try:
            while True:
                bbox_list = []
                msg = self.consumer.poll(1.0)
                #msg = self.consumer.seek(new TopicPartitionOffset(self.topic, new Partition(1), Offset.End))
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
                    self.msg_offset = msg.offset()
                    # Decode the image
                    image_cv2 = cv2.imdecode(np.frombuffer(msg.value(),'u1') , cv2.IMREAD_UNCHANGED) # Get numpy.ndarray
                
                    # predict bbox
                    bboxes = predict_bbox(image_cv2, self.detector, self.tracker)

                    print("Bbox list : ", bboxes)
                    #visualize_bbox(image_cv2, bboxes)
                    self.sendBoundingBox(self.msg_offset, bboxes)
                    
        except KeyboardInterrupt:
            pass
        finally:
            # Leave group and commit final offsets
            self.producer.flush()
            self.consumer.close()
            print("Closed consumer and producer")

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

    # Create BoundingBoxProcess instance
 
    bbox = BoundingBoxProcess("frames", config)
    bbox.getBoundingBox()

   