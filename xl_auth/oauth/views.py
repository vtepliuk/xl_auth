# -*- coding: utf-8 -*-
"""OAuth2 views."""

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from ..client.models import Client
from ..extensions import oauth_provider
from ..grant.models import Grant
from ..token.models import Token
from ..user.models import User
from .forms import AuthorizeForm

blueprint = Blueprint('oauth', __name__, url_prefix='/oauth', static_folder='../static')


@oauth_provider.clientgetter
def get_client(client_id):
    """Return Client object."""
    return Client.get_by_id(client_id)


@oauth_provider.grantsetter
def set_grant(client_id, code, request_, **_):
    """Create Grant object."""
    expires_at = None
    return Grant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=request_.redirect_uri,
        scopes=request_.scopes,
        user_id=current_user.id,
        expires_at=expires_at
    ).save()


@oauth_provider.grantgetter
def get_grant(client_id, code):
    """Return Grant object."""
    return Grant.query.filter_by(client_id=client_id, code=code).first()


@oauth_provider.tokensetter
def set_token(new_token, request_, **_):
    """Create Token object."""
    old_tokens = Token.query.filter_by(client_id=request_.client.client_id,
                                       user_id=request_.user.id)
    # Make sure that every client has only one token connected to a user.
    for token in old_tokens:
        token.delete()

    expires_in = new_token.get('expires_in')
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    return Token(
        access_token=new_token['access_token'],
        refresh_token=new_token['refresh_token'],
        token_type=new_token['token_type'],
        scopes=new_token['scope'],
        expires_at=expires_at,
        client_id=request_.client.client_id,
        user_id=request_.user.id
    ).save()


@oauth_provider.tokengetter
def get_token(access_token=None, refresh_token=None):
    """Return Token object."""
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    if refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()
    return None


@oauth_provider.invalid_response
def require_oauth_invalid(req):
    """OAuth2 errors JSONified."""
    return jsonify(app_version=current_app.config['APP_VERSION'], message=req.error_message), 401


@blueprint.route('/authorize', methods=['GET', 'POST'])
@login_required
@oauth_provider.authorize_handler
def authorize(*_, **kwargs):
    """OAuth2'orize."""
    authorize_form = AuthorizeForm(request.form)
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        return render_template('oauth/authorize.html', authorize_form=authorize_form, **kwargs)

    confirm = authorize_form['confirm'].data
    return confirm


@blueprint.route('/token', methods=['POST', 'GET'])
@oauth_provider.token_handler
def create_access_token():
    """Generate access token."""
    return {'app_version': current_app.config['APP_VERSION']}


@blueprint.route('/verify', methods=['GET'])
@oauth_provider.require_oauth('read', 'write')
def verify():
    """Verify access token is valid and return a bunch of user details."""
    # noinspection PyUnresolvedReferences
    oauth = request.oauth
    assert isinstance(oauth.user, User)

    return jsonify(
        app_version=current_app.config['APP_VERSION'],
        expires_at=oauth.access_token.expires_at.isoformat() + 'Z',
        user={
            'full_name': oauth.user.full_name,
            'email': oauth.user.email,
            'permissions': [{'code': permission.collection.code,
                             'cataloger': permission.cataloger,
                             'registrant': permission.registrant}
                            for permission in oauth.user.permissions]
        }
    )


@blueprint.route('/revoke', methods=['POST'])
@login_required
@oauth_provider.revoke_handler
def revoke_token():
    """Revoke access token."""
    pass


@blueprint.route('/errors', methods=['GET'])
def errors():
    """Render OAuth2 errors."""
    return render_template('oauth/errors.html', **request.args)