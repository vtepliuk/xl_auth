# -*- coding: utf-8 -*-
"""Test user ChangePasswordForm."""

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
from flask_babel import gettext as _
from wtforms.validators import ValidationError

from xl_auth.user.forms import ChangePasswordForm


def test_change_password_form_validate_modifying_username(superuser):
    """Attempt to change password but passing in a new username/email."""
    form = ChangePasswordForm(superuser, superuser.email, username='new.address@kb.se',
                              password='123456', confirm='123456')

    assert form.validate() is False
    assert _('Email cannot be modified') in form.username.errors


def test_change_password_form_validate_success(superuser):
    """Change user password with success."""
    form = ChangePasswordForm(superuser, superuser.email, username=superuser.email,
                              password='example', confirm='example')

    assert form.validate() is True


def test_change_password_form_as_user_validate_success(user):
    """Change user password with success."""
    form = ChangePasswordForm(user, user.email, username=user.email,
                              password='example', confirm='example')

    assert form.validate() is True


def test_user_change_password_form_for_other_user(superuser, user):
    """Change password for another user as admin."""
    form = ChangePasswordForm(user, superuser.email, username=superuser.email,
                              password='example', confirm='example')

    with pytest.raises(ValidationError) as e_info:
        form.validate()
    assert e_info.value.args[0] == _('You do not have sufficient privileges for this operation.')


def test_superuser_change_password_form_for_other_user(superuser, user):
    """Attempt to change password for another user."""
    form = ChangePasswordForm(superuser, user.email, username=user.email,
                              password='example', confirm='example')

    assert form.validate() is True
