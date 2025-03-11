# openai-cua

## build the image
docker build -t cua-image .

## run the container
docker run --rm -it --name cua-image -p 5900:5900 -e DISPLAY=:99 cua-image