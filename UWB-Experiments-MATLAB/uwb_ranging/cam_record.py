import sys, time, os, array
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

class VideoRecorder():  

    # Video class based on openCV
    def __init__(self, dev_index=0, verbose=False):
        self.open = True
        self.device_index = dev_index
        self.fps = FPS_LIMIT       # fps should be the minimum constant rate at which the camera can
        self.fourcc = "MJPG"       # capture images (with no decrease in speed over time; testing is required)
        self.frameSize = (640,480) # video formats and sizes also depend and vary according to the camera used
        self.video_filename = "temp_video.avi"
        self.video_cap = cv2.VideoCapture(self.device_index)
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.video_out = cv2.VideoWriter(self.video_filename, self.video_writer, self.fps, self.frameSize)
        self.frame_counts = 1
        self.start_time = time.time()
        self.video_thread = threading.Thread(target=self.record, args=(verbose,))

    # Video starts being recorded
    def record(self, verbose=False):
        counter = 1
        timer_start = time.time()
        timer_current = 0

        while self.open:
            ret, video_frame = self.video_cap.read()
            if (ret==True):
                timer_current = time.time() - timer_start
                self.video_out.write(video_frame)
                if verbose:
                    sys.stdout.write(timestamp_log() + str(self.frame_counts) + " video frames written " + str(timer_current) + "\n")
                self.frame_counts += 1
                counter += 1
                time.sleep(1 / FPS_LIMIT * 0.5)
            
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
    def __init__(self, device_index=0, verbose=False):
        self.open = True
        self.device_index = device_index
        self.rate = AUDIO_SAMPLE_RATE
        self.frames_per_buffer = AUDIO_FRAMES_PER_BUFFER_CHUNK
        self.channels = AUDIO_CHANNELS
        self.format = AUDIO_FORMAT
        self.audio_filename = "temp_audio.wav"

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer = self.frames_per_buffer)
        
        self.waveFile = wave.open(self.audio_filename, 'wb')
        self.waveFile.setnchannels(self.channels)
        self.waveFile.setsampwidth(self.audio.get_sample_size(self.format))
        self.waveFile.setframerate(self.rate)

        self.audio_thread = threading.Thread(target=self.record, args=(verbose,))

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


def start_AVrecording(video_recorder, audio_recorder, filename, verbose=False):
    audio_recorder.start()
    video_recorder.start()
    return filename


def stop_AVrecording(video_recorder, audio_recorder, filename):
    audio_recorder.stop()
    video_recorder.stop()
    frame_counts = video_recorder.frame_counts
    elapsed_time = time.time() - video_recorder.start_time
    recorded_fps = frame_counts / elapsed_time
    sys.stdout.write(timestamp_log() + "total frames " + str(frame_counts) + "\n")
    sys.stdout.write(timestamp_log() + "elapsed time " + str(elapsed_time) + "\n")
    sys.stdout.write(timestamp_log() + "recorded fps " + str(recorded_fps) + "\n")
    cv2.destroyAllWindows()

    # Makes sure the threads have finished
    while threading.active_count() > 1:
        time.sleep(1)

    # Merging audio and video signal
    if abs(recorded_fps - FPS_LIMIT) >= 0.01:    
        # If the fps rate was higher/lower than expected, re-encode it to the expected
        sys.stdout.write(timestamp_log() + "Re-encoding video\n")
        cmd = "ffmpeg -y -r " + str(recorded_fps) + " -i temp_video.avi -pix_fmt yuv420p -r " + str(FPS_LIMIT) + " temp_video2.avi"
        subprocess.call(cmd, shell=True)
        sys.stdout.write(timestamp_log() + "Muxing video\n")
        cmd = "ffmpeg -y -ac " + str(AUDIO_CHANNELS) + " -channel_layout mono -i temp_audio.wav -i temp_video2.avi -pix_fmt yuv420p " + filename + ".avi"
        subprocess.call(cmd, shell=True)
        sys.stdout.write(timestamp_log() + "Muxing done..\n")

    else:
        sys.stdout.write(timestamp_log() + "Normal recording & Muxing\n")
        cmd = "ffmpeg -y -ac " + str(AUDIO_CHANNELS) + " -channel_layout mono -i temp_audio.wav -i temp_video.avi -pix_fmt yuv420p " + filename + ".avi"
        subprocess.call(cmd, shell=True)
        sys.stdout.write(timestamp_log() + "Muxing done..\n")


def start_video_recording(video_recorder, filename):
    video_recorder.start()
    return filename

def stop_video_recording(video_recorder, filename):
    frame_counts = video_recorder.frame_counts
    elapsed_time = time.time() - video_recorder.start_time
    recorded_fps = frame_counts / elapsed_time
    sys.stdout.write(timestamp_log() + "total frames: " + str(frame_counts) + "\n")
    sys.stdout.write(timestamp_log() + "elapsed time: " + str(elapsed_time) + "\n")
    sys.stdout.write(timestamp_log() + "recorded fps: " + str(recorded_fps) + "\n")
    video_recorder.stop()
    cv2.destroyAllWindows()
    return filename

def start_audio_recording(audio_recorder, filename):
    audio_recorder.start()
    return filename

def stop_audio_recording(audio_recorder, filename):
    audio_recorder.stop()
    return filename

# Required and wanted processing of final files
def file_manager(filename):
    local_path = os.getcwd()
    if os.path.exists(str(local_path) + "/temp_audio.wav"):
        os.remove(str(local_path) + "/temp_audio.wav")
        
    if os.path.exists(str(local_path) + "/temp_video.avi"):
        os.remove(str(local_path) + "/temp_video.avi")

    if os.path.exists(str(local_path) + "/temp_video2.avi"):
        os.remove(str(local_path) + "/temp_video2.avi")


if __name__ == "__main__":
    f = "test"
    video_recorder, audio_recorder = VideoRecorder(), AudioRecorder()
    start_AVrecording(video_recorder, audio_recorder, f)
    time.sleep(15)
    stop_AVrecording(video_recorder, audio_recorder, f)
    file_manager(f)
    os.system("free -m")