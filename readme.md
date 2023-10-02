# Nethackathon youtube uploader

Uploads videos from nethackathon to youtube. Uploaded videos will be set to private, you can make them public in youtube manually once you have checked and trimmed them. Youtube requires google oauth flow to upload videos to your channel (api keys do not work).

Once only preparation steps:

1. make a google cloud project https://console.cloud.google.com/projectcreate
1. make yourself some credentials at https://console.cloud.google.com/projectselector2/apis/credentials
1. download them into `client_secrets.json`
1. enable the youtube api for the google cloud project
1. add yourself as a test user on the oath consent screen settings https://console.cloud.google.com/apis/credentials/consent

Running:

1. edit `download.sh` with the location to jjvantheman's scraped videos for the current nethackathon
1. run `./download.sh /some/path/to/downloaded/videos` (will resume from where it left off if interrupted and re-ran)
1. make a python virtualenv and activate it
1. `pip install -r requirements.txt`
1. `./upload_video.py /some/path/to/downloaded/videos --title="Nethackathon XVIXX:"

The first time you will be prompted for google credentials, they will then be saved to a file called `refresh_token`, this will be valid for some time (months I think) without having to redo the auth.

You may hit youtube quota limits pretty easily... might need to request an increase or start the free $300 trial thingy.
