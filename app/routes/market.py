from flask import Blueprint, render_template

bp = Blueprint("market", __name__)

@bp.route("/market")
def market():
    return render_template("market.html")
