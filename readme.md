# Nethackathon youtube uploader

Uploads videos from nethackathon to youtube. Uploaded videos will be set to private, you can make them public in youtube manually once you have checked and trimmed them. Youtube requires google oauth flow to upload videos to your channel (api keys do not work).

Once only preparation steps:

. make a google cloud project https://console.cloud.google.com/projectcreate
. make yourself some credentials at https://console.cloud.google.com/projectselector2/apis/credentials
. download them into `client_secrets.json`
. enable the youtube api for the google cloud project
. add yourself as a test user on the oath consent screen settings https://console.cloud.google.com/apis/credentials/consent

Running:

. edit `download.sh` with the location to jjvantheman's scraped videos for the current nethackathon
. cd where you want the videos and run `./download.sh`
. make a python virtualenv and activate it
. `pip install -r requirements.txt`
. `./upload_video.py /some/path/to/downloaded/videos --title="Nethackathon XVIXX:"

The first time you will be prompted for google credentials, they will then be saved to a file called `refresh_token`, this will be valid for some time without having to redo the auth.
