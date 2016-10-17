from flask import Blueprint, render_template
from flask import current_app as app

mod_site = Blueprint('site', __name__)


@mod_site.route("/", methods=["GET"])
def home():
    return render_template("index.html", total=0, datasets=[], coreDatasets=[], title='home')
