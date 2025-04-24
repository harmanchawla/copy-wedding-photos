import os
import pickle

from typing import Optional
from pydantic import BaseModel, DirectoryPath, FilePath, ValidationError

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class InputData(BaseModel):
    local_directory: DirectoryPath
    credentials_file: FilePath
    parent_folder_id: Optional[str] = None  # Optional Google Drive folder ID


def authenticate_google_drive(credentials_file: str):
    """
    Authenticate the user and return the Google Drive API service.
    """
    creds = None
    # Check if token.pickle exists (saved credentials)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If no valid credentials, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)


def create_folder(service, folder_name, parent_folder_id=None):
    """
    Create a folder in Google Drive.
    """
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        print(f"Error creating folder '{folder_name}': {e}")
        return None


def upload_file(service, file_path, parent_folder_id=None):
    """
    Upload a file to Google Drive.
    """
    try:
        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        print(f"Error uploading file '{file_path}': {e}")
        return None


def upload_directory(service, local_directory, parent_folder_id=None):
    """
    Recursively upload a directory (and its subdirectories) to Google Drive.
    """
    for root, dirs, files in os.walk(local_directory):
        # Create folders in Google Drive for each subdirectory
        relative_path = os.path.relpath(root, local_directory)
        current_folder_id = parent_folder_id
        if relative_path != '.':
            folder_names = relative_path.split(os.sep)
            for folder_name in folder_names:
                folder_id = create_folder(service, folder_name, current_folder_id)
                if folder_id is None:
                    print(f"Failed to create folder '{folder_name}'. Skipping...")
                    return
                current_folder_id = folder_id

        # Upload files in the current directory
        for file_name in files:
            file_path = os.path.join(root, file_name)
            upload_file(service, file_path, current_folder_id)


def validate_inputs(local_directory: str, credentials_file: str, parent_folder_id: Optional[str] = None) -> InputData:
    """
    Validate the inputs using Pydantic.
    """
    try:
        return InputData(
            local_directory=local_directory,
            credentials_file=credentials_file,
            parent_folder_id=parent_folder_id,
        )
    except ValidationError as e:
        print(f"Input validation error:\n{e}")
        exit(1)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Upload a directory to Google Drive.")
    parser.add_argument(
        "--local_directory", "-ld", 
        help="Path to the local directory to upload.", 
        required=True
    )
    parser.add_argument(
        "--credentials_file", "-creds", 
        help="Path to the Google API credentials JSON file.", 
        required=True
    )
    parser.add_argument(
        "--parent_folder_id", "-pfid", 
        help="Google Drive folder ID to upload into (optional).", 
        default=None
    )

    args = parser.parse_args()

    # Validate inputs
    validated_data = validate_inputs(args.local_directory, args.credentials_file, args.parent_folder_id)

    # Authenticate and get the Google Drive service
    service = authenticate_google_drive(validated_data.credentials_file)

    # Upload the directory
    try:
        upload_directory(service, validated_data.local_directory, validated_data.parent_folder_id)
        print("Upload complete!")
    except Exception as e:
        print(f"An error occurred during the upload process: {e}")
