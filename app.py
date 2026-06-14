from flask import (
    Flask, render_template, request,
    redirect, url_for, send_file, session, flash
)
from datetime import datetime
from io import BytesIO
import os
import pandas as pd
from tempfile import NamedTemporaryFile
import zipfile
from pathlib import Path
import csv

from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    CARD_OUTPUT_FOLDER,
)
from database import db, Student, CardBatch, Card
from services.helper import save_upload, extract_photos_zip, import_students_from_csv
from services.id_card_generator import generate_card_images
from services.pdf_service import build_batch_pdf
from sqlalchemy import or_


CSV_PATH = Path("data") / "students.csv"


# SIMPLE ADMIN CREDENTIALS
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"   # college demo ke liye


def login_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # ------------- AUTH --------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session["is_admin"] = True
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ------------- YEAR WISE STUDENTS --------------

    @app.route("/students_by_year")
    @login_required
    def students_by_year():
        # Dropdown se aane wala value: "FY" / "SY" / "TY" / None
        year = request.args.get("year")
        # Search text: name / ID
        q = request.args.get("q", "").strip()

        query = Student.query

        # FY / SY / TY -> class_name ke start me FY/SY/TY hota hai
        if year:
            query = query.filter(Student.class_name.ilike(f"{year}%"))

        # Sirf name + ID search
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(like),     # name
                    Student.student_code.ilike(like),  # ID
                )
            )

        students = query.order_by(Student.full_name).all()
        return render_template(
            "students_by_year.html",
            students=students,
            selected_year=year,
            q=q,
        )

    # Screen 1: CSV + ZIP upload (home)
    @app.route("/", methods=["GET"])
    @login_required
    def index():
        msg = request.args.get("msg")
        msg_type = request.args.get("type", "success")
        return render_template("index.html", home_message=msg, home_type=msg_type)

    @app.route("/process", methods=["POST"])
    @login_required
    def process_files():
        csv_file = request.files.get("csv_file")
        photos_zip = request.files.get("photos_zip")

        if not csv_file or not photos_zip:
            return redirect(
                url_for(
                    "index",
                    msg="CSV/Excel or Photos ZIP missing.",
                    type="error",
                )
            )

        # ---------- CSV ya Excel check ----------
        filename = csv_file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower()

        if ext in ("xlsx", "xls"):
            try:
                df = pd.read_excel(csv_file)
            except Exception:
                return redirect(
                    url_for(
                        "index",
                        msg="Could not read Excel file.",
                        type="error",
                    )
                )

            tmp = NamedTemporaryFile(delete=False, suffix=".csv")
            df.to_csv(tmp.name, index=False)
            csv_path = Path(tmp.name)
        elif ext == "csv":
            csv_path = save_upload(csv_file, "students")
        else:
            return redirect(
                url_for(
                    "index",
                    msg="Please upload .csv or .xlsx/.xls file only.",
                    type="error",
                )
            )

        zip_path = save_upload(photos_zip, "photos")
        extract_photos_zip(zip_path)

        students = import_students_from_csv(csv_path)

        if not students:
            return redirect(
                url_for(
                    "index",
                    msg="No students found in file.",
                    type="error",
                )
            )

        ids = ",".join(str(s.id) for s in students)
        return redirect(url_for("preview_cards", ids=ids))

    # -------- Promote select (pass students) --------

    @app.route("/promote-select", methods=["GET", "POST"])
    @login_required
    def promote_select():
        # URL se filter values (GET request ke liye)
        from_class = request.args.get("from_class", "").strip()
        from_year = request.args.get("from_year", "").strip()

        if request.method == "POST":
            # Form se data (POST)
            from_class = request.form.get("from_class", "").strip()
            from_year = request.form.get("from_year", "").strip()
            to_class = request.form.get("to_class", "").strip()
            to_year = request.form.get("to_year", "").strip()

            # Checkbox se selected ids ki list
            raw_ids = request.form.getlist("student_ids")  # ['1','5','9', ...]
            selected_ids = [int(x) for x in raw_ids]

            if not selected_ids:
                flash("No students selected for promotion.", "error")
                return redirect(
                    url_for(
                        "promote_select",
                        from_class=from_class,
                        from_year=from_year,
                    )
                )

            # Sirf selected students ko update karo
            students = Student.query.filter(
                Student.id.in_(selected_ids)
            ).all()

            for s in students:
                s.class_name = to_class
                s.year_text = to_year

            db.session.commit()
            flash(f"{len(students)} students promoted.", "success")
            return redirect(url_for("students_list"))

        # GET: list dikhane ke liye
        students = []
        if from_class and from_year:
            students = (
                Student.query.filter_by(
                    class_name=from_class,
                    year_text=from_year,
                )
                .order_by(Student.full_name)
                .all()
            )

            if not students:
                flash("No students found for given class and year.", "error")

        return render_template(
            "promote_select.html",
            students=students,
            from_class=from_class,
            from_year=from_year,
        )

    # Add Student form + CSV store
    @app.route("/students/new", methods=["GET", "POST"])
    @login_required
    def add_student():
        if request.method == "POST":
            form = request.form

            student_code = form.get("student_code", "").strip()
            full_name = form.get("full_name", "").strip()
            address_line1 = form.get("address_line1", "").strip()
            address_line2 = form.get("address_line2", "").strip()
            address_line3 = form.get("address_line3", "").strip()
            class_name = form.get("class_name", "").strip()
            dob = form.get("dob", "").strip()
            blood_group = form.get("blood_group", "").strip()
            contact_no = form.get("contact_no", "").strip()
            year_text = form.get("year_text", "").strip()

            # Photo file (optional)
            photo_file = request.files.get("photo_file")
            photo_filename = f"{student_code}.jpg"

            if photo_file and photo_file.filename:
                photos_dir = Path("static/uploads/photos")
                photos_dir.mkdir(parents=True, exist_ok=True)
                full_path = photos_dir / photo_filename
                photo_file.save(full_path)
                photo_path = str(full_path)
            else:
                # old behaviour: expect from ZIP later
                photo_path = f"static/uploads/photos/{photo_filename}"

            # Required fields
            if not (
                student_code
                and full_name
                and address_line1
                and class_name
                and dob
                and contact_no
                and year_text
            ):
                return render_template(
                    "add_student.html",
                    message="All required fields must be filled.",
                    error=True,
                )

            # student_code: exactly 10 digits
            if not (student_code.isdigit() and len(student_code) == 10):
                return render_template(
                    "add_student.html",
                    message="Student Code must be exactly 10 digits (numbers only).",
                    error=True,
                )

            # contact_no: exactly 10 digits
            if not (contact_no.isdigit() and len(contact_no) == 10):
                return render_template(
                    "add_student.html",
                    message="Contact number must be exactly 10 digits.",
                    error=True,
                )

            # Duplicate check in DB
            if Student.query.filter_by(student_code=student_code).first():
                return render_template(
                    "add_student.html",
                    message="Student with this code already exists (duplicate).",
                    error=True,
                )

            from sqlalchemy.exc import IntegrityError

            student = Student(
                student_code=student_code,
                full_name=full_name,
                address_line1=address_line1,
                address_line2=address_line2,
                address_line3=address_line3,
                class_name=class_name,
                dob=dob,
                blood_group=blood_group,
                contact_no=contact_no,
                year_text=year_text,
                photo_path=photo_path,
            )

            try:
                db.session.add(student)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return render_template(
                    "add_student.html",
                    message="Student with this code already exists (duplicate).",
                    error=True,
                )

            # CSV append
            CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
            file_exists = CSV_PATH.is_file()
            with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(
                        [
                            "student_code",
                            "full_name",
                            "address_line1",
                            "address_line2",
                            "address_line3",
                            "class_name",
                            "dob",
                            "blood_group",
                            "contact_no",
                            "year_text",
                            "photo_filename",
                        ]
                    )
                writer.writerow(
                    [
                        student_code,
                        full_name,
                        address_line1,
                        address_line2,
                        address_line3,
                        class_name,
                        dob,
                        blood_group,
                        contact_no,
                        year_text,
                        photo_filename,
                    ]
                )

            return render_template(
                "add_student.html",
                message="Student saved successfully.",
                error=False,
            )

        return render_template("add_student.html")

    # Delete Data (CSV remove)
    @app.route("/students/delete_all", methods=["POST"])
    @login_required
    def delete_all_students():
        if CSV_PATH.is_file():
            CSV_PATH.unlink()
            msg = "All records deleted from data/students.csv."
        else:
            msg = "No CSV file found to delete."
        return redirect(url_for("index", msg=msg, type="error"))
    

    # Students list with search (for Edit)
    @app.route("/students")
    @login_required
    def students_list():
        q = request.args.get("q", "").strip()

        query = Student.query
        if q:
            query = query.filter(
                (Student.student_code.like(f"%{q}%"))
                | (Student.full_name.ilike(f"%{q}%"))
            )

        students = query.order_by(Student.student_code).all()
        return render_template("students_list.html", students=students, q=q)

    @app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_student(student_id):
        student = Student.query.get_or_404(student_id)

        if request.method == "POST":
            form = request.form

            student.full_name = form.get("full_name", student.full_name).strip()
            student.address_line1 = form.get(
                "address_line1", student.address_line1
            ).strip()
            student.address_line2 = form.get(
                "address_line2", student.address_line2
            ).strip()
            student.address_line3 = form.get(
                "address_line3", student.address_line3
            ).strip()
            student.class_name = form.get(
                "class_name", student.class_name
            ).strip()
            student.dob = form.get("dob", student.dob).strip()
            student.blood_group = form.get(
                "blood_group", student.blood_group
            ).strip()
            student.contact_no = form.get(
                "contact_no", student.contact_no
            ).strip()
            student.year_text = form.get(
                "year_text", student.year_text
            ).strip()

            db.session.commit()
            flash("Student details saved successfully.", "success")
            return redirect(url_for("students_list", q=student.student_code))

        return render_template("edit_student.html", student=student)

    # Preview
    @app.route("/preview")
    @login_required
    def preview_cards():
        ids = request.args.get("ids", "")
        id_list = [int(x) for x in ids.split(",") if x]
        students = Student.query.filter(Student.id.in_(id_list)).all()
        return render_template("preview.html", students=students)
    

    # Generate cards (PNG/PDF) - all students
    @app.route("/generate", methods=["POST"])
    @login_required
    def generate_cards():
        output_format = request.form.get("format", "PNG")

        students = Student.query.all()
        if not students:
            return redirect(
                url_for(
                    "index",
                    msg="No students to generate.",
                    type="error",
                )
            )

        batch = CardBatch(
            created_at=datetime.now(),
            output_format=output_format,
            output_file="",
        )
        db.session.add(batch)
        db.session.commit()

        cards = []
        for s in students:
            card = Card(
                student_id=s.id,
                batch_id=batch.id,
                qr_data=s.student_code,
                barcode_number=s.student_code,
            )
            db.session.add(card)
            db.session.flush()
            generate_card_images(s, card)
            cards.append(card)

        db.session.commit()

        if output_format == "PDF":
            buffer, pdf_path = build_batch_pdf(students, cards)
            batch.output_file = pdf_path
            db.session.commit()
        else:
            Path(CARD_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
            zip_path = Path(CARD_OUTPUT_FOLDER) / f"batch_{batch.id}_cards.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for c in cards:
                    if c.front_image_path and os.path.exists(c.front_image_path):
                        zf.write(
                            c.front_image_path,
                            arcname=Path(c.front_image_path).name,
                        )
                    if c.back_image_path and os.path.exists(c.back_image_path):
                        zf.write(
                            c.back_image_path,
                            arcname=Path(c.back_image_path).name,
                        )
            batch.output_file = str(zip_path)
            db.session.commit()

        return redirect(url_for("success", batch_id=batch.id))

    # -------- Generate IDs by Class --------

    @app.route("/generate-class", methods=["GET", "POST"])
    @login_required
    def generate_class_cards():
        if request.method == "POST":
            class_name = request.form.get("class_name", "").strip()
            year_text = request.form.get("year_text", "").strip()
            output_format = request.form.get("format", "PNG")

            if not (class_name and year_text):
                flash("Class and Academic Year are required.", "error")
                return redirect(url_for("generate_class_cards"))

            students = (
                Student.query.filter_by(
                    class_name=class_name,
                    year_text=year_text,
                )
                .order_by(Student.student_code)
                .all()
            )

            if not students:
                flash("No students found for given class and year.", "error")
                return redirect(url_for("generate_class_cards"))

            batch = CardBatch(
                created_at=datetime.now(),
                output_format=output_format,
                output_file="",
            )
            db.session.add(batch)
            db.session.commit()

            cards = []
            for s in students:
                card = Card(
                    student_id=s.id,
                    batch_id=batch.id,
                    qr_data=s.student_code,
                    barcode_number=s.student_code,
                )
                db.session.add(card)
                db.session.flush()
                generate_card_images(s, card)
                cards.append(card)

            db.session.commit()

            if output_format == "PDF":
                buffer, pdf_path = build_batch_pdf(students, cards)
                batch.output_file = pdf_path
                db.session.commit()
            else:
                Path(CARD_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
                zip_path = Path(CARD_OUTPUT_FOLDER) / f"batch_{batch.id}_cards.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for c in cards:
                        if c.front_image_path and os.path.exists(c.front_image_path):
                            zf.write(
                                c.front_image_path,
                                arcname=Path(c.front_image_path).name,
                            )
                        if c.back_image_path and os.path.exists(c.back_image_path):
                            zf.write(
                                c.back_image_path,
                                arcname=Path(c.back_image_path).name,
                            )
                batch.output_file = str(zip_path)
                db.session.commit()

            return redirect(url_for("success", batch_id=batch.id))

        # GET: sirf form dikhana
        return render_template("generate_class.html")

        # -------- Delete selected students (hard delete) --------

    @app.route("/students/delete_selected", methods=["POST"])
    @login_required
    def delete_selected_students():
        raw_ids = request.form.getlist("student_ids")
        selected_ids = [int(x) for x in raw_ids if x.isdigit()]

        if not selected_ids:
            flash("No students selected for deletion.", "error")
            return redirect(url_for("students_list"))

        # --- Pehle related cards delete karo ---
        cards = Card.query.filter(Card.student_id.in_(selected_ids)).all()
        for c in cards:
            db.session.delete(c)

        # --- Ab students delete karo ---
        students = Student.query.filter(Student.id.in_(selected_ids)).all()
        count = len(students)
        for s in students:
            db.session.delete(s)

        db.session.commit()

        flash(f"{count} students deleted successfully.", "success")
        return redirect(url_for("students_list"))

    # -------- Single student generate (PDF/PNG) --------

    @app.route("/generate_one/<int:student_id>")
    @login_required
    def generate_one(student_id):
        student = Student.query.get_or_404(student_id)
        output_format = request.args.get("format", "PNG")

        batch = CardBatch(
            created_at=datetime.now(),
            output_format=output_format,
            output_file="",
        )
        db.session.add(batch)
        db.session.commit()

        card = Card(
            student_id=student.id,
            batch_id=batch.id,
            qr_data=student.student_code,
            barcode_number=student.student_code,
        )
        db.session.add(card)
        db.session.flush()
        generate_card_images(student, card)
        db.session.commit()

        if output_format == "PDF":
            buffer, pdf_path = build_batch_pdf([student], [card])
            batch.output_file = pdf_path
            db.session.commit()
            return send_file(pdf_path, as_attachment=True)
        else:
            Path(CARD_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
            zip_path = Path(CARD_OUTPUT_FOLDER) / f"single_{batch.id}_card.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if card.front_image_path and os.path.exists(card.front_image_path):
                    zf.write(
                        card.front_image_path,
                        arcname=Path(card.front_image_path).name,
                    )
                if card.back_image_path and os.path.exists(card.back_image_path):
                    zf.write(
                        card.back_image_path,
                        arcname=Path(card.back_image_path).name,
                    )
            batch.output_file = str(zip_path)
            db.session.commit()
            return send_file(zip_path, as_attachment=True)

    # Success
    @app.route("/success")
    @login_required
    def success():
        batch_id = request.args.get("batch_id", type=int)
        return render_template("success.html", batch_id=batch_id)

    @app.route("/download/<int:batch_id>")
    @login_required
    def download_batch(batch_id):
        batch = CardBatch.query.get_or_404(batch_id)

        if not batch.output_file or not os.path.exists(batch.output_file):
            return "Output file not found. Please generate again.", 404

        return send_file(batch.output_file, as_attachment=True)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
