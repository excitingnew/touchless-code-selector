# Touchless Code Selector

A Python webcam interface for selecting code lines and controlling an IDE assistant with hand gestures.

Developed as part of a team project that won **3rd place overall at the JetBrains Hackathon**. The Python component combines OpenCV video capture, MediaPipe hand tracking, gesture recognition, and TCP messages to an IntelliJ integration.

## How It Works

```text
Webcam -> OpenCV frames -> MediaPipe hand landmarks
       -> Gesture and line-range detection -> TCP messages -> IDE integration
```

- Tracks one hand in a mirrored, 640 x 480 camera preview.
- Maps the vertical positions of the thumb and index fingertips to a code-line range.
- Sends updated selections while selection is unlocked.
- Uses a stable fist to lock the range and trigger the IDE assistant.
- Sends three numbered assistant options using finger gestures.
- Sends a close command when the configured rock-sign gesture is detected.
- Displays hand landmarks, the candidate selection, fist state and the last selected option.

The Python script sends control messages. The corresponding IDE listener performs editor actions and supplies any assistant functionality; the script itself does not implement an AI model or an IntelliJ plugin.

## Gestures

| Gesture or action | Behavior |
| --- | --- |
| Move the thumb and index finger vertically | Adjust the candidate line range. |
| Hold a fist | Lock the buffered range and trigger the assistant. |
| Raise the index finger, keeping the other fingers folded and thumb tucked | Send option `1`. |
| Raise index and middle fingers, keeping ring and little fingers folded and thumb tucked | Send option `2`. |
| Raise thumb, index, and middle fingers, keeping ring and little fingers folded | Send option `3`. |
| Raise thumb, index, and little fingers while folding middle and ring fingers | Send the assistant close command. |
| Remove the hand from view | Clear the gesture buffers and unlock selection. |
| Press `q` in the camera window | Exit the loop. |

The meaning of option numbers `1`, `2`, and `3` is defined by the IDE integration. A physical pinch is not required: line selection uses fingertip positions.

## Stabilization

Fist detection and numbered options use a five-frame history. A candidate must occur in at least three buffered frames before it is accepted. The frames do not have to be consecutive.

Before locking a selection, the script takes the minimum start line and maximum end line from a buffer of up to ten recent ranges. Repeated transmissions of the same numbered option are suppressed until a different option is sent or the hand leaves view.

## Setup

The script needs a webcam, a graphical desktop session, OpenCV, and a MediaPipe version exposing the legacy `mp.solutions.hands` API. Python 3.11 or 3.12 with MediaPipe 0.10.21 is a suitable starting configuration; platform-specific wheels are listed on [PyPI](https://pypi.org/project/mediapipe/0.10.21/).

Example environment on macOS or Linux:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install "mediapipe==0.10.21" "opencv-contrib-python<4.12"
```

`opencv-contrib-python` provides the `cv2` module used by the script. Use one OpenCV package in the environment rather than installing multiple variants. The other imports, `socket` and `collections.deque`, are part of Python's standard library.

Start a compatible IDE listener on `localhost:9999`, then open the project's Python script in your editor and run it using this virtual environment. Allow camera access if your operating system requests it.

Without an IDE listener, the camera preview can still show detected gestures, but socket operations report connection errors and no IDE actions occur.

## TCP Protocol

Each command is sent over a new TCP connection that closes after sending. Text is encoded as UTF-8.

| Message | Meaning |
| --- | --- |
| `start,end\n` | Send the zero-based start and end line indices. |
| `AI:` | Trigger the assistant. This message has no trailing newline. |
| `AI_OPTION:1\n` | Select assistant option 1; options 2 and 3 use the same format. |
| `AI:CLOSE\n` | Close the assistant. |

The listener must handle the `AI:` message at connection close rather than waiting only for a newline. The IDE integration is responsible for interpreting the line indices and mapping option numbers to actions.

## Configuration

| Setting | Default | Purpose |
| --- | --- | --- |
| `cv2.VideoCapture(...)` | `0` | Camera device index. |
| `server_host` | `localhost` | IDE listener hostname. |
| `server_port` | `9999` | IDE listener port. |
| `total_lines` | `60` | Number of lines used for coordinate mapping. |
| `LINE_SCALE` | `0.9` | Vertical mapping scale. |
| `PINCH_BUFFER_LEN` | `10` | Number of recent selection ranges retained. |
| `min_detection_confidence` | `0.6` | MediaPipe hand-detection threshold. |

Set `total_lines` to match the intended editor context. The script does not read the active document's length or scroll position from the IDE.

## Current Limitations

- Gesture rules use relative landmark coordinates and may need adjustment for hand orientation, camera position, and lighting.
- Selection stays locked until hand tracking is lost.
- The close gesture can send a command on every detected frame; it does not use the same debounce rule as numbered options.
- Socket operations are synchronous and have no explicit timeout, so an unresponsive listener can affect the camera loop.
- This is a hackathon prototype; no measured latency, recognition-accuracy, or accessibility-validation claims are made.

For the hand-tracking API used here, see the [MediaPipe Hands documentation](https://chuoling.github.io/mediapipe/solutions/hands.html).
