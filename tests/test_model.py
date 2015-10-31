from unittest import TestCase
from prepare import AppInitialized

from model.default import BaseUser
import model.sample
from model.property import (ActiveProperty, UnsupportedProperty,
                            no_capabilities, Capabilities)


class TestBaseUserCase(TestCase):
    def test_BaseUser_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseUser('')

    def test_BaseUser_has_flask_login_properties(self):
        assert BaseUser.is_authenticated
        assert BaseUser.is_active
        assert not BaseUser.is_anonymous

    # more can't be done here, we need some instances.


class TestSampleUserCase(AppInitialized):
    expected_result = {
        # 'attr_name': ('key_in_sample_dict', Capabilities())
        'realname': ('name', no_capabilities),
        'login': ('uid', no_capabilities),
        'mac': ('mac', Capabilities(edit=True, delete=False)),
        'mail': ('mail', Capabilities(edit=True, delete=True)),
        'address': ('address', no_capabilities),
        'ips': ('ip', no_capabilities),
        'status': ('status', no_capabilities),
        'id': ('id', no_capabilities),
        'hostname': ('hostname', no_capabilities),
        'hostalias': ('hostalias', no_capabilities),
    }

    rows = expected_result.keys()

    def setUp(self):
        self.User = model.sample.datasource.user_class
        self.user = self.User('test')
        self.sample_users = self.app.extensions['sample_users']

    def test_uid_not_accepted(self):
        with self.assertRaises(KeyError):
            self.User(0)

    def test_uid_correct(self):
        self.assertEqual(self.user.uid, self.sample_users['test']['uid'])

    def test_row_getters(self):
        """Test if the basic properties have been implemented accordingly.
        """

        for key, val in self.expected_result.items():
            if val:
                self.assertEqual(
                    getattr(self.user, key),
                    ActiveProperty(
                        name=key,
                        value=self.sample_users['test'][val[0]],
                        capabilities=val[1],
                    ),
                )
            else:
                self.assertEqual(
                    getattr(self.user, key),
                    UnsupportedProperty(key),
                )

        self.assertEqual(self.user.userdb_status,
                         UnsupportedProperty('userdb_status'))

    def test_row_setters(self):
        for attr in self.rows:
            class_attr = getattr(self.user.__class__, attr)

            if class_attr.fset:
                value = "given_value"
                setattr(self.user, attr, value)
                self.assertEqual(getattr(self.user, attr).value, value)
            elif not getattr(self.user, attr).capabilities.edit:
                assert not class_attr.fset

    def test_row_deleters(self):
        for attr in self.rows:
            class_attr = getattr(self.user.__class__, attr)

            if class_attr.fdel:
                delattr(self.user, attr)
                assert not getattr(self.user, attr).raw_value
                assert getattr(self.user, attr).empty

            elif not getattr(self.user, attr).capabilities.delete:
                assert not class_attr.fdel

    def test_correct_password(self):
        user = self.User('test')
        # TODO: check authenticate
        user.re_authenticate(
            self.sample_users['test']['password']
        )

    def test_credit_valid(self):
        """check whether the credit is positive and below 63GiB.
        """
        assert 0 <= self.user.credit <= 1024 * 63

    def test_traffic_history(self):
        for day in self.user.traffic_history:
            assert 0 <= day['day'] <= 6
            assert 0 <= day['input']
            assert 0 <= day['output']
            self.assertEqual(day['throughput'], day['input'] + day['output'])
            assert 0 <= day['credit'] <= 1024 * 63