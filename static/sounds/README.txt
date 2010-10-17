WAV TO MP3
lame -h -b 192 49__Anton__Glass_G_mf.wav "Glass_G.mp3"

MP3 TO OGG
mpg321 Glass_G.mp3 -w - | oggenc -o Glass_G.ogg -