from flask import Blueprint, render_template

bp = Blueprint("backup", __name__)

@bp.route("/backup")
def backup():
    return render_template("backup.html")
