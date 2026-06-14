import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "change-this-secret-key"

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Upload + generated files
RAW_UPLOAD_FOLDER   = os.path.join(BASE_DIR, "static", "uploads", "raw")      # CSV + ZIP
PHOTO_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "photos")   # extracted photos
CARD_OUTPUT_FOLDER  = os.path.join(BASE_DIR, "static", "uploads", "cards")    # final PNG/PDF

ASSETS_FOLDER = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_FOLDER, "logos", "college_logo.png")
PRINCIPAL_SIGN_PATH = os.path.join(ASSETS_FOLDER, "signatures", "principal_sign.png")
FRONT_BG_PATH = os.path.join(ASSETS_FOLDER, "backgrounds", "front_bg.png")
BACK_BG_PATH  = os.path.join(ASSETS_FOLDER, "backgrounds", "back_bg.png")

FONTS_FOLDER = os.path.join(ASSETS_FOLDER, "fonts")
FONT_REGULAR = os.path.join(FONTS_FOLDER, "Poppins-Regular.ttf")
FONT_BOLD    = os.path.join(FONTS_FOLDER, "Poppins-Bold.ttf")

for path in [RAW_UPLOAD_FOLDER, PHOTO_UPLOAD_FOLDER, CARD_OUTPUT_FOLDER]:
    os.makedirs(path, exist_ok=True)
