from flask import Blueprint, render_template

bp = Blueprint("commands", __name__)

@bp.route("/commands")
def commands():
    return render_template("commands.html")
