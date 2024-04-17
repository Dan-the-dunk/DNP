#!/usr/bin/env python

from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, Producer, OFFSET_BEGINNING, OFFSET_END
import cv2
import numpy as np
import json

from mypose.apis import inference_topdown
from mypose.apis import init_model as init_pose_estimator
from mypose.apis import visualize
from utils import visualize_bbox_and_keypoints
import base64

from config import *


def serialize_pose_results(offset, frame, keypoint, bbox):
    """
    Converts a pose process results to a JSON-serializable dictionary.
    Args:
        tensor: PyTorch tensor.

    Returns:
        A dictionary containing tensor information:
        - offset: Offset of this frame.
        - frame: The processed frame (With keypoints). : ndarray.
        - data: Bounding box and keypoints.
        - shape: List representing the result shape.
    """
    #data = tensor.detach().numpy().tolist()  # Detach and convert to NumPy array

    _, frame = cv2.imencode('.jpg', frame)
    frame = base64.b64encode(frame).decode('utf-8')

    return {
        "offset": offset,
        "frame": frame,
        "bbox": bbox.tolist(), # bbox with the id
        "keypoints": keypoint.tolist(),
    }
    

def visualize_pose_results(image, pose_results, bboxes):
    """
    Visualizes the pose estimation results on the image.
    Args:
        image: Image to draw the pose estimation results on.
        pose_results: Pose estimation results.

    Returns:
        The image with the pose estimation results drawn on it. : 
        Processed Frame: ndarray.
        Keypoints: List of keypoints.
    """

    # Get the keypoints and keypoint scores
    keypoints = []
    keypoint_scores = []
    for i in range (len (pose_results)):
        pred_instances = pose_results[i].pred_instances
        keypoints.append(pred_instances.keypoints)
        keypoint_scores.append(pred_instances.keypoint_scores)
    # Draw the keypoints into the image
    pose_vis = visualize(
        image, # can be img or img path
        np.hstack(keypoints),
        np.hstack(keypoint_scores),
        show=False)
    
    pose_vis = visualize_bbox_and_keypoints(image, bboxes, np.hstack(keypoints))
    cv2.imwrite('fullres.jpg', pose_vis)
    return pose_vis, np.hstack(keypoints)


def delivery_callback(err, msg):
            if err:
                print('ERROR: Message failed delivery: {}'.format(err))
            else:
                print("Produced event to topic {topic}: offset = {offset}".format(
                    topic=msg.topic(), offset=msg.  offset()))

class PoseProcess:
    def __init__(self, frame_topic, bbox_topic, bootstrap_servers=BOOTSTRAP_SERVERS):
        self.frame_topic = frame_topic
        self.bbox_topic = bbox_topic

        # CONFIG
        producer_config = {
            'bootstrap.servers': bootstrap_servers
        }

        consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'pose',
            'auto.offset.reset': 'earliest'
        }
        
        self.producer = Producer(producer_config)
        self.consumer = Consumer(consumer_config)
        self.consumer.subscribe([self.frame_topic, self.bbox_topic], on_assign=self.reset_offset)
        #self.model = YOLO('yolov8n-pose.pt')

        

        self.pose_estimator = init_pose_estimator(
            config='mypose/configs/body_2d_keypoint/topdown_heatmap/coco/td-hm_hrnet-w48_udp-8xb32-210e_coco-256x192.py',
            checkpoint='mypose/checkpoints/td-hm_hrnet-w48_8xb32-210e_coco-256x192-0e67c616_20220913.pth',
            device='cuda')


    def reset_offset(self, consumer, partitions):
        if args_reset:
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

    def processFrame(self, frame_list, bbox):
        """
        Process the frame and the bounding box
        bbox_list: list of bounding boxes, each bounding box is a numpy array of 4 elements , size (1,4) or (0,)
        """
        if len(frame_list) == 0:
            print("No frame to process")
            return np.zeros((7,7)), np.zeros((7,7))
        else:
            for i in range (len(frame_list) -1, -1, -1):  
                if(frame_list[i]['offset'] == bbox['offset']):
                    print(f"Matching offset:{bbox['offset']}")
                    #Crop the frame to the bounding box

                    bboxes = bbox['data'][:, :4]
                    frame = frame_list[i]['frame']                    

                    pose_results = inference_topdown(self.pose_estimator, frame, bboxes)
                    # Visualize the pose results
                    processed_frame, keypoints = visualize_pose_results(frame, pose_results, 
                                                                        np.hstack((bboxes, bbox['data'][:, 4].reshape(-1, 1))))

                    self.drop_offset(self.consumer, self.consumer.assignment())
                    #Image.fromarray(frame).save('pose_results.jpg')
                    frame_list.clear()

                    return processed_frame, keypoints 
            return np.zeros((7,7)), np.zeros((7,7))
    
    def sendPoseResults(self, offset, frame, keypoints, bbox):
        """
        Send the pose results to the result topic.
        pose_results: List of pose results, each pose result is a dictionary containing:
        - frame: List of keypoints.
        - offset: List of keypoint scores.
        - data: List of bounding boxes and keypoints.
        """
        
        self.producer.produce("results", json.dumps(serialize_pose_results(offset, frame, keypoints, bbox))
                              , callback=delivery_callback)
        
        self.producer.poll(10000)

    def getPose(self):            
        frame_list = []
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
                    if msg.topic() == self.frame_topic:
                        # Decode the image
                        image_cv2 = cv2.imdecode(np.frombuffer(msg.value(),'u1') , cv2.IMREAD_UNCHANGED) # Get numpy.ndarray
                        frame_list.append({"frame":image_cv2, "offset":msg.offset()})
                        #print(f"image_cv2.shape: {image_cv2.shape}")

                    elif msg.topic() == self.bbox_topic:
                        bbox_dict = json.loads(msg.value())
                        #print("bbox list: ", bbox_dict)
                        bbox = np.array(bbox_dict['data'])
                        bbox_offset = bbox_dict['offset']
                        
                        if bbox.shape == (0,):
                            print("Empty bbox")
                        else:
                            tmp_bbox = {"data":bbox, "offset":bbox_offset}
                            
                            processed_frame, keypoints = self.processFrame(frame_list, tmp_bbox)
                            if keypoints.shape[0] != 7:
                                #print(f"Keypoints shape: {keypoints.shape}")
                                #print(f"Processed frame shape: {processed_frame.shape}")
                                self.sendPoseResults(bbox_offset, processed_frame, keypoints, bbox)
                
        except KeyboardInterrupt:
            pass
        finally:
            # Leave group and commit final offsets
            print("Closed consumer and producer")
            self.producer.flush()
            self.consumer.close()
                
if __name__ == '__main__':
    # Parse the command line.
    """parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    # Parse the configuration.
    # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser['consumer'])
"""
    args_reset = False
    # Create BoundingBoxProcess instance
 
    pose = PoseProcess("frames", "bbox")
    pose.getPose()

   