#!/bin/bash
# Denetim: sure, cozunurluk, ilk saniyeler, ses seviyesi. Hicbir mevcut dosyayi degistirmez.
K=/home/user/ring-tokat-3d/cocuk-kanali
O=$K/buyume/denetim
declare -A V=(
 [1-alibaba]=$K/ali-baba/ali-babanin-ciftligi-kisa.mp4
 [2-aile]=$K/pitirin-ailesi/pitirin-ailesi.mp4
 [3-parmak]=$K/parmak-ailesi/parmak-ailesi.mp4
 [4-maymun]=$K/bes-kucuk-maymun/bes-kucuk-maymun.mp4
 [5-balon]=$K/balon-sarkisi/balon-sarkisi.mp4
 [6-elyikama]=$K/el-yikama/el-yikama-sarkisi.mp4
 [7-otobus]=$K/otobus-sarkisi/otobus-sarkisi.mp4
)
echo "ad,sure_sn,genislik,yukseklik,fps,video_kbps,ses_codec,ses_hz,boyut_mb,lufs_I,true_peak,ilk_sessizlik_bitis,ilk_kesme_sn,bastaki_siyah" > $O/olcum.csv
for ad in $(echo "${!V[@]}" | tr ' ' '\n' | sort); do
 f=${V[$ad]}
 dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
 vs=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,bit_rate -of csv=p=0 "$f")
 as=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate -of csv=p=0 "$f")
 mb=$(du -m "$f" | cut -f1)
 lu=$(ffmpeg -hide_banner -nostats -i "$f" -vn -af ebur128=peak=true -f null - 2>&1 | tail -12 | tr '\n' ' ' | sed -E 's/.*I: +(-?[0-9.]+) LUFS.*Peak: +(-?[0-9.]+) dBFS.*/\1,\2/')
 sil=$(ffmpeg -hide_banner -nostats -t 8 -i "$f" -vn -af silencedetect=noise=-40dB:d=0.2 -f null - 2>&1 | grep -m1 silence_end | sed -E 's/.*silence_end: ([0-9.]+).*/\1/')
 cut=$(ffmpeg -hide_banner -nostats -t 15 -i "$f" -an -vf "scale=320:-2,select='gt(scene,0.30)',showinfo" -f null - 2>&1 | grep -o 'pts_time:[0-9.]*' | head -4 | sed 's/pts_time://' | tr '\n' ' ')
 blk=$(ffmpeg -hide_banner -nostats -t 4 -i "$f" -an -vf "scale=320:-2,blackdetect=d=0.1:pix_th=0.10" -f null - 2>&1 | grep -o 'black_start:[0-9.]* black_end:[0-9.]*' | head -1)
 echo "$ad,$dur,$vs,$as,$mb,$lu,${sil:-yok},\"${cut:-yok}\",\"${blk:-yok}\"" >> $O/olcum.csv
 e=$(python3 -c "print(max(0,float('$dur')-1.0))")
 i=0
 for t in 0.0 0.5 2.5 5.0 $e; do
  i=$((i+1))
  ffmpeg -hide_banner -loglevel error -y -ss $t -i "$f" -frames:v 1 -vf scale=640:360 -q:v 3 $O/kareler/${ad}_k${i}_${t}.jpg
 done
done
cat $O/olcum.csv
