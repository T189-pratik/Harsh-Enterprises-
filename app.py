import os, json, re, uuid
from bs4 import BeautifulSoup
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename







BASE_DIR = os.path.dirname(os.path.abspath(__file__))



LEGACY_DIR = os.path.join(BASE_DIR, "legacy") if os.path.isdir(os.path.join(BASE_DIR, "legacy")) else BASE_DIR



UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")



os.makedirs(UPLOAD_DIR, exist_ok=True)







app = Flask(__name__)



app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")







# MySQL is used when MYSQL_HOST is supplied; otherwise SQLite makes local setup easy.



if os.environ.get("MYSQL_HOST"):



    user = os.environ.get("MYSQL_USER", "root")



    pwd = os.environ.get("MYSQL_PASSWORD", "")



    host = os.environ.get("MYSQL_HOST", "localhost")



    port = os.environ.get("MYSQL_PORT", "3306")



    dbname = os.environ.get("MYSQL_DATABASE", "harsh_admin")



    app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{dbname}"



else:



    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "harsh_admin.sqlite3")







app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False



app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024



db = SQLAlchemy(app)







class Category(db.Model):



    id = db.Column(db.Integer, primary_key=True)



    name = db.Column(db.String(120), nullable=False)



    slug = db.Column(db.String(140), unique=True, nullable=False)



    description = db.Column(db.Text, default="")



    nav_order = db.Column(db.Integer, default=0)



    active = db.Column(db.Boolean, default=True)



    projects = db.relationship("Project", backref="category", cascade="all, delete-orphan", lazy=True)







class Project(db.Model):



    id = db.Column(db.Integer, primary_key=True)



    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)



    name = db.Column(db.String(180), nullable=False)



    builder = db.Column(db.String(180), default="")



    features = db.Column(db.String(300), default="")



    price = db.Column(db.String(180), default="")



    location = db.Column(db.String(300), default="")



    description = db.Column(db.Text, default="")



    amenities = db.Column(db.Text, default="")



    faq = db.Column(db.Text, default="")



    brochure_url = db.Column(db.String(500), default="")



    video_url = db.Column(db.String(500), default="")



    main_image = db.Column(db.String(500), default="")



    gallery = db.Column(db.Text, default="[]")



    tags = db.Column(db.Text, default="[]")



    legacy_page = db.Column(db.String(255), default="")



    brochure_images = db.Column(db.Text, default="[]")



    flat_images = db.Column(db.Text, default="[]")



    legacy_details_synced = db.Column(db.Boolean, default=False)



    active = db.Column(db.Boolean, default=True)



    created_at = db.Column(db.DateTime, default=datetime.utcnow)



    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)







class AdminUser(db.Model):



    id = db.Column(db.Integer, primary_key=True)



    username = db.Column(db.String(100), unique=True, nullable=False)



    password_hash = db.Column(db.String(255), nullable=False)







def slugify(value):



    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value or "").strip().lower()



    return re.sub(r"[-\s]+", "-", value) or "category"







def unique_slug(name, current_id=None):



    base = slugify(name)



    slug = base



    i = 2



    while True:



        q = Category.query.filter_by(slug=slug)



        if current_id:



            q = q.filter(Category.id != current_id)



        if not q.first():



            return slug



        slug = f"{base}-{i}"



        i += 1







def json_list(value):



    try:



        x = json.loads(value or "[]")



        return x if isinstance(x, list) else []



    except Exception:



        return []







@app.template_filter("asset")



def asset_filter(path):



    if not path:



        return url_for("static", filename="images/he_logo3-removebg-preview_result.webp")



    if path.startswith("http://") or path.startswith("https://"):



        return path



    if path.startswith("/"):



        return path



    if path.startswith("images/"):



        return url_for("legacy_images", filename=path.split("images/",1)[1])



    if path.startswith("uploads/"):



        return url_for("static", filename=path)



    return url_for("static", filename="uploads/" + path)







@app.context_processor



def inject_helpers():



    return {"json_list": json_list}







def login_required(fn):



    @wraps(fn)



    def wrapper(*args, **kwargs):



        if not session.get("admin_id"):



            return redirect(url_for("admin_login", next=request.path))



        return fn(*args, **kwargs)



    return wrapper







def save_upload(file):



    if not file or not file.filename:



        return ""



    allowed = {"png","jpg","jpeg","webp","gif","svg","mp4","mov","pdf"}



    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""



    if ext not in allowed:



        raise ValueError("Unsupported file type.")



    name = secure_filename(file.filename)



    name = f"{uuid.uuid4().hex[:12]}_{name}"



    file.save(os.path.join(UPLOAD_DIR, name))



    return "uploads/" + name







def ensure_project_columns():



    """Add new dynamic-detail columns to an already-created local/host database."""



    inspector = db.inspect(db.engine)



    try:



        columns = {c["name"] for c in inspector.get_columns("project")}



    except Exception:



        columns = set()



    additions = {



        "brochure_images": "TEXT",



        "flat_images": "TEXT",



        "legacy_details_synced": "BOOLEAN DEFAULT 0",



    }



    changed = False



    for name, sql_type in additions.items():



        if name not in columns:



            db.session.execute(db.text(f"ALTER TABLE project ADD COLUMN {name} {sql_type}"))



            changed = True



    if changed:



        db.session.commit()











def legacy_images_from_block(block):



    result = []



    if not block:



        return result



    for im in block.find_all("img"):



        src = (im.get("src") or "").strip()



        if src.startswith("images/") and src not in result:



            result.append(src)



    return result











def backfill_legacy_details():

    """Import the real legacy detail content into the dynamic database.



    This keeps the old project's real Overview/gallery/brochure/flat-image

    content available on the new dynamic property page.

    """



    changed = False



    for p in Project.query.all():



        # Only old/legacy projects need this import.

        if not p.legacy_page:

            continue



        detail_path = os.path.join(LEGACY_DIR, p.legacy_page)



        if not os.path.isfile(detail_path):

            continue



        try:

            with open(detail_path, encoding="utf-8", errors="ignore") as f:

                soup = BeautifulSoup(f.read(), "html.parser")

        except Exception:

            continue



        # IMPORTANT:

        # Always take the real Overview from the old HTML page.

        # The old database may already contain a short meta description,

        # so checking "if not p.description" would prevent the real

        # Overview from being imported.

        overview = soup.find(id="overview")



        if overview:

            text = overview.get_text("\n", strip=True)



            if text and text != (p.description or "").strip():

                p.description = text

                changed = True



        # Keep only the property's top gallery in the main gallery.

        thumbs = soup.select("#thumbs img")

        main_img = soup.select_one("#mainImage")

        top_gallery = []



        if main_img and main_img.get("src", "").startswith("images/"):

            top_gallery.append(main_img.get("src"))



        for im in thumbs:

            src = (im.get("data-large") or im.get("src") or "").strip()



            if src.startswith("images/") and src not in top_gallery:

                top_gallery.append(src)



        if top_gallery:

            if json_list(p.gallery) != top_gallery:

                p.gallery = json.dumps(top_gallery)

                changed = True



            if not p.main_image:

                p.main_image = top_gallery[0]

                changed = True



        # Import brochure and flat/room images separately.

        brochure = legacy_images_from_block(soup.find(id="itinerary"))

        flat = legacy_images_from_block(soup.find(id="inclusions"))



        if brochure and json_list(p.brochure_images) != brochure:

            p.brochure_images = json.dumps(brochure)

            changed = True



        if flat and json_list(p.flat_images) != flat:

            p.flat_images = json.dumps(flat)

            changed = True



        # Import video if the project does not already have one.

        if not p.video_url:

            video = soup.find("video")



            if video and video.get("src"):

                p.video_url = video.get("src")

                changed = True



            else:

                iframe = soup.find("iframe")



                if iframe and iframe.get("src"):

                    p.video_url = iframe.get("src")

                    changed = True



        # Mark the legacy project as synced.

        if not p.legacy_details_synced:

            p.legacy_details_synced = True

            changed = True



    if changed:

        db.session.commit()



def seed_from_legacy():



    if Category.query.count() or Project.query.count():



        return



    # The current static site has these five sections.



    category_defs = [



        ("Ready to Move", "Immediate possession available properties with all amenities and ready for occupancy", 1),



        ("Top Highlighted Projects", "Premium and exclusive property selections with unique features and amenities", 2),



        ("Commercial Property", "Handpicked homes specially recommended for you by our expert team", 3),



        ("Under-Construction", "Exclusive Showcase Of Top Projects From Renowned And Trusted Developers", 4),



        ("Villas", "Leading Projects In villas With Excellent Investment Potential", 5),



    ]



    categories = []



    for name, desc, order in category_defs:



        c = Category(name=name, slug=unique_slug(name), description=desc, nav_order=order, active=True)



        db.session.add(c)



        categories.append(c)



    db.session.flush()







    # Import cards directly from the supplied static index.html.



    index_path = os.path.join(LEGACY_DIR, "index.html")



    if not os.path.exists(index_path):



        db.session.commit()



        return



    soup = BeautifulSoup(open(index_path, encoding="utf-8", errors="ignore").read(), "html.parser")



    section_map = {



        "ready-to-move": categories[0],



        "top-highlighted": categories[1],



        "recommended": categories[2],



        "Trusted": categories[3],



        "high-demand": categories[4],



    }



    for sid, cat in section_map.items():



        sec = soup.find(id=sid)



        if not sec:



            continue



        section = sec.find_next("section")



        if not section:



            continue



        for card in section.select(".card"):



            def txt(sel):



                el = card.select_one(sel)



                return el.get_text(" ", strip=True) if el else ""



            img = card.select_one(".image-container img")



            link = card.select_one(".btn-view")



            href = link.get("href", "") if link else ""



            main = img.get("src", "") if img else ""



            gallery = []



            if href:



                detail = os.path.join(LEGACY_DIR, href)



                if os.path.exists(detail):



                    d = BeautifulSoup(open(detail, encoding="utf-8", errors="ignore").read(), "html.parser")



                    for im in d.find_all("img"):



                        src = im.get("src", "")



                        if src.startswith("images/") and src not in gallery:



                            # Skip global social/logo images.



                            low = src.lower()



                            if any(x in low for x in ["he_logo", "facebook", "instagram", "whatsapp", "youtube", "goggle map"]):



                                continue



                            gallery.append(src)



            if main and main not in gallery:



                gallery.insert(0, main)



            desc = ""



            if href and os.path.exists(os.path.join(LEGACY_DIR, href)):



                d = BeautifulSoup(open(os.path.join(LEGACY_DIR, href), encoding="utf-8", errors="ignore").read(), "html.parser")



                meta = d.find("meta", attrs={"name":"description"})



                desc = meta.get("content","") if meta else ""



            tags = [t.get_text(" ", strip=True) for t in card.select(".tag")]



            p = Project(



                category_id=cat.id,



                name=txt("h3") or "Project",



                builder=txt(".builder"),



                features=txt(".features"),



                price=txt(".price"),



                description=desc,



                main_image=main,



                gallery=json.dumps(gallery[:20]),



                tags=json.dumps(tags),



                legacy_page=href,



                active=True



            )



            db.session.add(p)



    db.session.commit()







@app.route("/")



def home():



    categories = Category.query.filter_by(active=True).order_by(Category.nav_order.asc(), Category.id.asc()).all()



    return render_template("index_dynamic.html", categories=categories)







@app.route("/property/<int:project_id>")



def property_detail(project_id):



    project = Project.query.get_or_404(project_id)



    if not project.active and not session.get("admin_id"):



        abort(404)



    categories = Category.query.filter_by(active=True).order_by(Category.nav_order.asc(), Category.id.asc()).all()



    return render_template(



        "property_detail.html",



        project=project,



        categories=categories,



        gallery=json_list(project.gallery),



        brochure_images=json_list(project.brochure_images),



        flat_images=json_list(project.flat_images),



        tags=json_list(project.tags),



    )







@app.route("/admin/login", methods=["GET","POST"])



def admin_login():



    if request.method == "POST":



        username = request.form.get("username","").strip()



        password = request.form.get("password","")



        user = AdminUser.query.filter_by(username=username).first()



        if user and check_password_hash(user.password_hash, password):



            session["admin_id"] = user.id



            session["admin_username"] = user.username



            return redirect(request.args.get("next") or url_for("admin_dashboard"))



        flash("Invalid username or password.", "error")



    return render_template("admin/login.html")







@app.route("/admin/logout")



def admin_logout():



    session.clear()



    return redirect(url_for("admin_login"))







@app.route("/admin")



@app.route("/admin/dashboard")



@login_required



def admin_dashboard():



    return render_template("admin/dashboard.html",



        category_count=Category.query.count(),



        project_count=Project.query.count(),



        active_project_count=Project.query.filter_by(active=True).count())







@app.route("/admin/categories")



@login_required



def admin_categories():



    categories = Category.query.order_by(Category.nav_order.asc(), Category.id.asc()).all()



    return render_template("admin/categories.html", categories=categories)







@app.route("/admin/categories/add", methods=["GET","POST"])



@login_required



def admin_category_add():



    if request.method == "POST":



        name = request.form.get("name","").strip()



        if not name:



            flash("Category name is required.", "error")



        else:



            c = Category(name=name, slug=unique_slug(name),



                         description=request.form.get("description","").strip(),



                         nav_order=int(request.form.get("nav_order") or 0),



                         active=bool(request.form.get("active")))



            db.session.add(c); db.session.commit()



            flash("Category added.", "success")



            return redirect(url_for("admin_categories"))



    return render_template("admin/category_form.html", category=None)







@app.route("/admin/categories/edit/<int:category_id>", methods=["GET","POST"])



@login_required



def admin_category_edit(category_id):



    c = Category.query.get_or_404(category_id)



    if request.method == "POST":



        name = request.form.get("name","").strip()



        if not name:



            flash("Category name is required.", "error")



        else:



            c.name = name



            c.slug = unique_slug(name, c.id)



            c.description = request.form.get("description","").strip()



            c.nav_order = int(request.form.get("nav_order") or 0)



            c.active = bool(request.form.get("active"))



            db.session.commit()



            flash("Category updated.", "success")



            return redirect(url_for("admin_categories"))



    return render_template("admin/category_form.html", category=c)







@app.post("/admin/categories/toggle/<int:category_id>")



@login_required



def admin_category_toggle(category_id):



    c = Category.query.get_or_404(category_id)



    c.active = not c.active



    db.session.commit()



    return redirect(url_for("admin_categories"))







@app.post("/admin/categories/delete/<int:category_id>")



@login_required



def admin_category_delete(category_id):



    c = Category.query.get_or_404(category_id)



    db.session.delete(c); db.session.commit()



    flash("Category and its projects were deleted.", "success")



    return redirect(url_for("admin_categories"))







@app.route("/admin/projects")



@login_required



def admin_projects():



    category_id = request.args.get("category_id", type=int)



    q = Project.query.order_by(Project.id.desc())



    if category_id:



        q = q.filter_by(category_id=category_id)



    return render_template("admin/projects.html", projects=q.all(),



                           categories=Category.query.order_by(Category.nav_order.asc()).all(),



                           selected_category=category_id)







@app.route("/admin/projects/add", methods=["GET","POST"])



@login_required



def admin_project_add():



    categories = Category.query.order_by(Category.nav_order.asc()).all()



    if request.method == "POST":



        try:



            cat_id = int(request.form.get("category_id"))



            main = save_upload(request.files.get("main_image")) or request.form.get("main_image_url","").strip()



            gallery = [x for x in request.form.get("gallery_urls","").splitlines() if x.strip()]



            for f in request.files.getlist("gallery_images"):



                p = save_upload(f)



                if p: gallery.append(p)



            brochure_images = [x for x in request.form.get("brochure_urls","").splitlines() if x.strip()]



            for f in request.files.getlist("brochure_images"):



                x = save_upload(f)



                if x: brochure_images.append(x)



            flat_images = [x for x in request.form.get("flat_urls","").splitlines() if x.strip()]



            for f in request.files.getlist("flat_images"):



                x = save_upload(f)



                if x: flat_images.append(x)



            tags = [x.strip() for x in request.form.get("tags","").split(",") if x.strip()]



            p = Project(category_id=cat_id, name=request.form.get("name","").strip(),



                        builder=request.form.get("builder","").strip(),



                        features=request.form.get("features","").strip(),



                        price=request.form.get("price","").strip(),



                        location=request.form.get("location","").strip(),



                        description=request.form.get("description","").strip(),



                        amenities=request.form.get("amenities","").strip(),



                        faq=request.form.get("faq","").strip(),



                        brochure_url=request.form.get("brochure_url","").strip(),



                        video_url=request.form.get("video_url","").strip(),



                        main_image=main, gallery=json.dumps(gallery),



                        brochure_images=json.dumps(brochure_images), flat_images=json.dumps(flat_images),



                        tags=json.dumps(tags), active=bool(request.form.get("active")))



            db.session.add(p); db.session.commit()



            flash("Project added successfully.", "success")



            return redirect(url_for("admin_projects"))



        except Exception as e:



            db.session.rollback()



            flash(str(e), "error")



    return render_template("admin/project_form.html", project=None, categories=categories)







@app.route("/admin/projects/edit/<int:project_id>", methods=["GET","POST"])



@login_required



def admin_project_edit(project_id):



    p = Project.query.get_or_404(project_id)



    categories = Category.query.order_by(Category.nav_order.asc()).all()



    if request.method == "POST":



        try:



            p.category_id = int(request.form.get("category_id"))



            p.name = request.form.get("name","").strip()



            p.builder = request.form.get("builder","").strip()



            p.features = request.form.get("features","").strip()



            p.price = request.form.get("price","").strip()



            p.location = request.form.get("location","").strip()



            p.description = request.form.get("description","").strip()



            p.amenities = request.form.get("amenities","").strip()



            p.faq = request.form.get("faq","").strip()



            p.brochure_url = request.form.get("brochure_url","").strip()



            p.video_url = request.form.get("video_url","").strip()



            new_main = save_upload(request.files.get("main_image"))



            if new_main: p.main_image = new_main



            gallery = json_list(p.gallery)



            gallery.extend([x for x in request.form.get("gallery_urls","").splitlines() if x.strip()])



            for f in request.files.getlist("gallery_images"):



                x = save_upload(f)



                if x: gallery.append(x)



            p.gallery = json.dumps(list(dict.fromkeys(gallery)))



            brochure_images = json_list(p.brochure_images)



            brochure_images.extend([x for x in request.form.get("brochure_urls","").splitlines() if x.strip()])



            for f in request.files.getlist("brochure_images"):



                x = save_upload(f)



                if x: brochure_images.append(x)



            p.brochure_images = json.dumps(list(dict.fromkeys(brochure_images)))



            flat_images = json_list(p.flat_images)



            flat_images.extend([x for x in request.form.get("flat_urls","").splitlines() if x.strip()])



            for f in request.files.getlist("flat_images"):



                x = save_upload(f)



                if x: flat_images.append(x)



            p.flat_images = json.dumps(list(dict.fromkeys(flat_images)))



            p.tags = json.dumps([x.strip() for x in request.form.get("tags","").split(",") if x.strip()])



            p.active = bool(request.form.get("active"))



            db.session.commit()



            flash("Project updated successfully.", "success")



            return redirect(url_for("admin_projects"))



        except Exception as e:



            db.session.rollback()



            flash(str(e), "error")



    return render_template("admin/project_form.html", project=p, categories=categories)







@app.post("/admin/projects/toggle/<int:project_id>")



@login_required



def admin_project_toggle(project_id):



    p = Project.query.get_or_404(project_id)



    p.active = not p.active



    db.session.commit()



    return redirect(url_for("admin_projects"))







@app.post("/admin/projects/delete/<int:project_id>")



@login_required



def admin_project_delete(project_id):



    p = Project.query.get_or_404(project_id)



    db.session.delete(p); db.session.commit()



    flash("Project deleted.", "success")



    return redirect(url_for("admin_projects"))







@app.route("/admin/change-password", methods=["GET","POST"])



@login_required



def change_password():



    user = AdminUser.query.get(session["admin_id"])



    if request.method == "POST":



        new = request.form.get("new_password","")



        confirm = request.form.get("confirm_password","")



        if len(new) < 8:



            flash("Password must be at least 8 characters.", "error")



        elif new != confirm:



            flash("Passwords do not match.", "error")



        else:



            user.password_hash = generate_password_hash(new)



            db.session.commit()



            flash("Password changed.", "success")



            return redirect(url_for("admin_dashboard"))



    return render_template("admin/change_password.html")







# Serve the original site's legacy pages/CSS/JS so the supplied site remains intact.



@app.route("/images/<path:filename>")



def legacy_images(filename):



    return send_from_directory(os.path.join(LEGACY_DIR, "images"), filename)







@app.route("/<path:filename>")



def legacy_files(filename):



    # Dynamic routes are defined above; this catches original HTML/CSS/JS/PDF/video files.



    full = os.path.join(LEGACY_DIR, filename)



    if os.path.isfile(full):



        return send_from_directory(LEGACY_DIR, filename)



    abort(404)







def bootstrap():



    with app.app_context():



        db.create_all()



        ensure_project_columns()



        if not AdminUser.query.first():



            username = os.environ.get("ADMIN_USERNAME", "admin")



            password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")



            db.session.add(AdminUser(username=username, password_hash=generate_password_hash(password)))



            db.session.commit()



        seed_from_legacy()



        backfill_legacy_details()







bootstrap()







if __name__ == "__main__":



    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
