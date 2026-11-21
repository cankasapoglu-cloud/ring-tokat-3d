#!/bin/bash
# Decode the full mix to WAV (44.1 kHz, stereo + mono) for analysis. Read-only on the source.
set -e
A=/home/user/ring-tokat-3d/cocuk-kanali/ali-baba
O=$A/yeni3/analiz/tempo
ffmpeg -hide_banner -loglevel error -y -i $A/dinle_2.mp3 -ar 44100 -ac 2 $O/mix_44k_stereo.wav
ffmpeg -hide_banner -loglevel error -y -i $A/dinle_2.mp3 -ar 44100 -ac 1 $O/mix_44k_mono.wav
ffprobe -hide_banner $O/mix_44k_mono.wav 2>&1 | tail -3
