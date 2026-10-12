"""Generate a local synthetic speech fixture with Windows SAPI, not a recording."""
from pathlib import Path
from comtypes.client import CreateObject

root = Path(__file__).resolve().parents[1]
root.joinpath('data').mkdir(exist_ok=True)
voice = CreateObject('SAPI.SpVoice', dynamic=True)
stream = CreateObject('SAPI.SpFileStream', dynamic=True)
stream.Open(str(root / 'data' / 'synthetic-speech.wav'), 3, False)
voice.AudioOutputStream = stream
voice.Speak('The music should become quiet while I am speaking. After a short pause, it should come back gently. Testing one, two, three.', 0)
stream.Close()
print('Synthetic speech fixture generated locally with Windows SAPI')
