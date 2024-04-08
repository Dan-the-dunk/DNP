import cv2
import numpy as np

from mypose.apis import inference_topdown
from mypose.apis import init_model as init_pose_estimator
from mypose.apis import visualize
from utils import visualize_bbox_and_keypoints

from ultralytics import YOLO

bbox_det = YOLO('yolov8n.pt')

pose_estimator = init_pose_estimator(
            config='mmpose/configs/body_2d_keypoint/topdown_heatmap/coco/td-hm_hrnet-w48_8xb32-210e_coco-256x192.py',
            checkpoint='mmpose/checkpoints/td-hm_hrnet-w48_8xb32-210e_coco-256x192-0e67c616_20220913.pth',
            device='cpu')


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
    cv2.imwrite('fullres_mypose.jpg', pose_vis)
    return pose_vis, np.hstack(keypoints)


def main():

    img = cv2.imread('demo_dnp.png')
    detect_result = bbox_det(img, classes=[0])


    # Detect the bbox
    pred_instance = detect_result[0].boxes.cpu().numpy()
    bbox = pred_instance.data[:,:6] # (x, y, x, y, conf, cls)
    bboxes = bbox[:, :4]


    # Detect the pose
    pose_results = inference_topdown(pose_estimator, img, bboxes)

    processed_frame, keypoints = visualize_pose_results(img, pose_results,   
                                                np.hstack((bboxes, bbox[:, 4].reshape(-1, 1))))

    print(f"Frame shape: {processed_frame.shape}")

if __name__ == '__main__':
    main()