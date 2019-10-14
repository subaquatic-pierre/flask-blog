from flask import Blueprint, redirect, url_for, flash, render_template, abort, request
from flask_login import current_user, login_user, logout_user, login_required
from flaskblog import db, bcrypt
from flaskblog.users.forms import RegistrationForm, LoginForm, UpdateAccountForm, ResetPasswordForm, RequestResetForm
from flaskblog.users.utils import save_picture, send_reset_email
from flaskblog.models import Post, User

users = Blueprint('users', __name__)


# Show the register form page or register a new user if POST method
@users.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    # Check if user is already logged in with current_user variable from flask login module downloaded
    if current_user.is_authenticated:
        return redirect('home') 

    # WTForms checks if request is POST
    if form.validate_on_submit():
        # Hash users password
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Create new instance of user with User class declared in models
        user = User(username=form.username.data, email=form.email.data, password=hashed_pw)

        # Add user to the database using SQLAlchemy
        db.session.add(user)
        db.session.commit()

        # Show user successful registration message
        flash(f'Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('users.login'))

    # If method is GET return register form template
    return render_template('register.html', title='Register', form=form)


# Show the login page or log the user into their account if POST request
@users.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in with current_user variable from flask login module downloaded
    if current_user.is_authenticated:
        return redirect('home')
    
    # Get data from login form
    form = LoginForm()

    if form.validate_on_submit():
        # Check if user is in database with SQLAlchmey function
        user = User.query.filter_by(email=form.email.data).first()

        # Check if user exits and check passwaord, use bcrypt to check password received from user in db and data passed in from the form
        if user and bcrypt.check_password_hash(user.password, form.password.data):

            # Get user login function from flask_login module downloaded
            login_user(user, remember=form.remember.data)

            # Get next page parameter from argument parameter from request module from flask
            next_page = request.args.get('next')
            
            # Use turnery operator to check if next_page exists in args from previous request and return to page
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            # Checked username and password failed which means email is correct but password is wrong
            flash('Login unsuccessful. Please check email and password', 'danger')

    # Render login form if request is GET 
    return render_template('login.html', title='Login', form=form)


# Log the user out of their acount
@users.route('/logout')
def logout():
    # Use logout function from flask_login module downloaded
    logout_user()
    return redirect('home')


# Account page route to view the account, any POST requests will update user profile data
@users.route('/account', methods=['GET', 'POST'])
@login_required # Imported from flask login module downloaded
def account():
    # Create instance on UpdateAccountForm imported from forms module
    form = UpdateAccountForm()

    # Check if POST route and form is valid
    if form.validate_on_submit():
        # Check if profile picture exists, use save_picture function created to pass in information and save file so file system, get new picture filename back
        if form.picture.data:

            # CREATE LOGIC TO REMOVE OLD PROFIILE PICTURE WHEN NEW ONE IS UPLOADED
            # ************************************

            picture_file = save_picture(form.picture.data) # Call save_picture function which returns new picture file name
            current_user.image_file = picture_file

        # Change current data to submitted data from form, using flask_login module, current_user class
        current_user.username = form.username.data
        current_user.email = form.email.data
        # Update db
        db.session.commit()
        # Send flash message to user successful update
        flash('Your account has been updated!', 'success')

        # POST,GET redirect pattern, seen on browser reload, Are your sure you want to reload, prevent POST request to account
        return redirect(url_for('users.account'))

    elif request.method == 'GET':        
        # Populate account update form with current user data if method is GET
        form.username.data = current_user.username
        form.email.data = current_user.email        

    # Get user profile pic from the db
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', 
                            image_file=image_file, form=form)


# Show posts from particular user
@users.route('/user/<string:username>') # Set variable as string with : before the variable arg in url
def user_posts(username):
    # Set page for SQLAlchemy pagination meythod from request.args
    page = request.args.get('page', 1, type=int) # Use int type to prevent anyone submitting anything other than integer

    # Get user from db using SQLAchemy
    user = User.query.filter_by(username=username).first_or_404() # Username comes from variable in route, similar to get version from post lookup, return 404 if user not found

    # Get posts from db using SQLAlchemy
    # First filter posts by user set from username query
    # Order by latest posts
    # use paginate method to get only few posts
    posts = Post.query.filter_by(author=user). \
    order_by(Post.date_posted.desc()) \
    .paginate(page=page, per_page=5) # user order_by to order the posts by newest post at the top

    return render_template('user_posts.html', posts=posts, user=user)


# Request reset password route
@users.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    # Make sure user is logged out to view this
    # Check if user is already logged in with current_user variable from flask login module downloaded
    if current_user.is_authenticated:
        return redirect('home')    

    # GET request, Initialize form to be filled on reset_token.html wich will be sent to user email on form submit
    form = RequestResetForm()    

    # If form was submitted with POST request and validated
    if form.validate_on_submit():
        # Get user data from form and check database for the user information
        user = User.query.filter_by(email=form.email.data).first()

        # Use function created above to send the user an email with the token url to reset their password
        send_reset_email(user)
        # Successful email sent with instructions
        flash('An email has been sent with instructions to reset your password', 'info')
        # Redirect back to login page
        return redirect(url_for('users.login'))
    

    # Get request show reset password token form
    return render_template('reset_request.html', title='Reset Password', form=form)


# Get request form url sent to user email with enrytped timed token sent to their email
@users.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    # Make sure user is logged out to view this
    # Check if user is already logged in with current_user variable from flask login module downloaded
    if current_user.is_authenticated:
        return redirect('home')

    # Use the method from the User class created in models
    # Method checks if the toekn is valid and returns user_id from db if valid
    user = User.verify_reset_token(token)

    # Invalid token message
    if not user:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))

    form = ResetPasswordForm()

    # WTForms checks if request is POST
    if form.validate_on_submit():
        # Hash users password from form data
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        # Update to new password to the database using SQLAlchemy
        user.password = hashed_pw
        db.session.commit()

        # Show user successful password change message
        flash(f'Your account has been updated! You are now able to log in.', 'success')
        return redirect(url_for('users.login'))
    
    return render_template('reset_token.html', title='Reset Password', form=form)
    