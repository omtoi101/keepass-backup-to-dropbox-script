import dropbox, os, time, logging, sys, traceback
from dotenv import load_dotenv

backup_limit = 2000
os.makedirs(os.path.join(os.path.dirname(__file__), "logs/"), exist_ok=True)
logger = logging.getLogger('logger')
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs/backuper.log"))
logger.addHandler(fh)
def exc_handler(exctype, value, tb):
    logger.exception(''.join(traceback.format_exception(exctype, value, tb)))
sys.excepthook = exc_handler


load_dotenv()
key = os.getenv('KEY')
secret = os.getenv('SECRET')
refresh = os.getenv('REFRESH')
dbx = dropbox.Dropbox(
            app_key = key,
            app_secret = secret,
            oauth2_refresh_token = refresh
        )


backup_folder = "/mnt/fileserver/keys/old"
dir_list = []
response = dbx.files_list_folder(path="/files/")
for entry in response.entries:
  dir_list.append(entry.name)
while True:
  files = os.listdir(backup_folder)

  if files != dir_list:
    time.sleep(1)
    new = []
    for file in files:
       if file not in dir_list:
          new.append(file)
    for file in new:
      file_from = os.path.join(backup_folder, file)
      file_to = f'/files/{file}'
      f = open(file_from, 'rb')
      dbx.files_upload(f.read(), file_to)
      print(f"Backed up: {file}")
    dir_list = []
    response = dbx.files_list_folder(path="/files/")
    for entry in response.entries:
      dir_list.append(entry.name)
    if len(dir_list) > backup_limit:
        b_age = None
        b_oldest = ""
        dir_list = []
        response = dbx.files_list_folder(path="/files/")
        for entry in response.entries:
          dir_list.append(entry.name)
        print(f"Deleted: {dir_list[0]}")
        dbx.files_delete(f'/files/{dir_list[0]}')
        os.remove(os.path.join(backup_folder, dir_list[0]))