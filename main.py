import dropbox, os, time, logging, sys, traceback
from dotenv import load_dotenv

# Configuration
BACKUP_LIMIT = 2000
BACKUP_FOLDER = "/mnt/fileserver/keys/old"
DROPBOX_FOLDER = "/files/"
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs/backuper.log")

class Backup:
    """A class to handle backing up files to Dropbox."""
    def __init__(self, key, secret, refresh):
        """
        Initializes the Backup object.

        Args:
            key (str): The Dropbox API key.
            secret (str): The Dropbox API secret.
            refresh (str): The Dropbox API refresh token.
        """
        self.dbx = dropbox.Dropbox(
            app_key=key,
            app_secret=secret,
            oauth2_refresh_token=refresh
        )
        self.setup_logging()

    def setup_logging(self):
        """Sets up logging for the script."""
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        self.logger = logging.getLogger('logger')
        fh = logging.FileHandler(LOG_FILE)
        self.logger.addHandler(fh)
        sys.excepthook = self.exc_handler

    def exc_handler(self, exctype, value, tb):
        """Handles uncaught exceptions and logs them."""
        self.logger.exception(''.join(traceback.format_exception(exctype, value, tb)))

    def get_remote_files(self):
        """
        Gets the list of files from the Dropbox folder.

        Returns:
            list: A list of file names in the Dropbox folder.
        """
        try:
            response = self.dbx.files_list_folder(path=DROPBOX_FOLDER)
            return [entry.name for entry in response.entries]
        except dropbox.exceptions.ApiError as err:
            self.logger.error(f"Dropbox API error: {err}")
            return []

    def upload_new_files(self, local_files, remote_files):
        """
        Uploads new files from the local backup folder to Dropbox.

        Args:
            local_files (list): A list of file names in the local backup folder.
            remote_files (list): A list of file names in the Dropbox folder.
        """
        new_files = [f for f in local_files if f not in remote_files]
        self.logger.info(f"Found {len(new_files)} new files to back up.")
        for file in new_files:
            file_from = os.path.join(BACKUP_FOLDER, file)
            file_to = f'{DROPBOX_FOLDER}{file}'
            try:
                with open(file_from, 'rb') as f:
                    self.dbx.files_upload(f.read(), file_to)
                self.logger.info(f"Backed up: {file}")
                print(f"Backed up: {file}")
            except Exception as e:
                self.logger.error(f"Error backing up {file}: {e}")

    def enforce_backup_limit(self, remote_files):
        """
        Enforces the backup limit by deleting the oldest files.

        Args:
            remote_files (list): A list of file names in the Dropbox folder.
        """
        num_files_to_delete = len(remote_files) - BACKUP_LIMIT
        if num_files_to_delete > 0:
            self.logger.info(f"Backup limit exceeded. Deleting {num_files_to_delete} oldest files.")
            try:
                response = self.dbx.files_list_folder(path=DROPBOX_FOLDER, include_media_info=True)
                files = sorted(response.entries, key=lambda x: x.server_modified)
                for i in range(num_files_to_delete):
                    oldest_file = files[i]
                    self.dbx.files_delete(f'{DROPBOX_FOLDER}{oldest_file.name}')
                    os.remove(os.path.join(BACKUP_FOLDER, oldest_file.name))
                    self.logger.info(f"Deleted oldest backup: {oldest_file.name}")
                    print(f"Deleted: {oldest_file.name}")
            except Exception as e:
                self.logger.error(f"Error deleting oldest backup: {e}")

    def run(self):
        """Runs the main backup loop."""
        while True:
            local_files = os.listdir(BACKUP_FOLDER)
            remote_files = self.get_remote_files()

            if set(local_files) != set(remote_files):
                self.upload_new_files(local_files, remote_files)
                # Refresh remote file list after upload
                remote_files = self.get_remote_files()
                self.enforce_backup_limit(remote_files)

            time.sleep(1)

def main():
    """The main function of the script."""
    load_dotenv()
    key = os.getenv('KEY')
    secret = os.getenv('SECRET')
    refresh = os.getenv('REFRESH')

    if not all([key, secret, refresh]):
        print("Error: KEY, SECRET, and REFRESH environment variables must be set.")
        sys.exit(1)

    backup = Backup(key, secret, refresh)
    backup.run()

if __name__ == "__main__":
    main()