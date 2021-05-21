import sys, time, os
import subprocess, threading
from utils import timestamp_log

import cv2
import pyaudio, wave

AUDIO_SAMPLE_RATE = 48000
AUDIO_FRAMES_PER_BUFFER_CHUNK = 1024
AUDIO_CHANNELS = 1 
AUDIO_FORMAT = pyaudio.paInt16
FPS_LIMIT = 10
# Camera module: AUKEY PC-LM1E
# TODO: separate the audio/video files into a different folder.

class VideoRecorder():  

    # Video class based on openCV
    def __init__(self, fdir, fname, dev_index=0, verbose=False):
        self.open = True
        self.device_index = dev_index
        self.fps = FPS_LIMIT       # fps should be the minimum constant rate at which the camera can
        self.fourcc = "MJPG"       # capture images (with no decrease in speed over time; testing is required)
        self.frameSize = (640,480) # video formats and sizes also depend and vary according to the camera used
        self.fdir = fdir
        self.fname = fname
        self.video_filename = fname + "-raw_video.avi"
        if sys.platform.startswith('win'):
            # Windows OS has to select cv2.CAP_DSHOW to properly release the camera.
            self.video_cap = cv2.VideoCapture(self.device_index + cv2.CAP_DSHOW)
        else:
            self.video_cap = cv2.VideoCapture(self.device_index)
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.video_out = cv2.VideoWriter(os.path.join(self.fdir, self.video_filename), self.video_writer, self.fps, self.frameSize)
        self.frame_counts = 1
        self.start_time = time.time()
        self.video_thread = threading.Thread(target=self.record, args=(verbose,), daemon=True)

    # Video starts being recorded
    def record(self, verbose=False):
        counter = 1
        timer_start = time.time()
        timer_current = 0
        font                   = cv2.FONT_HERSHEY_SIMPLEX
        bottomLeftCornerOfText = (10,470)
        fontScale              = 1
        fontColor              = (255,255,255)
        lineType               = 2
        with open(os.path.join(self.fdir, self.fname + "-frame_meta.log"), "a") as f_meta:
            while self.open:
                ret, video_frame = self.video_cap.read()
                if (ret==True):
                    idx = counter - 1
                    timer_current = time.time() - timer_start
                    cv2.putText(video_frame, timestamp_log(), bottomLeftCornerOfText, font, fontScale, fontColor, lineType)
                    self.video_out.write(video_frame)
                    f_meta.write(timestamp_log() + "frame index: " + str(idx) + "\n")
                    if verbose:
                        sys.stdout.write(timestamp_log() + str(self.frame_counts) + " video frames written " + str(timer_current) + "\n")
                    self.frame_counts += 1
                    counter += 1
                    time.sleep(1 / FPS_LIMIT * 0.1)
            
        self.video_out.release()
        self.video_cap.release()
        
    # Finishes the video recording therefore the thread too
    def stop(self):
        if self.open==True:
            self.open=False

    # Launches the video recording function using a thread          
    def start(self):
        self.video_thread.start()


class AudioRecorder():

    # Audio class based on pyAudio and Wave
    def __init__(self, fdir, fname, device_index=0, verbose=False):
        self.open = True
        self.device_index = device_index
        self.rate = AUDIO_SAMPLE_RATE
        self.frames_per_buffer = AUDIO_FRAMES_PER_BUFFER_CHUNK
        self.channels = AUDIO_CHANNELS
        self.format = AUDIO_FORMAT
        self.fdir = fdir
        self.audio_filename = fname + "-raw_audio.wav"

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer = self.frames_per_buffer)
        
        self.waveFile = wave.open(os.path.join(self.fdir, self.audio_filename), 'wb')
        self.waveFile.setnchannels(self.channels)
        self.waveFile.setsampwidth(self.audio.get_sample_size(self.format))
        self.waveFile.setframerate(self.rate)

        self.audio_thread = threading.Thread(target=self.record, args=(verbose,), daemon=True)

    # Audio starts being recorded
    def record(self, verbose=False):
        self.stream.start_stream()
        counter = 1
        timer_start = time.time()
        timer_current = 0

        while self.open:
            timer_current = time.time() - timer_start
            read_data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
            self.waveFile.writeframes(read_data)
            if verbose:
                sys.stdout.write(timestamp_log() + str(counter) + " audio frames written " + str(timer_current) + "\n")
            counter += 1
        self.stream.close()
        self.audio.terminate()
        self.waveFile.close()

    # Finishes the audio recording therefore the thread too    
    def stop(self):
        if self.open==True:
            self.open = False

    # Launches the audio recording function using a thread
    def start(self):
        self.audio_thread.start()


def start_AVrecording(video_recorder, audio_recorder, fdir, fname, verbose=False):
    os.chdir(fdir)
    audio_recorder.start()
    video_recorder.start()
    return fname


def stop_AVrecording(video_recorder, audio_recorder, fdir, fname, muxing=True):
    os.chdir(fdir)
    audio_recorder.stop()
    video_recorder.stop()
    frame_counts = video_recorder.frame_counts
    elapsed_time = time.time() - video_recorder.start_time
    recorded_fps = frame_counts / elapsed_time
    sys.stdout.write(timestamp_log() + fname + " vid total frames " + str(frame_counts) + "\n")
    sys.stdout.write(timestamp_log() + fname + " vid elapsed time " + str(elapsed_time) + "\n")
    sys.stdout.write(timestamp_log() + fname + " vid recorded fps " + str(recorded_fps) + "\n")
    cv2.destroyAllWindows()

    # Makes sure the threads have finished
    time.sleep(1)

    if muxing:
        # Merging audio and video signal
        if abs(recorded_fps - FPS_LIMIT) >= 0.01:    
            # If the fps rate was higher/lower than expected, re-encode it to the expected
            sys.stdout.write(timestamp_log() + "Re-encoding video\n")
            cmd = "ffmpeg -y -r " + str(recorded_fps) + " -i " + fname+"-raw_video.avi -pix_fmt yuv420p -r " + str(recorded_fps) + " " + fname+"-raw_video2.avi"
            subprocess.call(cmd, shell=True)
            sys.stdout.write(timestamp_log() + "Muxing video\n")
            cmd = "ffmpeg -y -ac " + str(AUDIO_CHANNELS) + " -channel_layout mono -i "+ fname + "-raw_audio.wav -i " + fname+"-raw_video2.avi -pix_fmt yuv420p " + fname + ".avi"
            subprocess.call(cmd, shell=True)
            sys.stdout.write(timestamp_log() + "Muxing done..\n")

        else:
            sys.stdout.write(timestamp_log() + "Normal recording & Muxing\n")
            cmd = "ffmpeg -y -ac " + str(AUDIO_CHANNELS) + " -channel_layout mono -i "+ fname+"-raw_audio.wav -i " + fname+"-raw_video.avi -pix_fmt yuv420p " + fname+".avi"
            subprocess.call(cmd, shell=True)
            sys.stdout.write(timestamp_log() + "Muxing done..\n")


def start_video_recording(video_recorder, fdir, fname):
    video_recorder.start()
    return fname

def stop_video_recording(video_recorder, fdir, fname):
    frame_counts = video_recorder.frame_counts
    elapsed_time = time.time() - video_recorder.start_time
    recorded_fps = frame_counts / elapsed_time
    sys.stdout.write(timestamp_log() + "total frames: " + str(frame_counts) + "\n")
    sys.stdout.write(timestamp_log() + "elapsed time: " + str(elapsed_time) + "\n")
    sys.stdout.write(timestamp_log() + "recorded fps: " + str(recorded_fps) + "\n")
    video_recorder.stop()
    cv2.destroyAllWindows()
    return fname

def start_audio_recording(audio_recorder, fdir, fname):
    audio_recorder.start()
    return fname

def stop_audio_recording(audio_recorder, fdir, fname):
    audio_recorder.stop()
    return fname

def remove_temp_files(fdir, fname):
    local_path = os.getcwd()
    if os.path.exists(str(local_path) + "/" + fname+"-raw_audio.wav"):
        os.remove(str(local_path) + "/" + fname+"-raw_audio.wav")
    if os.path.exists(str(local_path) + "/" + fname+"-raw_video.avi"):
        os.remove(str(local_path) + "/" + fname+"-raw_video.avi")
    if os.path.exists(str(local_path) + "/" + fname+"-raw_video2.avi"):
        os.remove(str(local_path) + "/" + fname+"-raw_video2.avi")


if __name__ == "__main__":
    if sys.platform.startswith('darwin'):
        USERDIR = os.path.join("/Users")
        USERNAME = os.environ.get('USER')
    if sys.platform.startswith('linux'):
        USERDIR = os.path.join("/home")
        USERNAME = os.environ.get('USER')
    if sys.platform.startswith('win'):
        USERDIR = os.path.join("C:/", "Users")
        USERNAME = os.getlogin()
    f = "test"
    video_recorder, audio_recorder = VideoRecorder(fdir=os.path.join(USERDIR, USERNAME, 'uwb_ranging'), fname=f), AudioRecorder(fdir=os.path.join(USERDIR, USERNAME, 'uwb_ranging'), fname=f)
    start_AVrecording(video_recorder, audio_recorder, os.path.join(USERDIR, USERNAME, 'uwb_ranging'), f)
    time.sleep(15)
    stop_AVrecording(video_recorder, audio_recorder, os.path.join(USERDIR, USERNAME, 'uwb_ranging'), f)
    print("test1 finished")
    f = "test_consecutive"
    video_recorder, audio_recorder = VideoRecorder(fdir=os.path.join(USERDIR, USERNAME, 'uwb_ranging'), fname=f), AudioRecorder(fdir=os.path.join(USERDIR, USERNAME, 'uwb_ranging'), fname=f)
    start_AVrecording(video_recorder, audio_recorder, os.path.join(USERDIR, USERNAME, 'uwb_ranging'), f)
    time.sleep(15)
    stop_AVrecording(video_recorder, audio_recorder, os.path.join(USERDIR, USERNAME, 'uwb_ranging'), f)
    print("test2, finished")