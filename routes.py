from app import app
from flask import render_template, request, redirect, flash
import users
import visits
import os
import orders
import customers
import datetime
import events
import calculate
from datetime import date
from db import db
from flask import session


@app.route("/")
def index():
    counter = visits.get_counter()
    time = datetime.datetime.now()
    date = time.strftime("%d.%m.%Y")
    return render_template("index.html", counter=counter, time=time.strftime("%H:%M"), date=date)


@app.route("/login", methods=["get", "post"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if users.login(username, password):
            session["csrf_token"] = os.urandom(16).hex()
            return redirect("/")
        else:
            flash("Väärä tunnus tai salasana", "warning")
            return redirect(request.url)


@app.route("/logout")
def logout():
    users.logout()
    return redirect("/")


@app.route("/charts")
def charts():
    hard_worker_list = events.hard_workers()
    slowest = calculate.seek_slowest()
    if users.user_status() == 1:
        return render_template("charts.html", hard_worker_list=hard_worker_list, slowest=slowest)
    else:
        return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")


@app.route("/new_event", methods=["get", "post"])
def new_event():
    user_data = users.user()
    order_list = orders.listAll()
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            return render_template("new_event.html", user_data=user_data, order_list=order_list)
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        order_id = request.form["order_id"]
        description = request.form["description"]
        user_id = user_data[0]
        is_pending = request.form["is_pending"]
        in_progress = request.form["in_progress"]
        token = request.form["csrf_token"]
        if orders.order(order_id) != None and description != '' and events.add(order_id, user_id, description, is_pending) and session["csrf_token"] == token:
            if in_progress == '0':
                orders.check_out_in(order_id, in_progress)
                events.add(order_id, user_id, "Uloskirjaus", 0)
            flash("Työvaihe '"+description+ "' lisätty tilaukselle "+order_id, "success")
            return redirect(request.url)
        else:
            flash("Työvaiheen lisääminen epäonnistui", "warning")
            return redirect(request.url)


@app.route("/seek_by_user")
def seek_by_user():
    event_list = events.event_list()
    username = users.user()[1]
    user_id = users.user()[0]
    if users.user_status() == 1 or users.user_status() == 0:
        return render_template("seek_by_user.html", event_list=event_list, user_id=user_id, username=username)
    else:
        return render_template("error.html", message="Haku ei onnistunut")


@app.route("/seek/")
def seek():
    order_list = orders.listAll()
    event_list = events.event_list()
    order_id = request.args.get("order_id", "")
    if users.user_status() == 1 or users.user_status() == 0:
        return render_template("seek.html", event_list=event_list, orderit=order_list, order_id=order_id)
    else:
        return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")


@app.route("/register", methods=["get", "post"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password2 = request.form["password2"]
        if users.seek(username):
            flash("Käyttäjänimi on varattu", "warning")
        if password != password2:
            flash("Salasanat eivät täsmää", "warning")
        if password != password2 or users.seek(username):
            return redirect(request.url)
        if users.register(username, password):
            flash("Käyttäjätunnus '"+username+ "' luotu", "success")
            return redirect("/")
        else:
            flash("Rekisteröinti epäonnistui. Käyttäjätunnus '"+username+ "' on ehkä jo olemassa", "warning")
            return redirect(request.url)


@app.route("/admin", methods=["get"])
def admin():
    if request.method == "GET":
        if users.user_status() == 1:
            return render_template("admin.html")
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")


@app.route("/change_status", methods=["get", "post"])
def change_status():
    if request.method == "GET":
        if users.user_status() == 1:
            user_list = users.user_list()
            return render_template("change_status.html", user_list=user_list)
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        new_status = request.form["new_status"]
        username = request.form["username"]
        token = request.form["csrf_token"]
        if users.update_status(username, new_status) and session["csrf_token"] == token:
            flash("Käyttäjän '"+username+ "' oikeudet päivitetty", "success")
            return redirect(request.url)
        else:
            flash("Oikeuksien päivitys epäonnistui", "warning")
            return redirect(request.url)


@app.route("/new_order", methods=["get", "post"])
def new_order():
    order_type_list = orders.order_type_list()
    customer_list = customers.customer_list()
    clinic_list = customers.clinic_list()
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            return render_template('new_order.html', order_type_list=order_type_list, customer_list=customer_list, clinic_list=clinic_list)
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")

    if request.method == "POST":
        clinic_id = request.form["clinic_id"]
        order_type_id = request.form["order_type_id"]
        customer_id = request.form["customer_id"]
        d_date = request.form["delivery_date"]
        d_time = request.form["delivery_time"]
        delivery_date = d_date + ' ' + d_time + ':00.000000'
        token = request.form["csrf_token"]
        if clinic_id == '0' or order_type_id == '0' or customer_id == '0' or d_date == '':
            flash("Täytä kaikki kentät!", "warning")
            return redirect(request.url)
        elif clinic_id != '0' or order_type_id != '0' or customer_id != '0' and session["csrf_token"] == token:
            latest_id = orders.add(
                order_type_id, customer_id, delivery_date, clinic_id)
            if (latest_id != None):
                events.add(latest_id, users.user()[0], "Sisäänkirjaus", 0)
                flash("Tilaus lisätty! Tilauksen id on: "+str(latest_id)+ ". Kirjoita se lähetteeseen.", "success")
                return redirect(request.url)
        else:
            flash("Tilauksen lisääminen epäonnistui", "warning")
            return redirect(request.url)


@app.route("/new_order_type", methods=["get", "post"])
def new_order_type():
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            return render_template("new_order_type.html")
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        product = request.form["product"]
        materials = request.form["materials"]
        token = request.form["csrf_token"]
        if product != "" and materials != "" and orders.add_order_type(product, materials) and session["csrf_token"] == token:
            flash("Tuote lisätty listaan", "success")
            return redirect("/new_order")
        else:
            flash("Tuotteen lisääminen epäonnistui", "warning")
            return redirect(request.url)

@app.route("/new_clinic", methods=["get", "post"])
def new_clinic():
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            citys = customers.citys_fi()
            return render_template("new_clinic.html", citys=citys)
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        name = request.form["name"]
        adress = request.form["adress"]
        city = request.form["city"]
        postal = request.form["postal"]
        token = request.form["csrf_token"]
        if name != "" and adress != "" and postal != "" and customers.add_clinic(name, adress, postal, city) and session["csrf_token"] == token:
            flash("Toimipiste lisätty listaan", "success")
            return redirect("/new_order")
        else:
            flash("Toimipisteen lisääminen epäonnistui, tarkista onko toimipiste jo olemassa", "warning")
            return redirect(request.url)


@app.route("/new_customer", methods=["get", "post"])
def new_customer():
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            return render_template("new_customer.html")
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        name = request.form["name"]
        token = request.form["csrf_token"]
        if name != "" and customers.add(name) and session["csrf_token"] == token:
            flash("Asiakas lisätty listaan", "success")
            return redirect("/new_order")
        else:
            flash("Asiakkaan lisääminen epäonnistui, tarkista onko asiakas jo olemassa", "warning")
            return redirect(request.url)


today = date.today()


@app.route("/production", methods=["get", "post"])
def production():
    order_list = orders.list(today.strftime("%Y-%m-%d"))
    if request.method == "GET":
        if users.user_status() == 1 or users.user_status() == 0:
            return render_template("production.html", date=today, order_list=order_list, today=today)
        else:
            return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
    if request.method == "POST":
        datef = request.form["date"]
        if (datef == ""):
            return render_template("production.html", date=today, order_list=order_list, today=today)
        new_date = datetime.datetime.strptime(datef, '%Y-%m-%d').date()
        new_order_list = orders.list(datef)
        return render_template("production.html", date=new_date, order_list=new_order_list, today=today)
    else:
        return render_template("error.html", message="")


@app.errorhandler(404)
def error(e):
    return render_template("error.html")


@app.errorhandler(500)
def server_error(e):
    return redirect("/")


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", message="Käyttäjän oikeudet eivät riitä tähän toimintoon.")
