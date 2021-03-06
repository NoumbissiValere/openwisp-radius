import swapper
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

from ..utils import (
    DEFAULT_SESSION_TIME_LIMIT,
    DEFAULT_SESSION_TRAFFIC_LIMIT,
    SESSION_TIME_ATTRIBUTE,
    SESSION_TRAFFIC_ATTRIBUTE,
    load_model,
)
from .mixins import BaseTestCase

Nas = load_model('Nas')
RadiusAccounting = load_model('RadiusAccounting')
RadiusCheck = load_model('RadiusCheck')
RadiusReply = load_model('RadiusReply')
RadiusPostAuth = load_model('RadiusPostAuth')
RadiusGroup = load_model('RadiusGroup')
RadiusGroupCheck = load_model('RadiusGroupCheck')
RadiusGroupReply = load_model('RadiusGroupReply')
RadiusUserGroup = load_model('RadiusUserGroup')
RadiusBatch = load_model('RadiusBatch')
Organization = swapper.load_model('openwisp_users', 'Organization')


class TestNas(BaseTestCase):
    def test_string_representation(self):
        nas = Nas(name='entry nasname')
        self.assertEqual(str(nas), nas.name)


class TestRadiusAccounting(BaseTestCase):
    def test_string_representation(self):
        radiusaccounting = RadiusAccounting(unique_id='entry acctuniqueid')
        self.assertEqual(str(radiusaccounting), radiusaccounting.unique_id)

    def test_ipv6_validator(self):
        radiusaccounting = RadiusAccounting(
            organization=self.default_org,
            unique_id='entry acctuniqueid',
            session_id='entry acctuniqueid',
            nas_ip_address='192.168.182.3',
            framed_ipv6_prefix='::/64',
        )
        radiusaccounting.full_clean()

        radiusaccounting.framed_ipv6_prefix = '192.168.0.0/28'
        self.assertRaises(ValidationError, radiusaccounting.full_clean)

        radiusaccounting.framed_ipv6_prefix = 'invalid ipv6_prefix'
        self.assertRaises(ValidationError, radiusaccounting.full_clean)


class TestRadiusCheck(BaseTestCase):
    def test_string_representation(self):
        radiuscheck = RadiusCheck(username='entry username')
        self.assertEqual(str(radiuscheck), radiuscheck.username)

    def test_auto_username(self):
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        c = self._create_radius_check(
            user=u, op=':=', attribute='Max-Daily-Session', value='3600'
        )
        self.assertEqual(c.username, u.username)

    def test_empty_username(self):
        opts = dict(op=':=', attribute='Max-Daily-Session', value='3600')
        try:
            self._create_radius_check(**opts)
        except ValidationError as e:
            self.assertIn('username', e.message_dict)
            self.assertIn('user', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_change_user_username(self):
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        c = self._create_radius_check(
            user=u, op=':=', attribute='Max-Daily-Session', value='3600'
        )
        u.username = 'changed'
        u.full_clean()
        u.save()
        c.refresh_from_db()
        # ensure related records have been updated
        self.assertEqual(c.username, u.username)

    def test_auto_value(self):
        obj = self._create_radius_check(
            username='Monica', value='Cam0_liX', attribute='NT-Password', op=':='
        )
        self.assertEqual(obj.value, '891fc570507eef023cbfec043dd5f2b1')

    def test_create_radius_check_model(self):
        obj = RadiusCheck.objects.create(
            organization=self.default_org,
            username='Monica',
            new_value='Cam0_liX',
            attribute='NT-Password',
            op=':=',
        )
        self.assertEqual(obj.value, '891fc570507eef023cbfec043dd5f2b1')


class TestRadiusReply(BaseTestCase):
    def test_string_representation(self):
        radiusreply = RadiusReply(username='entry username')
        self.assertEqual(str(radiusreply), radiusreply.username)

    def test_auto_username(self):
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        r = self._create_radius_reply(
            user=u, attribute='Reply-Message', op=':=', value='Login failed'
        )
        self.assertEqual(r.username, u.username)

    def test_empty_username(self):
        opts = dict(attribute='Reply-Message', op=':=', value='Login failed')
        try:
            self._create_radius_reply(**opts)
        except ValidationError as e:
            self.assertIn('username', e.message_dict)
            self.assertIn('user', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_change_user_username(self):
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        r = self._create_radius_reply(
            user=u, attribute='Reply-Message', op=':=', value='Login failed'
        )
        u.username = 'changed'
        u.full_clean()
        u.save()
        r.refresh_from_db()
        # ensure related records have been updated
        self.assertEqual(r.username, u.username)


class TestRadiusPostAuth(BaseTestCase):
    def test_string_representation(self):
        radiuspostauthentication = RadiusPostAuth(username='entry username')
        self.assertEqual(
            str(radiuspostauthentication), radiuspostauthentication.username
        )


class TestRadiusGroup(BaseTestCase):
    def test_group_str(self):
        g = RadiusGroup(name='entry groupname')
        self.assertEqual(str(g), g.name)

    def test_group_reply_str(self):
        r = RadiusGroupReply(groupname='entry groupname')
        self.assertEqual(str(r), r.groupname)

    def test_group_check_str(self):
        c = RadiusGroupCheck(groupname='entry groupname')
        self.assertEqual(str(c), c.groupname)

    def test_user_group_str(self):
        ug = RadiusUserGroup(username='entry username')
        self.assertEqual(str(ug), ug.username)

    def test_default_groups(self):
        default_org = Organization.objects.first()
        queryset = RadiusGroup.objects.filter(organization=default_org)
        self.assertEqual(queryset.count(), 2)
        self.assertEqual(queryset.filter(name='default-users').count(), 1)
        self.assertEqual(queryset.filter(name='default-power-users').count(), 1)
        self.assertEqual(queryset.filter(default=True).count(), 1)
        users = queryset.get(name='default-users')
        self.assertTrue(users.default)
        self.assertEqual(users.radiusgroupcheck_set.count(), 2)
        check = users.radiusgroupcheck_set.get(attribute=SESSION_TIME_ATTRIBUTE)
        self.assertEqual(check.value, DEFAULT_SESSION_TIME_LIMIT)
        check = users.radiusgroupcheck_set.get(attribute=SESSION_TRAFFIC_ATTRIBUTE)
        self.assertEqual(check.value, DEFAULT_SESSION_TRAFFIC_LIMIT)
        power_users = queryset.get(name='default-power-users')
        self.assertEqual(power_users.radiusgroupcheck_set.count(), 0)

    def test_change_default_group(self):
        org1 = self._create_org(name='org1', slug='org1')
        org2 = self._create_org(name='org2', slug='org2')
        new_default_org1 = RadiusGroup(
            name='org1-new', organization=org1, description='test', default=True
        )
        new_default_org1.full_clean()
        new_default_org1.save()
        new_default_org2 = RadiusGroup(
            name='org2-new', organization=org2, description='test', default=True
        )
        new_default_org2.full_clean()
        new_default_org2.save()
        queryset = RadiusGroup.objects.filter(default=True, organization=org1)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.filter(name='org1-new').count(), 1)
        # org2
        queryset = RadiusGroup.objects.filter(default=True, organization=org2)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.filter(name='org2-new').count(), 1)

    def test_delete_default_group(self):
        group = RadiusGroup.objects.get(default=1)
        try:
            group.delete()
        except ProtectedError:
            pass
        else:
            self.fail('ProtectedError not raised')

    def test_undefault_group(self):
        group = RadiusGroup.objects.get(default=True)
        group.default = False
        try:
            group.full_clean()
        except ValidationError as e:
            self.assertIn('default', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_no_default_failure_after_erasing(self):
        # this is a corner case but a very annoying one
        RadiusGroup.objects.all().delete()  # won't trigger ValidationError
        self._create_radius_group(name='test')

    def test_new_user_default_group(self):
        org = Organization.objects.get(slug='default')
        u = get_user_model()(username='test', email='test@test.org', password='test')
        u.full_clean()
        u.save()
        org.add_user(u)
        u.refresh_from_db()
        usergroup_set = u.radiususergroup_set.all()
        self.assertEqual(usergroup_set.count(), 1)
        ug = usergroup_set.first()
        self.assertTrue(ug.group.default)

    def test_groupcheck_auto_name(self):
        g = self._create_radius_group(name='test', description='test')
        c = self._create_radius_groupcheck(
            group=g, attribute='Max-Daily-Session', op=':=', value='3600'
        )
        self.assertEqual(c.groupname, g.name)

    def test_groupcheck_empty_groupname(self):
        opts = dict(attribute='Max-Daily-Session', op=':=', value='3600')
        try:
            self._create_radius_groupcheck(**opts)
        except ValidationError as e:
            self.assertIn('groupname', e.message_dict)
            self.assertIn('group', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_groupreply_auto_name(self):
        g = self._create_radius_group(name='test', description='test')
        r = self._create_radius_groupreply(
            group=g, attribute='Reply-Message', op=':=', value='Login failed'
        )
        self.assertEqual(r.groupname, g.name)

    def test_groupreply_empty_groupname(self):
        opts = dict(attribute='Reply-Message', op=':=', value='Login failed')
        try:
            self._create_radius_groupreply(**opts)
        except ValidationError as e:
            self.assertIn('groupname', e.message_dict)
            self.assertIn('group', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_usergroups_auto_fields(self):
        g = self._create_radius_group(name='test', description='test')
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        ug = self._create_radius_usergroup(user=u, group=g, priority=1)
        self.assertEqual(ug.groupname, g.name)
        self.assertEqual(ug.username, u.username)

    def test_usergroups_empty_groupname(self):
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        try:
            self._create_radius_usergroup(user=u, priority=1)
        except ValidationError as e:
            self.assertIn('groupname', e.message_dict)
            self.assertIn('group', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_usergroups_empty_username(self):
        g = self._create_radius_group(name='test', description='test')
        try:
            self._create_radius_usergroup(group=g, priority=1)
        except ValidationError as e:
            self.assertIn('username', e.message_dict)
            self.assertIn('user', e.message_dict)
        else:
            self.fail('ValidationError not raised')

    def test_change_group_auto_name(self):
        g = self._create_radius_group(name='test', description='test')
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        c = self._create_radius_groupcheck(
            group=g, attribute='Max-Daily-Session', op=':=', value='3600'
        )
        r = self._create_radius_groupreply(
            group=g, attribute='Reply-Message', op=':=', value='Login failed'
        )
        ug = self._create_radius_usergroup(user=u, group=g, priority=1)
        g.name = 'changed'
        g.full_clean()
        g.save()
        c.refresh_from_db()
        r.refresh_from_db()
        ug.refresh_from_db()
        # ensure related records have been updated
        self.assertEqual(c.groupname, g.name)
        self.assertEqual(r.groupname, g.name)
        self.assertEqual(ug.groupname, g.name)

    def test_change_user_username(self):
        g = self._create_radius_group(name='test', description='test')
        u = get_user_model().objects.create(
            username='test', email='test@test.org', password='test'
        )
        ug = self._create_radius_usergroup(user=u, group=g, priority=1)
        u.username = 'changed'
        u.full_clean()
        u.save()
        ug.refresh_from_db()
        # ensure related records have been updated
        self.assertEqual(ug.username, u.username)

    def test_delete(self):
        g = self._create_radius_group(name='test', description='test')
        g.delete()
        self.assertEqual(RadiusGroup.objects.all().count(), 2)

    def test_create_organization_default_group(self):
        new_org = self._create_org(name='new org', slug='new-org')
        queryset = RadiusGroup.objects.filter(organization=new_org)
        self.assertEqual(queryset.count(), 2)
        self.assertEqual(queryset.filter(name='new-org-users').count(), 1)
        self.assertEqual(queryset.filter(name='new-org-power-users').count(), 1)
        self.assertEqual(queryset.filter(default=True).count(), 1)
        group = queryset.filter(default=True).first()
        self.assertEqual(group.radiusgroupcheck_set.count(), 2)
        self.assertEqual(group.radiusgroupreply_set.count(), 0)

    def test_rename_organization(self):
        default_org = Organization.objects.first()
        default_org.name = 'renamed'
        default_org.slug = default_org.name
        default_org.full_clean()
        default_org.save()
        queryset = RadiusGroup.objects.filter(organization=default_org)
        self.assertEqual(queryset.count(), 2)
        self.assertEqual(queryset.filter(name='renamed-users').count(), 1)
        self.assertEqual(queryset.filter(name='renamed-power-users').count(), 1)

    def test_auto_prefix(self):
        org = self._create_org(name='Cool WiFi', slug='cool-wifi')
        rg = RadiusGroup(name='guests', organization=org)
        rg.full_clean()
        self.assertEqual(rg.name, '{}-guests'.format(org.slug))

    def test_org_none(self):
        rg = RadiusGroup(name='guests')
        try:
            rg.full_clean()
        except ValidationError as e:
            self.assertIn('organization', e.message_dict)
        except Exception as e:
            name = e.__class__.__name__
            self.fail(
                'ValidationError not raised, ' 'got "{}: {}" instead'.format(name, e)
            )
        else:
            self.fail('ValidationError not raised')


class TestRadiusBatch(BaseTestCase):
    def test_string_representation(self):
        radiusbatch = RadiusBatch(name='test')
        self.assertEqual(str(radiusbatch), 'test')

    def test_delete_method(self):
        radiusbatch = self._create_radius_batch(
            strategy='prefix', prefix='test-prefix16', name='test'
        )
        radiusbatch.prefix_add('test-prefix16', 5)
        User = get_user_model()
        self.assertEqual(User.objects.all().count(), 5)
        radiusbatch.delete()
        self.assertEqual(RadiusBatch.objects.all().count(), 0)
        self.assertEqual(User.objects.all().count(), 0)

    def test_clean_method(self):
        with self.assertRaises(ValidationError):
            self._create_radius_batch()
        # missing csvfile
        try:
            self._create_radius_batch(strategy='csv', name='test')
        except ValidationError as e:
            self.assertIn('csvfile', e.message_dict)
        else:
            self.fail('ValidationError not raised')
        # missing prefix
        try:
            self._create_radius_batch(strategy='prefix', name='test')
        except ValidationError as e:
            self.assertIn('prefix', e.message_dict)
        else:
            self.fail('ValidationError not raised')
        # mixing strategies
        try:
            self._create_radius_batch(
                strategy='prefix', prefix='prefix', csvfile='test', name='test'
            )
        except ValidationError as e:
            self.assertIn('Mixing', str(e))
        else:
            self.fail('ValidationError not raised')
