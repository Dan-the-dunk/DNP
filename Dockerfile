FROM nvidia/cuda:11.2.2-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN  apt-get update && apt-get install -y python3.9\
                            python3-pip  # Install Python 3

WORKDIR ./ 

COPY ./requirements.txt . 

RUN pip install torch torchvision torchaudio

RUN pip install -r requirements.txt  

RUN DEBIAN_FRONTEND=noninteractive  apt-get install -y ffmpeg libsm6 libxext6

RUN pip install mmengine


COPY . .

CMD ["echo", "Hello world!"]

