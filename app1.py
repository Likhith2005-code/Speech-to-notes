from vosk import Model, KaldiRecognizer
import wave
import json

model = Model("vosk-model")
wf = wave.open("harvard.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(json.loads(rec.Result()))
print(json.loads(rec.FinalResult()))