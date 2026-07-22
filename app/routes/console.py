from flask import Blueprint, render_template

bp = Blueprint("console", __name__)

@bp.route("/console")
def console():
    return render_template("console.html")
