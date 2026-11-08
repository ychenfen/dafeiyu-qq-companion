#!/bin/bash
# 刷新 NapCat 二维码并落到 ./qrcode.png，同时打印解码 URL
cd "$(dirname "$0")" || exit 1
docker restart deepfish-napcat >/dev/null || exit 1
sleep 6
docker cp deepfish-napcat:/app/napcat/cache/qrcode.png ./qrcode.png >/dev/null 2>&1
echo "二维码图片: $(pwd)/qrcode.png"
echo -n "解码 URL: "
docker logs --since 2m deepfish-napcat 2>&1 | grep -o 'https://txz.qq.com/p?k=[^ ]*' | tail -1
echo "WebUI: http://127.0.0.1:6099/webui?token=deepfish-local"
