import cv2
import pyaudio
import wave
import threading
import time
import subprocess
import os
import array


AUDIO_SAMPLE_RATE = 48000
AUDIO_FRAMES_PER_BUFFER_CHUNK = 1024
AUDIO_CHANNELS = 1 
AUDIO_FORMAT = pyaudio.paInt16
FPS_LIMIT = 10

class VideoRecorder():  

    # Video class based on openCV 
    # Non-blocking
    def __init__(self, dev_index=0):
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
        self.video_thread = threading.Thread(target=self.record)

    # Video starts being recorded 
    def record(self):
        counter = 1
        timer_start = time.time()
        timer_current = 0

        while self.open:
            ret, video_frame = self.video_cap.read()
            if (ret==True):
                    self.video_out.write(video_frame)
                    print(str(counter) + " " + str(self.frame_counts) + " frames written " + str(timer_current))
                    self.frame_counts += 1
                    counter += 1
                    timer_current = time.time() - timer_start
                    time.sleep(1 / FPS_LIMIT * 0.7)
            else:
                break
        self.video_out.release()
        self.video_cap.release()
        
    # Finishes the video recording therefore the thread too
    def stop(self):
        if self.open==True:
            self.open=False
        else: 
            pass

    # Launches the video recording function using a thread          
    def start(self):
        self.video_thread.start()


class AudioRecorder():

    # Audio class based on pyAudio and Wave
    def __init__(self, device_index=2):
        self.open = True
        self.device_index = device_index
        self.rate = AUDIO_SAMPLE_RATE
        self.frames_per_buffer = AUDIO_FRAMES_PER_BUFFER_CHUNK
        self.channels = AUDIO_CHANNELS
        self.format = AUDIO_FORMAT
        self.audio_filename = "temp_audio.wav"

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(input_device_index=self.device_index,
                                      format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer = self.frames_per_buffer)
        
        self.audio_thread = threading.Thread(target=self.record)

        self.waveFile = wave.open(self.audio_filename, 'wb')
        self.waveFile.setnchannels(self.channels)
        self.waveFile.setsampwidth(self.audio.get_sample_size(self.format))
        self.waveFile.setframerate(self.rate)

    # Audio starts being recorded
    def record(self):
        self.stream.start_stream()
        while self.open:
            read_data = None
            try:
                read_data = self.stream.read(self.frames_per_buffer)
            except:
                pass
            if read_data:
                self.waveFile.writeframes(read_data)
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


def start_AVrecording(filename):

    global video_recorder
    global audio_recorder

    video_recorder = VideoRecorder()
    audio_recorder = AudioRecorder()

    audio_recorder.start()
    video_recorder.start()

    return filename


def start_video_recording(filename):
    global video_recorder
    video_recorder = VideoRecorder()
    video_recorder.start()
    return filename


def start_audio_recording(filename):
    global audio_recorder
    audio_recorder = AudioRecorder()
    audio_recorder.start()
    return filename


def stop_AVrecording(filename):
    audio_recorder.stop()
    frame_counts = video_recorder.frame_counts
    elapsed_time = time.time() - video_recorder.start_time
    recorded_fps = frame_counts / elapsed_time
    print("total frames " + str(frame_counts))
    print("elapsed time " + str(elapsed_time))
    print("recorded fps " + str(recorded_fps))
    video_recorder.stop()
    cv2.destroyAllWindows()

    # Makes sure the threads have finished
    while threading.active_count() > 1:
        time.sleep(1)

    #Merging audio and video signal
    if abs(recorded_fps - FPS_LIMIT) >= 0.01:    # If the fps rate was higher/lower than expected, re-encode it to the expected
        print("Re-encoding")
        cmd = "ffmpeg -r " + str(recorded_fps) + " -i temp_video.avi -pix_fmt yuv420p -r " + str(FPS_LIMIT) + " temp_video2.avi"
        subprocess.call(cmd, shell=True)
        print("Muxing")
        cmd = "ffmpeg -ac " + str(AUDIO_CHANNELS) + " -channel_layout stereo -i temp_audio.wav -i temp_video2.avi -pix_fmt yuv420p " + filename + ".avi"
        subprocess.call(cmd, shell=True)
        print("..")

    else:
        print("Normal recording\nMuxing")
        cmd = "ffmpeg -ac " + str(AUDIO_CHANNELS) + " -channel_layout stereo -i temp_audio.wav -i temp_video.avi -pix_fmt yuv420p " + filename + ".avi"
        subprocess.call(cmd, shell=True)
        print("..")


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
    file_manager(f)
    start_AVrecording(f)
    time.sleep(3600)
    stop_AVrecording(f)
    os.system("free -m")