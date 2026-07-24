from flask import Blueprint, render_template

bp = Blueprint("plugins", __name__)

@bp.route("/plugins")
def plugins():
    return render_template("plugins.html")
