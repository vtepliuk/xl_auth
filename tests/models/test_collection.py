# -*- coding: utf-8 -*-
"""Unit tests for Collection model."""

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

import pytest
from flask_babel import gettext as _
from six import string_types

from xl_auth.collection.models import Collection
from xl_auth.permission.models import Permission
from xl_auth.user.models import User

from ..factories import CollectionFactory, SuperUserFactory


@pytest.mark.usefixtures('db')
def test_get_by_id():
    """Get collection by ID."""
    collection = Collection(code='SKB', friendly_name='Literature by Strindberg',
                            category='bibliography')
    collection.save()

    retrieved = Collection.get_by_id(collection.id)
    assert retrieved == collection


def test_created_by_and_modified_by_is_updated(superuser):
    """Test created/modified by."""
    collection = Collection('KBX', 'Secret books', 'library')
    collection.save_as(superuser)
    assert collection.created_by_id == superuser.id
    assert collection.created_by == superuser
    assert collection.modified_by_id == superuser.id
    assert collection.modified_by == superuser

    # Another superuser updates something in the collection.
    another_superuser = SuperUserFactory()
    collection.update_as(another_superuser, commit=True, is_active=not collection.is_active)
    assert collection.created_by == superuser
    assert collection.modified_by == another_superuser


@pytest.mark.usefixtures('db')
def test_created_at_defaults_to_datetime():
    """Test creation date."""
    collection = Collection('KBX', 'Secret books', 'library')
    collection.save()
    assert bool(collection.created_at)
    assert isinstance(collection.created_at, datetime)


@pytest.mark.usefixtures('db')
def test_modified_at_defaults_to_current_datetime():
    """Test modified date."""
    collection = Collection('KBU', 'Outdated name', 'library')
    collection.save()
    first_modified_at = collection.modified_at

    assert abs((first_modified_at - collection.created_at).total_seconds()) < 10

    collection.friendly_name = 'Not outdated name!'
    collection.save()

    assert first_modified_at != collection.modified_at


def test_factory(db):
    """Test collection factory."""
    collection = CollectionFactory()
    db.session.commit()
    assert isinstance(collection.code, string_types)
    assert isinstance(collection.friendly_name, string_types)
    assert collection.category in {'bibliography', 'library', 'uncategorized'}
    assert collection.is_active is True
    assert isinstance(collection.permissions, list)
    assert collection.replaces is None
    assert collection.replaced_by is None

    assert isinstance(collection.modified_at, datetime)
    assert isinstance(collection.modified_by, User)
    assert isinstance(collection.created_at, datetime)
    assert isinstance(collection.created_by, User)


def test_adding_permissions(user):
    """Add a permission on the collection."""
    collection = CollectionFactory()
    collection.save()
    permission = Permission(user=user, collection=collection)
    permission.save()

    assert permission in collection.permissions


def test_removing_permissions(user):
    """Remove the permissions an a collection."""
    collection = CollectionFactory()
    collection.save()
    permission = Permission(user=user, collection=collection)
    permission.save()
    permission.delete()

    assert permission not in collection.permissions


@pytest.mark.usefixtures('db')
def test_get_replaces_and_replaced_by_str():
    """Check get_replaces_and_replaced_by_str output."""
    collection = CollectionFactory(replaces='A', replaced_by='B')
    assert collection.get_replaces_and_replaced_by_str() == \
        _('Replaces %(replaces_code)s, then replaced by %(replaced_by_code)s',
          replaces_code='A', replaced_by_code='B')
    collection = CollectionFactory(replaces='A')
    assert collection.get_replaces_and_replaced_by_str() == _('Replaces %(replaces_code)s',
                                                              replaces_code='A')
    collection = CollectionFactory(replaced_by='X')
    assert collection.get_replaces_and_replaced_by_str() == _('Replaced by %(replaced_by_code)s',
                                                              replaced_by_code='X')


@pytest.mark.usefixtures('db')
def test_repr():
    """Check repr output."""
    collection = CollectionFactory(code='KBZ')
    assert repr(collection) == '<Collection({!r})>'.format('KBZ')
