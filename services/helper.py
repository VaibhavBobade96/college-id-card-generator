import csv
import os
import zipfile
from datetime import datetime

from werkzeug.utils import secure_filename

from config import RAW_UPLOAD_FOLDER, PHOTO_UPLOAD_FOLDER
from database import db, Student


def save_upload(file_storage, sub_name: str) -> str:
    """
    Generic saver: CSV / ZIP.
    Returns absolute path.
    """
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sub_name}_{file_storage.filename}")
    path = os.path.join(RAW_UPLOAD_FOLDER, filename)
    file_storage.save(path)
    return path


def extract_photos_zip(zip_path: str) -> None:
    """
    photos.zip ko PHOTO_UPLOAD_FOLDER me extract karega.
    Folder already config.py me create ho raha hai.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(PHOTO_UPLOAD_FOLDER)


def import_students_from_csv(csv_path: str) -> list[Student]:
    """
    CSV read karke Student rows create kare.
    Expected columns (header row):
    student_code,full_name,class_name,year_text,dob,contact_no,blood_group,
    address_line1,address_line2,address_line3
    """
    created_students: list[Student] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("student_code") or row.get("id") or row.get("roll_no")
            if not code:
                continue

            # photo filename convention: <student_code>.jpg / .png
            photo_jpg = os.path.join(PHOTO_UPLOAD_FOLDER, f"{code}.jpg")
            photo_png = os.path.join(PHOTO_UPLOAD_FOLDER, f"{code}.png")
            photo_path = None
            if os.path.exists(photo_jpg):
                photo_path = photo_jpg
            elif os.path.exists(photo_png):
                photo_path = photo_png

            student = Student(
                student_code=str(code),
                full_name=row.get("full_name", "").strip(),
                class_name=row.get("class_name", "").strip(),
                year_text=row.get("year_text", "").strip(),
                dob=row.get("dob", "").strip(),
                contact_no=row.get("contact_no", "").strip(),
                blood_group=row.get("blood_group", "").strip(),
                address_line1=row.get("address_line1", "").strip(),
                address_line2=row.get("address_line2", "").strip(),
                address_line3=row.get("address_line3", "").strip(),
                photo_path=photo_path,
            )
            db.session.add(student)
            created_students.append(student)

    db.session.commit()
    return created_students
