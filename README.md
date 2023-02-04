# PythonMIDIPlayer
Fast MIDI Player, written in Python. 🐇

Originally made as a funny project.

With the help of Anon64(Anon64#7195), Assile(Assile#2704), and Sono's MIDI parser written in Python (https://gist.github.com/SonoSooS/6ad345ef21bed2bb74c05d8b52c6fb82), this has become a reality.

# Requirements

Required modules:
pySDL2 (pip install pysdl2) and KDMAPI (pip install KDMAPI)

OmniMIDI Synth is required in order for it to work as it uses KDMAPI for clear, low latency sound.

# LiMItAtiONS!!?!?!?!11111 😱

Most limiting factor here: after 70k NPS (Notes per Second), it may start slowing down, or earlier (Depends on your PC, and Python version)

The notes only go from up to bottom. (I cannot figure out how to make it hit a certain spot (because i don't know how to delay the audio.))

No piano, only falling notes.


This isn't some crazy polished work, it's just a little project. 😉

#Help?

You are absolutely welcome to fork, and issue pull requests to make this little script better! 😊
