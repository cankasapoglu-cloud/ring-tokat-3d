#!/bin/bash
# Decode the full mix v2_2.mp3 to mono WAV (44.1 kHz) into the deletable cache folder. Read-only on the source.
set -e
A=/home/user/ring-tokat-3d/cocuk-kanali/ali-baba
O=$A/yeni4/analiz/tempo
mkdir -p $O/gecici
ffmpeg -hide_banner -loglevel error -y -i $A/v2_2.mp3 -ar 44100 -ac 1 $O/gecici/mix_44k_mono.wav
ffprobe -hide_banner $O/gecici/mix_44k_mono.wav 2>&1 | tail -2
