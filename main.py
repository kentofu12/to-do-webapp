from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import BadRequestKeyError
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegisterForm, LoginForm
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    username = db.Column(db.String(250), nullable=False)

    todos = relationship("ToDos", back_populates="user")


class ToDos(db.Model):
    __tablename__ = "todos"
    id = db.Column(db.Integer, primary_key=True)
    todo = db.Column(db.String(250), unique=True, nullable=False)
    due = db.Column(db.String(500), nullable=True)
    overdue = db.Column(db.Boolean, nullable=False)
    done = db.Column(db.Boolean, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = relationship("User", back_populates="todos")

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        print(current_user)
        if current_user.is_anonymous:
            flash("Please sign up or log in first.")
            return redirect(url_for("home"))
        else:
            try:
                new_todo = ToDos(todo=request.form["todo"],
                                 due=request.form["date"] + " " + request.form["time"],
                                 overdue=False,
                                 done=False,
                                 user=current_user
                                 )
            except BadRequestKeyError:
                new_todo = ToDos(todo=request.form["todo"],
                                 due=request.form["date"],
                                 overdue=False,
                                 done=False,
                                 user=current_user
                                 )

        db.session.add(new_todo)
        db.session.commit()

    date = datetime.datetime.now().date()
    time = datetime.datetime.now().time().strftime("%H:%M")

    todos = ToDos.query.all()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for todo in todos:
        due = ""
        if len(todo.due.split(" ")) == 1:
            due = todo.due + " " + "23:59:59"
        else:
            due = todo.due

        if due < now:
            todo_overdue = ToDos.query.get(todo.id)
            todo_overdue.overdue = 1
            db.session.commit()
        else:
            todo_not_due = ToDos.query.get(todo.id)
            todo_not_due.overdue = 0
            db.session.commit()

    todos = ToDos.query.filter_by(done=0).order_by(ToDos.due)
    todos_done = ToDos.query.filter_by(done=1).order_by(ToDos.due.desc())
    return render_template("index.html", date=date, time=time, todos=todos, todos_done=todos_done)


@app.route("/done/<int:todo_id>", methods=["GET", "POST"])
def get_todo_done(todo_id):
    todo_done = ToDos.query.get(todo_id)
    todo_done.done = 1
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit_todo(todo_id):
    todo = ToDos.query.get(todo_id)
    try:
        date = todo.due.split(" ")[0]
        time = todo.due.split(" ")[1]
    except IndexError:
        date = todo.due
        time = ""

    if request.method == "POST":
        todo.todo = request.form["todo"]
        try:
            todo.due = request.form["date"] + " " + request.form["time"]
        except BadRequestKeyError:
            todo.due = request.form["date"]
        todo.done = todo.done
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", todo=todo, date=date, time=time)


@app.route("/delete/<int:todo_id>", methods=["GET", "POST"])
def delete_todo(todo_id):
    todo_to_delete = ToDos.query.get(todo_id)
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/restore/<int:todo_id>", methods=["GET", "POST"])
def restore_todo(todo_id):
    todo_to_restore = ToDos.query.get(todo_id)
    todo_to_restore.done = 0
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(
            form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )

        user = User.query.filter_by(email=form.email.data).first()

        if user:
            flash("The email is already used. Please try again.")
            return redirect(url_for("sign_up"))

        else:
            new_user = User(email=form.email.data,
                            username=form.username.data,
                            password=hashed_password
                            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("home"))

    return render_template("sign_up.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Password incorrect. Please try again.")
                return redirect(url_for("login"))
        else:
            flash("The email does not exit. Please try again.")
            return redirect(url_for("login"))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)

