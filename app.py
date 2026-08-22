from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sqlite3
import io
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

app = Flask(__name__)
app.secret_key = "cyberescape_secret_key"

DATABASE = "cyberescape.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_progress(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT level_id, status, score, hints_used, attempts, completion_time FROM game_progress WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()

    progress = {}
    for row in rows:
        progress[row["level_id"]] = {
            "status": row["status"],
            "score": row["score"],
            "hints_used": row["hints_used"],
            "attempts": row["attempts"],
            "completion_time": row["completion_time"]
        }
    return progress


def get_default_level(status="locked"):
    return {
        "status": status,
        "score": 0,
        "hints_used": 0,
        "attempts": 0,
        "completion_time": 0
    }


def get_all_levels_for_user(user_id):
    progress = get_user_progress(user_id)

    level1 = progress.get(1, get_default_level("unlocked"))
    level2 = progress.get(2, get_default_level())
    level3 = progress.get(3, get_default_level())
    level4 = progress.get(4, get_default_level())
    level5 = progress.get(5, get_default_level())

    return [level1, level2, level3, level4, level5]


def calculate_xp_and_rank(levels):
    total_xp = 0

    for level in levels:
        score = level["score"] or 0
        hints = level["hints_used"] or 0
        completion_time = level["completion_time"] or 0
        status = level["status"]

        total_xp += score

        if status == "completed":
            total_xp += 200

        if status == "completed" and hints == 0:
            total_xp += 100

        if status == "completed" and completion_time > 0 and completion_time <= 60:
            total_xp += 150

    rank_levels = [
        {"name": "Beginner Defender", "min_xp": 0, "next_name": "Cyber Scout", "next_xp": 500},
        {"name": "Cyber Scout", "min_xp": 500, "next_name": "Security Trainee", "next_xp": 1200},
        {"name": "Security Trainee", "min_xp": 1200, "next_name": "Security Analyst", "next_xp": 2200},
        {"name": "Security Analyst", "min_xp": 2200, "next_name": "Cyber Guardian", "next_xp": 3500},
        {"name": "Cyber Guardian", "min_xp": 3500, "next_name": "CyberEscape Champion", "next_xp": 5000},
        {"name": "CyberEscape Champion", "min_xp": 5000, "next_name": "Max Rank", "next_xp": 5000}
    ]

    current_rank = rank_levels[0]

    for rank in rank_levels:
        if total_xp >= rank["min_xp"]:
            current_rank = rank

    rank = current_rank["name"]
    next_rank = current_rank["next_name"]
    next_rank_xp = current_rank["next_xp"]

    if next_rank == "Max Rank":
        rank_progress = 100
    else:
        current_min_xp = current_rank["min_xp"]
        xp_needed_for_rank = next_rank_xp - current_min_xp
        xp_earned_in_rank = total_xp - current_min_xp

        if xp_needed_for_rank <= 0:
            rank_progress = 100
        else:
            rank_progress = int((xp_earned_in_rank / xp_needed_for_rank) * 100)

        rank_progress = max(0, min(rank_progress, 100))

    return {
        "xp": total_xp,
        "rank": rank,
        "next_rank": next_rank,
        "next_rank_xp": next_rank_xp,
        "rank_progress": rank_progress
    }


def calculate_coins_earned(score, hints_used, completion_time):
    coins = 50
    coins += score // 20

    if hints_used == 0:
        coins += 25

    if completion_time > 0 and completion_time <= 60:
        coins += 20

    return coins


def get_user_coins(user_id):
    conn = get_db_connection()
    user = conn.execute("""
        SELECT coins FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()
    conn.close()

    if user and user["coins"] is not None:
        return user["coins"]

    return 0


def get_shop_items():
    return [
        {
            "key": "extra_password_hint",
            "name": "Extra Password Hint Token",
            "cost": 40,
            "icon": "fa-lightbulb",
            "level": "Level 1",
            "desc": "Gives an extra password security hint during Password Fortress."
        },
        {
            "key": "level1_time_boost",
            "name": "Time Boost +20s",
            "cost": 70,
            "icon": "fa-clock",
            "level": "Level 1",
            "desc": "Adds 20 extra seconds to Level 1 when activated."
        },
        {
            "key": "level1_mistake_shield",
            "name": "Mistake Shield",
            "cost": 90,
            "icon": "fa-shield-halved",
            "level": "Level 1",
            "desc": "Protects the player from one wrong password choice penalty."
        },
        {
            "key": "level2_extra_hint",
            "name": "Extra Phishing Hint",
            "cost": 60,
            "icon": "fa-lightbulb",
            "level": "Level 2",
            "desc": "Shows a phishing hint: payment requests in emails can be a phishing warning."
        },
        {
            "key": "level2_trust_restore",
            "name": "Trust Restore +15%",
            "cost": 100,
            "icon": "fa-heart-pulse",
            "level": "Level 2",
            "desc": "Restores 15% trust level during Phishing Pond."
        },
        {
            "key": "interception_shield",
            "name": "Interception Shield",
            "cost": 30,
            "icon": "fa-shield-halved",
            "level": "Level 4",
            "desc": "Protects the player from one interception spirit hit."
        },
        {
            "key": "neon_dashboard_theme",
            "name": "Neon Dashboard Theme",
            "cost": 90,
            "icon": "fa-palette",
            "level": "Full Game",
            "desc": "Unlocks a special neon dashboard style."
        },
        {
            "key": "champion_title_badge",
            "name": "Champion Title Badge",
            "cost": 300,
            "icon": "fa-crown",
            "level": "Full Game",
            "desc": "Unlocks a special Champion title badge for the player."
        }
    ]


def get_user_rewards(user_id):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT item_key, quantity
        FROM user_rewards
        WHERE user_id = ?
    """, (user_id,)).fetchall()
    conn.close()

    rewards = {}
    for row in rows:
        rewards[row["item_key"]] = row["quantity"]

    return rewards


def use_user_reward(user_id, item_key):
    conn = get_db_connection()
    row = conn.execute("""
        SELECT quantity
        FROM user_rewards
        WHERE user_id = ? AND item_key = ?
    """, (user_id, item_key)).fetchone()

    if not row or row["quantity"] <= 0:
        conn.close()
        return False

    conn.execute("""
        UPDATE user_rewards
        SET quantity = quantity - 1
        WHERE user_id = ? AND item_key = ?
    """, (user_id, item_key))

    conn.commit()
    conn.close()
    return True


def get_user_certificate_data(user_id):
    levels = get_all_levels_for_user(user_id)

    completed_count = sum(1 for p in levels if p["status"] == "completed")
    total_score = sum(p["score"] for p in levels)
    total_hints_used = sum(p["hints_used"] for p in levels)
    total_attempts = sum(p["attempts"] for p in levels)

    completed_times = [
        p["completion_time"]
        for p in levels
        if p["status"] == "completed" and p["completion_time"] > 0
    ]
    average_completion_time = int(sum(completed_times) / len(completed_times)) if completed_times else 0

    return {
        "levels": levels,
        "completed_count": completed_count,
        "total_score": total_score,
        "total_hints_used": total_hints_used,
        "total_attempts": total_attempts,
        "average_completion_time": average_completion_time
    }


def draw_centered_text(pdf, text, y, font_name="Helvetica", font_size=14, color=HexColor("#FFFFFF")):
    pdf.setFillColor(color)
    pdf.setFont(font_name, font_size)
    page_width = A4[0]
    text_width = pdf.stringWidth(text, font_name, font_size)
    x = (page_width - text_width) / 2
    pdf.drawString(x, y, text)


def generate_certificate_pdf(username, total_score, total_hints, total_attempts, avg_time, issued_date):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColor(HexColor("#031126"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setStrokeColor(HexColor("#00CFFF"))
    pdf.setLineWidth(2.5)
    pdf.roundRect(28, 28, width - 56, height - 56, 22, stroke=1, fill=0)

    pdf.setStrokeColor(HexColor("#1E4E72"))
    pdf.setLineWidth(1)
    pdf.roundRect(42, 42, width - 84, height - 84, 18, stroke=1, fill=0)

    icon_x = (width / 2) - 35
    icon_y = height - 125
    pdf.setFillColor(HexColor("#0A1B33"))
    pdf.setStrokeColor(HexColor("#FFD86B"))
    pdf.roundRect(icon_x, icon_y, 70, 70, 16, fill=1, stroke=1)

    pdf.setFillColor(HexColor("#FFD86B"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, icon_y + 24, "CE")

    draw_centered_text(pdf, "CYBERESCAPE CERTIFICATE OF ACHIEVEMENT", height - 155, "Helvetica-Bold", 17, HexColor("#FFD86B"))
    draw_centered_text(pdf, "Certificate of Completion", height - 220, "Helvetica-Bold", 32, HexColor("#FFFFFF"))
    draw_centered_text(pdf, "This certificate is proudly presented to", height - 265, "Helvetica", 16, HexColor("#D8F7FF"))
    draw_centered_text(pdf, username, height - 330, "Helvetica-Bold", 34, HexColor("#00CFFF"))

    draw_centered_text(pdf, "for successfully completing the full CyberEscape cybersecurity awareness journey", height - 390, "Helvetica", 14, HexColor("#D8F7FF"))
    draw_centered_text(pdf, "and finishing all 5 levels of interactive training.", height - 413, "Helvetica", 14, HexColor("#D8F7FF"))

    stats_y = height - 535
    box_w = 120
    box_h = 76
    gap = 16
    total_width = (4 * box_w) + (3 * gap)
    start_x = (width - total_width) / 2

    stats = [
        ("Total Score", str(total_score)),
        ("Hints Used", str(total_hints)),
        ("Total Attempts", str(total_attempts)),
        ("Average Time", f"{avg_time}s")
    ]

    for i, (label, value) in enumerate(stats):
        x = start_x + i * (box_w + gap)
        pdf.setFillColor(HexColor("#0A1B33"))
        pdf.setStrokeColor(HexColor("#00CFFF"))
        pdf.roundRect(x, stats_y, box_w, box_h, 12, fill=1, stroke=1)

        pdf.setFillColor(HexColor("#A8C7D8"))
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(x + box_w / 2, stats_y + 48, label)

        pdf.setFillColor(HexColor("#FFFFFF"))
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawCentredString(x + box_w / 2, stats_y + 20, value)

    pdf.setStrokeColor(HexColor("#1E4E72"))
    pdf.setLineWidth(1)
    pdf.line(70, 210, width - 70, 210)

    pdf.setFillColor(HexColor("#A8C7D8"))
    pdf.setFont("Helvetica", 13)
    pdf.drawString(85, 170, "Awarded for:")
    pdf.drawCentredString(width / 2, 170, "Date Issued:")
    pdf.drawRightString(width - 85, 170, "Status:")

    pdf.setFillColor(HexColor("#FFFFFF"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(85, 138, "Cybersecurity Awareness")
    pdf.drawString(85, 118, "Training")
    pdf.drawCentredString(width / 2, 128, issued_date)
    pdf.drawRightString(width - 85, 128, "Successfully")
    pdf.drawRightString(width - 85, 108, "Completed")

    pdf.save()
    buffer.seek(0)
    return buffer


def is_admin_user():
    return "username" in session and session["username"].lower() == "admin"


def is_level_unlocked(user_id, level_id):
    if level_id == 1:
        return True

    conn = get_db_connection()
    progress = conn.execute("""
        SELECT status FROM game_progress
        WHERE user_id = ? AND level_id = ?
    """, (user_id, level_id)).fetchone()
    conn.close()

    if not progress:
        return False

    return progress["status"] in ["unlocked", "completed"]


def save_progress_to_db(user_id, level_id, score, hints_used, completion_time, status="completed"):
    conn = get_db_connection()
    cursor = conn.cursor()

    existing = cursor.execute("""
        SELECT score, completion_time, status, coins_awarded
        FROM game_progress
        WHERE user_id = ? AND level_id = ?
    """, (user_id, level_id)).fetchone()

    coins_earned = 0

    if existing:
        old_score = existing["score"] or 0
        old_time = existing["completion_time"] or 0
        old_status = existing["status"]
        old_coins_awarded = existing["coins_awarded"] or 0

        best_score = max(old_score, score)

        if old_time > 0 and completion_time > 0:
            best_time = min(old_time, completion_time)
        elif completion_time > 0:
            best_time = completion_time
        else:
            best_time = old_time

        if status == "completed":
            if old_status != "completed":
                coins_earned = calculate_coins_earned(score, hints_used, completion_time)
            elif score > old_score:
                coins_earned = 30

        total_coins_awarded = old_coins_awarded + coins_earned

        cursor.execute("""
            UPDATE game_progress
            SET
                status = ?,
                score = ?,
                hints_used = ?,
                attempts = attempts + 1,
                completion_time = ?,
                coins_awarded = ?
            WHERE user_id = ? AND level_id = ?
        """, (
            status,
            best_score,
            hints_used,
            best_time,
            total_coins_awarded,
            user_id,
            level_id
        ))
    else:
        if status == "completed":
            coins_earned = calculate_coins_earned(score, hints_used, completion_time)

        cursor.execute("""
            INSERT INTO game_progress 
            (user_id, level_id, status, score, hints_used, attempts, completion_time, coins_awarded)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            user_id,
            level_id,
            status,
            score,
            hints_used,
            completion_time,
            coins_earned
        ))

    if coins_earned > 0:
        cursor.execute("""
            UPDATE users
            SET coins = COALESCE(coins, 0) + ?
            WHERE id = ?
        """, (coins_earned, user_id))

    if status == "completed" and level_id < 5:
        next_level_id = level_id + 1

        cursor.execute("""
            INSERT INTO game_progress
            (user_id, level_id, status, score, hints_used, attempts, completion_time, coins_awarded)
            VALUES (?, ?, 'unlocked', 0, 0, 0, 0, 0)
            ON CONFLICT(user_id, level_id)
            DO UPDATE SET
                status = CASE
                    WHEN game_progress.status = 'locked' THEN 'unlocked'
                    ELSE game_progress.status
                END
        """, (user_id, next_level_id))

    conn.commit()
    conn.close()

    return coins_earned


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not username or not email or not password or not confirm_password:
            error = "Please fill in all fields."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            conn = get_db_connection()
            existing_user = conn.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (username, email)
            ).fetchone()

            if existing_user:
                error = "Username or email already exists."
            else:
                hashed_password = generate_password_hash(password)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, coins) VALUES (?, ?, ?, 0)",
                    (username, email, hashed_password)
                )
                user_id = cursor.lastrowid

                conn.execute("""
                    INSERT OR IGNORE INTO game_progress
                    (user_id, level_id, status, score, hints_used, attempts, completion_time, coins_awarded)
                    VALUES (?, 1, 'unlocked', 0, 0, 0, 0, 0)
                """, (user_id,))

                conn.commit()
                conn.close()
                return redirect(url_for("login"))

            conn.close()

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if username.lower() == "admin":
            error = "Admin cannot log in from the player login page. Please use Admin Login."
            return render_template("login.html", error=error)

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if not user:
            error = "Admin account not found."
        elif user["username"].lower() != "admin":
            error = "This page is only for admin login."
        elif check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("admin"))
        else:
            error = "Invalid admin password."

    return render_template("admin_login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    coins = get_user_coins(user_id)
    user_rewards = get_user_rewards(user_id)
    progress = get_user_progress(user_id)

    level1 = progress.get(1, get_default_level("unlocked"))
    level2 = progress.get(2, get_default_level())
    level3 = progress.get(3, get_default_level())
    level4 = progress.get(4, get_default_level())
    level5 = progress.get(5, get_default_level())

    levels = [level1, level2, level3, level4, level5]

    completed_count = sum(1 for p in levels if p["status"] == "completed")
    progress_percent = int((completed_count / 5) * 100)
    total_score = sum(p["score"] for p in levels)
    total_hints_used = sum(p["hints_used"] for p in levels)
    total_attempts = sum(p["attempts"] for p in levels)

    completed_times = [
        p["completion_time"]
        for p in levels
        if p["status"] == "completed" and p["completion_time"] > 0
    ]
    average_completion_time = int(sum(completed_times) / len(completed_times)) if completed_times else 0

    all_completed = completed_count == 5
    xp_data = calculate_xp_and_rank(levels)

    badges = []
    if level1["status"] == "completed":
        badges.append({"name": "Password Protector", "icon": "fa-lock", "desc": "Completed Level 1"})
    if level2["status"] == "completed":
        badges.append({"name": "Phishing Detective", "icon": "fa-envelope-open-text", "desc": "Completed Level 2"})
    if level3["status"] == "completed":
        badges.append({"name": "Malware Hunter", "icon": "fa-bug", "desc": "Completed Level 3"})
    if level4["status"] == "completed":
        badges.append({"name": "Cipher Solver", "icon": "fa-key", "desc": "Completed Level 4"})
    if level5["status"] == "completed":
        badges.append({"name": "Firewall Commander", "icon": "fa-shield-halved", "desc": "Completed Level 5"})
    if all_completed:
        badges.append({"name": "CyberEscape Champion", "icon": "fa-trophy", "desc": "Completed all 5 levels"})

    return render_template(
        "dashboard.html",
        username=session["username"],
        is_admin=is_admin_user(),
        coins=coins,
        user_rewards=user_rewards,
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        level5=level5,
        completed_count=completed_count,
        progress_percent=progress_percent,
        total_score=total_score,
        total_hints_used=total_hints_used,
        total_attempts=total_attempts,
        average_completion_time=average_completion_time,
        all_completed=all_completed,
        badges=badges,
        xp=xp_data["xp"],
        player_rank=xp_data["rank"],
        next_rank=xp_data["next_rank"],
        next_rank_xp=xp_data["next_rank_xp"],
        rank_progress=xp_data["rank_progress"]
    )


@app.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("leaderboard.html")


@app.route("/api/leaderboard")
def api_leaderboard():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT 
            u.id,
            u.username,
            COALESCE(SUM(gp.score), 0) AS total_score,
            COALESCE(SUM(gp.hints_used), 0) AS total_hints,
            COALESCE(SUM(gp.attempts), 0) AS total_attempts,
            COALESCE(SUM(gp.completion_time), 0) AS total_time,
            COUNT(CASE WHEN gp.status = 'completed' THEN 1 END) AS completed_levels
        FROM users u
        LEFT JOIN game_progress gp ON u.id = gp.user_id
        WHERE LOWER(u.username) != 'admin'
        GROUP BY u.id, u.username
        ORDER BY 
            total_score DESC,
            completed_levels DESC,
            total_hints ASC,
            total_time ASC,
            total_attempts ASC
        LIMIT 20
    """).fetchall()

    conn.close()

    leaderboard_data = []

    for index, row in enumerate(rows, start=1):
        leaderboard_data.append({
            "rank": index,
            "username": row["username"],
            "total_score": row["total_score"],
            "completed_levels": row["completed_levels"],
            "total_hints": row["total_hints"],
            "total_attempts": row["total_attempts"],
            "total_time": row["total_time"]
        })

    return jsonify({
        "success": True,
        "leaderboard": leaderboard_data
    })


@app.route("/certificate")
def certificate():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    data = get_user_certificate_data(user_id)

    if data["completed_count"] < 5:
        return redirect(url_for("dashboard"))

    issued_date = datetime.now().strftime("%d %B %Y")

    return render_template(
        "certificate.html",
        username=session["username"],
        total_score=data["total_score"],
        total_hints=data["total_hints_used"],
        total_attempts=data["total_attempts"],
        avg_time=data["average_completion_time"],
        completed_count=data["completed_count"],
        issued_date=issued_date
    )


@app.route("/download_certificate")
def download_certificate():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    data = get_user_certificate_data(user_id)

    if data["completed_count"] < 5:
        return redirect(url_for("dashboard"))

    issued_date = datetime.now().strftime("%d %B %Y")

    pdf_buffer = generate_certificate_pdf(
        username=session["username"],
        total_score=data["total_score"],
        total_hints=data["total_hints_used"],
        total_attempts=data["total_attempts"],
        avg_time=data["average_completion_time"],
        issued_date=issued_date
    )

    safe_username = session["username"].replace(" ", "_")
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"CyberEscape_Certificate_{safe_username}.pdf",
        mimetype="application/pdf"
    )


@app.route("/level1")
def level1():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("level1.html")


@app.route("/level2")
def level2():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if not is_level_unlocked(user_id, 2):
        return redirect(url_for("dashboard"))

    return render_template("level2.html")


@app.route("/level3")
def level3():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if not is_level_unlocked(user_id, 3):
        return redirect(url_for("dashboard"))

    return render_template("level3.html")


@app.route("/level4")
def level4():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if not is_level_unlocked(user_id, 4):
        return redirect(url_for("dashboard"))

    return render_template("level4.html")


@app.route("/level5")
def level5():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if not is_level_unlocked(user_id, 5):
        return redirect(url_for("dashboard"))

    return render_template("level5.html")


@app.route("/save_level_progress", methods=["POST"])
def save_level_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()

    user_id = session["user_id"]
    level_id = int(data.get("level_id"))
    score = int(data.get("score", 0))
    hints_used = int(data.get("hints_used", 0))
    completion_time = int(data.get("completion_time", 0))
    status = data.get("status", "completed")

    coins_earned = save_progress_to_db(
        user_id=user_id,
        level_id=level_id,
        score=score,
        hints_used=hints_used,
        completion_time=completion_time,
        status=status
    )

    return jsonify({
        "success": True,
        "coins_earned": coins_earned
    })


@app.route("/save_level1_progress", methods=["POST"])
def save_level1_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()

    coins_earned = save_progress_to_db(
        user_id=session["user_id"],
        level_id=1,
        score=int(data.get("score", 0)),
        hints_used=int(data.get("hints_used", 0)),
        completion_time=int(data.get("completion_time", 0)),
        status="completed"
    )

    return jsonify({
        "success": True,
        "coins_earned": coins_earned
    })


@app.route("/save_level3_progress", methods=["POST"])
def save_level3_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()

    coins_earned = save_progress_to_db(
        user_id=session["user_id"],
        level_id=3,
        score=int(data.get("score", 0)),
        hints_used=int(data.get("hints_used", 0)),
        completion_time=int(data.get("completion_time", 0)),
        status="completed"
    )

    return jsonify({
        "success": True,
        "coins_earned": coins_earned
    })


@app.route("/save_level5_progress", methods=["POST"])
def save_level5_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()

    coins_earned = save_progress_to_db(
        user_id=session["user_id"],
        level_id=5,
        score=int(data.get("score", 0)),
        hints_used=int(data.get("hints_used", 0)),
        completion_time=int(data.get("completion_time", 0)),
        status="completed"
    )

    return jsonify({
        "success": True,
        "coins_earned": coins_earned
    })


@app.route("/reward_shop")
def reward_shop():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    coins = get_user_coins(user_id)
    items = get_shop_items()
    user_rewards = get_user_rewards(user_id)

    return render_template(
        "reward_shop.html",
        username=session["username"],
        coins=coins,
        items=items,
        user_rewards=user_rewards
    )


@app.route("/buy_reward", methods=["POST"])
def buy_reward():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()
    item_key = data.get("item_key")

    items = get_shop_items()
    selected_item = None

    for item in items:
        if item["key"] == item_key:
            selected_item = item
            break

    if not selected_item:
        return jsonify({"success": False, "message": "Invalid item."}), 400

    user_id = session["user_id"]
    cost = selected_item["cost"]

    conn = get_db_connection()
    user = conn.execute("""
        SELECT coins FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    current_coins = user["coins"] if user and user["coins"] is not None else 0

    if current_coins < cost:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Not enough Cyber Coins."
        })

    conn.execute("""
        UPDATE users
        SET coins = coins - ?
        WHERE id = ?
    """, (cost, user_id))

    conn.execute("""
        INSERT INTO user_rewards (user_id, item_key, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, item_key)
        DO UPDATE SET quantity = quantity + 1
    """, (user_id, item_key))

    conn.commit()

    new_balance = current_coins - cost

    conn.close()

    return jsonify({
        "success": True,
        "message": selected_item["name"] + " purchased successfully.",
        "new_balance": new_balance
    })


@app.route("/api/level_rewards/<int:level_id>")
def api_level_rewards(level_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    user_rewards = get_user_rewards(session["user_id"])

    if level_id == 1:
        allowed = [
            "extra_password_hint",
            "level1_time_boost",
            "level1_mistake_shield"
        ]
    elif level_id == 2:
        allowed = [
            "level2_extra_hint",
            "level2_trust_restore"
        ]
    elif level_id == 4:
        allowed = [
            "interception_shield"
        ]
    else:
        allowed = []

    filtered_rewards = {}
    for key in allowed:
        filtered_rewards[key] = user_rewards.get(key, 0)

    return jsonify({
        "success": True,
        "rewards": filtered_rewards
    })


@app.route("/use_reward", methods=["POST"])
def use_reward():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()
    item_key = data.get("item_key")

    if not item_key:
        return jsonify({"success": False, "message": "Missing reward item."}), 400

    success = use_user_reward(session["user_id"], item_key)

    if not success:
        return jsonify({
            "success": False,
            "message": "You do not own this reward."
        })

    user_rewards = get_user_rewards(session["user_id"])

    return jsonify({
        "success": True,
        "message": "Reward used successfully.",
        "remaining": user_rewards.get(item_key, 0)
    })


@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if not is_admin_user():
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    users = conn.execute("""
        SELECT id, username, email, password_hash, COALESCE(coins, 0) AS coins
        FROM users
        ORDER BY id ASC
    """).fetchall()

    progress_rows = conn.execute("""
        SELECT
            u.username,
            gp.level_id,
            gp.status,
            gp.score,
            gp.hints_used,
            gp.attempts,
            gp.completion_time
        FROM users u
        LEFT JOIN game_progress gp ON u.id = gp.user_id
        ORDER BY u.username, gp.level_id
    """).fetchall()

    conn.close()

    user_summary = {}
    level_completion = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_score_all = 0
    total_hints_all = 0
    total_attempts_all = 0
    total_completed_users = 0
    total_completion_times = []

    for row in progress_rows:
        username = row["username"]

        if username not in user_summary:
            user_summary[username] = {
                "completed_levels": 0,
                "total_score": 0,
                "total_hints": 0,
                "total_attempts": 0
            }

        if row["level_id"] is not None:
            score = row["score"] or 0
            hints = row["hints_used"] or 0
            attempts = row["attempts"] or 0
            completion_time = row["completion_time"] or 0

            user_summary[username]["total_score"] += score
            user_summary[username]["total_hints"] += hints
            user_summary[username]["total_attempts"] += attempts

            total_score_all += score
            total_hints_all += hints
            total_attempts_all += attempts

            if row["status"] == "completed":
                user_summary[username]["completed_levels"] += 1
                level_completion[row["level_id"]] += 1

                if completion_time > 0:
                    total_completion_times.append(completion_time)

    for summary in user_summary.values():
        if summary["completed_levels"] == 5:
            total_completed_users += 1

    avg_completion_time_all = int(sum(total_completion_times) / len(total_completion_times)) if total_completion_times else 0

    return render_template(
        "admin.html",
        username=session["username"],
        users=users,
        user_summary=user_summary,
        progress_rows=progress_rows,
        total_users=len(users),
        total_completed_users=total_completed_users,
        total_score_all=total_score_all,
        total_hints_all=total_hints_all,
        total_attempts_all=total_attempts_all,
        avg_completion_time_all=avg_completion_time_all,
        level_completion=level_completion
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)