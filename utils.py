import cv2

def visualize_bbox_and_keypoints(img, bboxes, keypoints):
    """
    Visualizes the bounding box and keypoints on the image.
    Args:
        img: Image to draw the bounding box and keypoints on.
        bboxes: Bounding box coordinates.
        keypoints: Keypoints coordinates.
    Returns:
        The image with the bounding box and keypoints drawn on it. : ndarray.
    """
    bboxes = bboxes.astype(int)
    keypoints = keypoints.astype(int)
    for bbox in bboxes:
        cv2.putText(img, "ID: {}".format(bbox[4]), (bbox[0], bbox[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 2)
    for keypoint in keypoints:
        for i in range(0, len(keypoint)):
            print(f"Keypoint: {keypoint[i]}")
            cv2.circle(img, ((keypoint[i])), 3, (0, 255, 0), -1)
    return img