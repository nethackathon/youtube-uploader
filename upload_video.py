#! /usr/bin/env python

import click
import http.client
import httplib2
import logging
import os
from pathlib import Path
import random
import re
import requests
import time

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
import google_auth_oauthlib.helpers


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)

# Always retry when an googleapiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.cloud.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = Path(__file__).parent.joinpath("client_secrets.json")
REFRESH_TOKEN_FILE = Path(__file__).parent.joinpath("refresh_token")

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = f"""
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   {CLIENT_SECRETS_FILE}

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

# VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_api_key_service():
    load_dotenv()
    DEVELOPER_KEY = os.environ.get("GOOGLE_API_KEY")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=YOUTUBE_UPLOAD_SCOPE)

    # Attempt to read refresh token from file, if that fails, do the whole auth flow again,
    # then write the refresh token to a file.
    try:
        with REFRESH_TOKEN_FILE.open() as f:
            refresh_token = f.read()

        flow.oauth2session.refresh_token(
            flow.client_config["token_uri"],
            refresh_token=refresh_token,
            client_id=flow.client_config["client_id"],
            client_secret=flow.client_config["client_secret"],
        )
        credentials = google_auth_oauthlib.helpers.credentials_from_session(flow.oauth2session, flow.client_config)
    except Exception as e:
        logging.exception(e)
        logging.info(f"Refresh token at {REFRESH_TOKEN_FILE} didn't work, redoing auth")
        credentials = flow.run_local_server()

    logging.info(f"Saving refresh token to {REFRESH_TOKEN_FILE}")
    with open(REFRESH_TOKEN_FILE, "w") as f:
        f.write(credentials.refresh_token)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def initialize_upload(youtube, file, title, description="", tags=None, category="20", privacy_status="private"):
    if tags is None:
        tags = []

    body = dict(
        snippet=dict(title=title, description=description, tags=tags, categoryId=category),
        status=dict(privacyStatus=privacy_status, selfDeclaredMadeForKids=False),
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True),
    )

    resumable_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logging.info("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if "id" in response:
                    logging.info("Video id '%s' was successfully uploaded." % response["id"])
                else:
                    exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            logging.error(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2**retry
            sleep_seconds = random.random() * max_sleep
            logging.info("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)


def upload(video: Path, title):
    youtube = get_authenticated_service()
    #title = f"{title} {video.parent.name}"

    try:
        initialize_upload(youtube, video, title)
    except HttpError as e:
        logging.error("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


@click.command()
@click.argument("url")
@click.option("--title", help="A prefix for the video title on youtube", default="Nethackathon VI:")
def main(url, title):
    logging.basicConfig(level=logging.INFO)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a"):
            href = link.get("href")
            # Only uploading six at a time, to conform to our current quota of 10,000 per day (1600 * 6)
            if re.match(r'^(13|14|15|16|17|18)-\w+/$', href):
                response = requests.get(f"{url}{href}")
                soup = BeautifulSoup(response.text, "html.parser")
                for file_link in soup.find_all("a"):
                    file_href = file_link.get("href")
                    if re.match(r'^\d+\.mp4$', file_href):
                        logging.info(f"Downloading {url}{href}{file_href}")
                        response = requests.get(f"{url}{href}{file_href}", stream=True)
                        if response.status_code == 200:
                            with open(f"downloaded/{file_href}", "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logging.info(f"Uploading {file_href}")
                            upload(Path(f"downloaded/{file_href}"), f"{href[:-1]} NetHackathon Fall 2023")
                            os.remove(f"downloaded/{file_href}")


    #directory = Path(directory)
    #videos = sorted(p for p in directory.glob("**/*.mp4") if "chat" not in p.name)
    #for v in videos:
    #    upload(v, title)


if __name__ == "__main__":
    main()
