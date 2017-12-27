# -*- coding: utf-8 -*-
"""User views."""

from __future__ import absolute_import, division, print_function, unicode_literals

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_babel import lazy_gettext as _
from flask_login import current_user, login_required

from ..collection.models import Collection
from ..oauth.client.models import Client
from ..oauth.token.models import Token
from ..permission.models import Permission
from ..utils import flash_errors, get_redirect_target
from .forms import AdministerForm, ApproveToSForm, ChangePasswordForm, EditDetailsForm, RegisterForm
from .models import PasswordReset, User

blueprint = Blueprint('user', __name__, url_prefix='/users', static_folder='../static')


@blueprint.route('/')
@login_required
def home():
    """Users' overview landing page."""
    active_users = User.query.filter_by(is_active=True).order_by('email').all()
    inactive_users = User.query.filter_by(is_active=False).order_by('email').all()

    return render_template('users/home.html', active_users=active_users,
                           inactive_users=inactive_users)


@blueprint.route('/approve_tos', methods=['GET', 'POST'])
@login_required
def approve_tos():
    """Request approval of application ToS."""
    approve_tos_form = ApproveToSForm(current_user, request.form)
    if request.method == 'POST':
        if approve_tos_form.validate_on_submit():
            approve_tos_form.user.set_tos_approved()
            flash(_('ToS approved.'), 'success')
            return redirect(get_redirect_target())
        else:
            flash_errors(approve_tos_form)

    return render_template('users/approve_tos.html', approve_tos_form=approve_tos_form,
                           next_redirect_url=get_redirect_target())


@blueprint.route('/profile/')
@login_required
def profile():
    """Own user profile."""
    return render_template('users/profile.html', user=current_user)


@blueprint.route('/register/', methods=['GET', 'POST'])
@login_required
def register():
    """Register new user."""
    if not (current_user.is_admin or current_user.is_cataloging_admin):
        abort(403)

    register_user_form = RegisterForm(current_user, request.form)
    if request.method == 'POST':
        if register_user_form.validate_on_submit():
            user = User(email=register_user_form.username.data.lower().strip(),
                        full_name=register_user_form.full_name.data)
            if register_user_form.send_password_reset_email.data:
                password_reset = PasswordReset(user)
                password_reset.send_email()
                user.save_as(current_user)
                password_reset.save()
                flash(_('User "%(username)s" registered and emailed with a password reset link.',
                        username=user.email), 'success')
            else:
                user.save_as(current_user)
                flash(_('User "%(username)s" registered.', username=user.email), 'success')
            return redirect(get_redirect_target() or url_for('user.view', user_id=user.id))
        else:
            flash_errors(register_user_form)

    return render_template('users/register.html', register_user_form=register_user_form,
                           next_redirect_url=get_redirect_target())


@blueprint.route('/view/<int:user_id>', methods=['GET'])
@login_required
def view(user_id):
    """View user profile."""
    user = User.get_by_id(user_id)
    if not user:
        flash(_('User ID "%(user_id)s" does not exist', user_id=user_id), 'danger')
        return redirect(get_redirect_target())
    else:
        # Cataloging admins and admins need to see more information, so they get their own view.
        if current_user.is_admin or current_user.is_cataloging_admin:
            return render_template('users/view.html', user=user)
        else:
            return render_template('users/simple_view.html', user=user)


@blueprint.route('/inspect/<int:user_id>', methods=['GET'])
@login_required
def inspect(user_id):
    """Inspect user profile."""
    if not current_user.is_admin:
        abort(403)

    user = User.get_by_id(user_id)
    if not user:
        flash(_('User ID "%(user_id)s" does not exist', user_id=user_id), 'danger')
        return redirect(get_redirect_target())
    else:
        tokens = Token.query.filter_by(user=user).all()

        permissions_created = Permission.query.filter_by(created_by=user).count()
        permissions_modified = Permission.query.filter_by(modified_by=user).count()
        permissions_created_or_modified = Permission.query.filter(
            (Permission.created_by == user) | (Permission.modified_by == user)).all()

        collections_created = Collection.query.filter_by(created_by=user).count()
        collections_modified = Collection.query.filter_by(modified_by=user).count()

        users_created = User.query.filter_by(created_by=user).count()
        users_modified = User.query.filter_by(modified_by=user).count()
        users_created_or_modified = User.query.filter(
            ((User.created_by == user) | (User.modified_by == user)) & (User.id != user.id)
        ).order_by(User.email).all()

        clients_created = Client.query.filter_by(created_by=user).count()
        clients_modified = Client.query.filter_by(modified_by=user).count()

        return render_template('users/inspect.html',
                               user=user,
                               tokens=tokens,
                               permissions_created=permissions_created,
                               permissions_modified=permissions_modified,
                               permissions_created_or_modified=permissions_created_or_modified,
                               collections_created=collections_created,
                               collections_modified=collections_modified,
                               users_created=users_created,
                               users_modified=users_modified,
                               users_created_or_modified=users_created_or_modified,
                               clients_created=clients_created,
                               clients_modified=clients_modified)


@blueprint.route('/administer/<int:user_id>', methods=['GET', 'POST'])
@login_required
def administer(user_id):
    """Edit user details."""
    if not current_user.is_admin:
        abort(403)

    user = User.get_by_id(user_id)
    if not user:
        flash(_('User ID "%(user_id)s" does not exist', user_id=user_id), 'danger')
        return redirect(get_redirect_target())

    administer_form = AdministerForm(current_user, user.email, request.form)
    if administer_form.validate_on_submit():
        user.update_as(current_user,
                       full_name=administer_form.full_name.data,
                       is_active=administer_form.is_active.data,
                       is_admin=administer_form.is_admin.data).save()
        flash(_('Thank you for updating user details for "%(username)s".', username=user.email),
              'success')
        return redirect(get_redirect_target())
    else:
        administer_form.set_defaults(user)
        flash_errors(administer_form)
        return render_template('users/administer.html', administer_form=administer_form, user=user,
                               next_redirect_url=get_redirect_target())


@blueprint.route('/edit_details/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_details(user_id):
    """Edit user details."""
    if (current_user.id != user_id) and not current_user.is_admin:
        abort(403)

    user = User.get_by_id(user_id)
    if not user:
        flash(_('User ID "%(user_id)s" does not exist', user_id=user_id), 'danger')
        return redirect(get_redirect_target())

    edit_details_form = EditDetailsForm(current_user, user.email, request.form)
    if edit_details_form.validate_on_submit():
        user.update_as(current_user, full_name=edit_details_form.full_name.data).save()
        flash(_('Thank you for updating user details for "%(username)s".', username=user.email),
              'success')
        return redirect(get_redirect_target())
    else:
        edit_details_form.set_defaults(user)
        flash_errors(edit_details_form)
        return render_template('users/edit_details.html', edit_details_form=edit_details_form,
                               user=user, next_redirect_url=get_redirect_target())


@blueprint.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_password(user_id):
    """Change user password."""
    if (current_user.id != user_id) and not current_user.is_admin:
        abort(403)

    user = User.get_by_id(user_id)
    if not user:
        flash(_('User ID "%(user_id)s" does not exist', user_id=user_id), 'danger')
        return redirect(get_redirect_target())

    change_password_form = ChangePasswordForm(current_user, user.email, request.form)
    if change_password_form.validate_on_submit():
        user.set_password(change_password_form.password.data)
        user.save_as(current_user)
        flash(_('Thank you for changing password for "%(username)s".', username=user.email),
              'success')
        return redirect(get_redirect_target())
    else:
        flash_errors(change_password_form)
        return render_template(
            'users/change_password.html', change_password_form=change_password_form, user=user,
            next_redirect_url=get_redirect_target())
