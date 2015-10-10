# Introduction

Add Aliyun-OSS file storage support in Scrapy, like S3FilesStore.

# Prerequisite

Install Aliyun OSS python sdk into you python envs, go to [official](https://docs.aliyun.com/?spm=5176.100057.3.4.NNu7cf#/pub/oss/sdk/sdk-download&python) to download

# How to use

- Put the code in pipeline.py into your own pipleline file
- Add variables as blow into you settings.py
  - IMAGES_STORE = 'alioss://dlimgs'    # image storage type, dlimgs is the name of your bucket which to store files
  - ALI_OSS_ACCESS_KEY_ID = 'your-access-key'     # access-key-id
  - ALI_OSS_ACCESS_KEY_SECRET = 'your-access-key-secret'    # access-key
  - ALI_OSS_ENDPOINT = 'your-oss-endpoint'   # oss endpoint, eg: oss-cn-beijing.aliyuncs.com
- Put CustomizedImagesPipeline class full path into ITEM_PIPELINES = {}, with a high priority
- Advise: you should set IMAGES_EXPIRES varibale in settings.py, which could avoid the nonsense downloading same images and accessing Aliyun OSS repeatly

