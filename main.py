from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager
admin_manager = LoginManager(app)

# Creating a gravatar image and read more about gravatar image too
gravatar_img = Gravatar(app, size=100, rating='g', default="retro", force_default=False, force_lower=False,
                        use_ssl=False, base_url=None)


# CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    post = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = relationship("User", back_populates="post")
    blog_comments = relationship("Comment", back_populates="user_comments")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    # User and Comment Relationship
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comment_author = relationship("User", back_populates="comments")
    # Blog_post and Comment Relationship
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    user_comments = relationship("BlogPost", back_populates="blog_comments")
    text = db.Column(db.Text, nullable=False)


db.create_all()


# Admin Decorator Function Limited to admins only

def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403, "This page is not found at all")
        return func(*args, **kwargs)

    return decorated_function


# Configuring the login
@admin_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Showing all the blog post the Blogger has written
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


# Register a user in other to access the blog site
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("This email has been registered. Login with the email")
            return redirect(url_for("login"))

        name = form.name.data
        email = form.email.data
        password = form.password.data
        hash_func = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)

        register_user = User(
            email=email,
            password=hash_func,
            name=name
        )

        db.session.add(register_user)
        db.session.commit()

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


# Login the registered user to the blog site
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("This email does not exist. Please try again")
            return redirect(url_for("login"))

        elif check_password_hash(user.password, password) is True:
            login_user(user)
            return redirect(url_for("get_all_posts"))

        else:
            flash("Password incorrect. Please try again")

    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


# Logout the registered user from the blog site
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("get_all_posts"))


# Show the blog post only to the registered user
@app.route("/post/<int:index>", methods=["GET", "POST"])
def show_post(index):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(index)

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        text = comment_form.comment.data

        user_comment = Comment(
            text=text,
            comment_author=current_user,
            user_comments=requested_post
        )
        db.session.add(user_comment)
        db.session.commit()

        return redirect(url_for("show_post", index=index))

    # Once not logged in and click on the link redirect the user to the login page
    if not current_user.is_authenticated:
        redirect(url_for("login"))

    return render_template("post.html", post=requested_post, logged_in=True, form=comment_form,
                           current_user=current_user, num=index)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


# Only admin can access this function if you are not an admin you can't edit or delete a blog post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def make_post():
    forms = CreatePostForm()
    if forms.validate_on_submit():
        new_posts = BlogPost(
            title=forms.title.data,
            subtitle=forms.subtitle.data,
            date=datetime.now().strftime("%B %d, %Y"),
            body=forms.body.data,
            img_url=forms.img_url.data,
            author_id=current_user.id
        )

        db.session.add(new_posts)
        db.session.commit()

        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=forms, logged_in=True)


# Only admin can access this function if you are not an admin you can't edit or delete a blog post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", index=post_id))

    return render_template("make-post.html", form=edit_form, is_edit=True, logged_in=True)


# Only admin can access this function if you are not an admin you can't edit or delete a blog post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post = BlogPost.query.get(post_id)
    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("get_all_posts"))


if __name__ == "__main__":
    app.run(debug=True)
