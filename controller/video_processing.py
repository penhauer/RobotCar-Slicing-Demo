import cv2
import numpy as np
import os
import io
import av  # NEW: PyAV (FFmpeg) backend for capture

os.sched_setaffinity(0, {0, 1, 2, 3})

command_dict = {
    "move": True,
    "obstacle": False,
}


def filter_red(frame):
    top_half = frame[:frame.shape[0] // 2, :]
    frame = top_half

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    red_lower1 = np.array([0, 100, 100])   # First range of red
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 100, 100]) # Second range of red
    red_upper2 = np.array([180, 255, 255])

    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)

    return red_mask, is_dominant(red_mask)

def is_dominant(mask):
    total_pixels = mask.size
    red_pixels = cv2.countNonZero(mask)
    return red_pixels > (total_pixels / 20)

def compute_average_hsv(frame):
    height, width, _ = frame.shape

    # Define the size and position of the square (10% of frame size)
    square_size = int(min(height, width) * 0.5)
    center_x, center_y = width // 2, height // 2
    # center_x, center_y = width // 6, height // 6
    top_left_x = center_x - square_size // 2
    top_left_y = center_y - square_size // 2
    bottom_right_x = center_x + square_size // 2
    bottom_right_y = center_y + square_size // 2

    # Extract the region of interest (ROI)
    roi = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]

    # Convert ROI to HSV
    # hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hsv_roi = frame

    # Compute average HSV values
    avg_h = (np.mean(hsv_roi[:, :, 0]), np.std(hsv_roi[:, :, 0]))
    avg_s = (np.mean(hsv_roi[:, :, 1]), np.std(hsv_roi[:, :, 1]))
    avg_v = (np.mean(hsv_roi[:, :, 2]), np.std(hsv_roi[:, :, 2]))

    return avg_h, avg_s, avg_v


def capture_thread(port: str):
    """
    Receive RTP/H264 on UDP `port` via FFmpeg (PyAV), decode to BGR, and run the original logic.
    No OpenCV+GStreamer or gi required.
    """
    # Minimal SDP describing an H264 RTP stream on the given port (PT=96)
    sdp = f"""v=0
o=- 0 0 IN IP4 0.0.0.0
s=stream
c=IN IP4 0.0.0.0
t=0 0
m=video {port} RTP/AVP 96
a=rtpmap:96 H264/90000
a=recvonly
"""

    # Open via PyAV using the SDP in-memory. Allow UDP/RTP from FFmpeg.
    # fifo_size/overrun_nonfatal help with bursts; ffflags/flags reduce latency.
    container = av.open(
        io.BytesIO(sdp.encode("utf-8")),
        format="sdp",
        options={
            "protocol_whitelist": "file,udp,rtp",
            "fifo_size": "1000000",
            "overrun_nonfatal": "1",
            "fflags": "nobuffer",
            "flags": "low_delay",
        },
    )

    # Get the first video stream
    if not container.streams.video:
        print("Error: No video stream found in SDP/port.")
        container.close()
        return
    vstream = container.streams.video[0]
    vstream.thread_type = "AUTO"

    try:
        for packet in container.demux(vstream):
            # Packets may contain multiple frames
            for frame in packet.decode():
                # Convert to numpy BGR (like cv2 expects)
                bgr = frame.to_ndarray(format="bgr24")

                # --- Original logic preserved ---
                cv2.imshow("Original Frame", bgr)
                print("hererer", command_dict)

                if command_dict:
                    processed_frame, obstacle_detected = filter_red(bgr)

                    if obstacle_detected:
                        text = "Obstacle Detected!"
                        color = (0, 0, 255)
                    else:
                        text = "No Obstacle"
                        color = (0, 255, 0)

                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 1
                    thickness = 2
                    line_type = cv2.LINE_AA
                    text_position = (10, 30)

                    cv2.putText(processed_frame, text, text_position, font, font_scale, color, thickness, line_type)
                    cv2.imshow("Processed Frame", processed_frame)

                    command_dict["obstacle"] = obstacle_detected

                # UI / exit
                if cv2.waitKey(1) == 27:  # ESC
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass
    finally:
        container.close()
        cv2.destroyAllWindows()
