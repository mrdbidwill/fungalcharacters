from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Character, DisplayOption, Source, ValueOption

User = get_user_model()


class EditingRulesTests(TestCase):
    def setUp(self):
        self.importer = User.objects.create(username="mrdbid-import", is_active=False)
        self.admin = User.objects.create_superuser("will", password="pw-admin-123")
        self.alice = User.objects.create_user("alice", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", password="pw-bob-123")
        self.radio = DisplayOption.objects.create(name="radio", created_by=self.importer)
        self.imported = Character.objects.create(name="Taste", created_by=self.importer, display_option=self.radio)
        ValueOption.objects.create(character=self.imported, name="Mild", created_by=self.importer)

    def login(self, user):
        self.client.force_login(user)

    def post_character(self, **data):
        return self.client.post(reverse("characters:create"), {"name": "", **data})

    # --- accounts and access ---

    def test_anonymous_can_read_but_not_create(self):
        self.assertEqual(self.client.get(reverse("characters:list")).status_code, 200)
        self.assertEqual(self.client.get(self.imported.get_absolute_url()).status_code, 200)
        r = self.client.get(reverse("characters:create"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("characters:create"))

    def test_signup_logs_in_and_rejects_case_variant_username(self):
        r = self.client.post(reverse("characters:signup"), {
            "username": "carol", "password1": "a-long-pass-987", "password2": "a-long-pass-987"})
        self.assertRedirects(r, reverse("characters:list"))
        self.assertTrue(User.objects.filter(username="carol").exists())
        self.client.logout()
        r = self.client.post(reverse("characters:signup"), {
            "username": "ALICE", "password1": "a-long-pass-987", "password2": "a-long-pass-987"})
        self.assertContains(r, "That username is taken.")

    # --- create, history, reasons ---

    def test_create_records_creator_and_reason_in_history(self):
        self.login(self.alice)
        r = self.post_character(name="Stem Width", reason="Needed for boletes")
        c = Character.objects.get(name="Stem Width")
        self.assertRedirects(r, c.get_absolute_url())
        self.assertEqual(c.created_by, self.alice)
        h = c.history.get()
        self.assertEqual((h.history_user, h.history_change_reason, h.history_type), (self.alice, "Needed for boletes", "+"))

    def test_edit_history_shows_old_and_new_values(self):
        self.login(self.alice)
        self.post_character(name="Stem Width")
        c = Character.objects.get(name="Stem Width")
        self.client.post(reverse("characters:edit", args=[c.pk]), {"name": "Stem Width", "description": "Widest point", "reason": "clarify"})
        r = self.client.get(reverse("characters:history", args=["character", c.pk]))
        self.assertContains(r, "Widest point")
        self.assertContains(r, "clarify")

    # --- duplicates ---

    def test_exact_and_near_exact_duplicates_blocked(self):
        self.login(self.alice)
        for name in ["Taste", "taste", " TASTE ", "Ta-ste"]:
            r = self.post_character(name=name)
            self.assertContains(r, "Already exists", msg_prefix=name)
        self.assertEqual(Character.objects.filter(name_normalized="taste").count(), 1)

    def test_similar_name_needs_confirmation(self):
        Character.objects.create(name="Spore Color", created_by=self.importer)
        self.login(self.alice)
        r = self.post_character(name="Spore Colour")
        self.assertContains(r, "Similar names already exist")
        self.assertFalse(Character.objects.filter(name="Spore Colour").exists())
        r = self.post_character(name="Spore Colour", confirm_similar="on")
        self.assertTrue(Character.objects.filter(name="Spore Colour").exists())

    def test_existing_duplicate_can_be_edited_without_renaming(self):
        dup = Character.objects.create(name="taste", created_by=self.importer)
        self.login(self.admin)
        r = self.client.post(reverse("characters:edit", args=[dup.pk]), {"name": "taste", "description": "x"})
        self.assertRedirects(r, dup.get_absolute_url())

    def test_value_option_duplicate_blocked_within_character_only(self):
        self.login(self.alice)
        url = reverse("characters:option_create", args=[self.imported.pk])
        self.assertContains(self.client.post(url, {"name": "mild", "sort_order": 2}), "Already exists")
        other = Character.objects.create(name="Odor", created_by=self.alice)
        r = self.client.post(reverse("characters:option_create", args=[other.pk]), {"name": "Mild", "sort_order": 1})
        self.assertRedirects(r, other.get_absolute_url())

    # --- ownership ---

    def test_users_edit_only_their_own_work(self):
        self.login(self.alice)
        self.post_character(name="Stem Width")
        c = Character.objects.get(name="Stem Width")
        self.login(self.bob)
        self.assertEqual(self.client.get(reverse("characters:edit", args=[c.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("characters:edit", args=[self.imported.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("characters:delete", args=[c.pk])).status_code, 403)

    def test_others_can_add_options_and_creator_then_cannot_delete(self):
        self.login(self.alice)
        self.post_character(name="Stem Width")
        c = Character.objects.get(name="Stem Width")
        self.login(self.bob)
        self.client.post(reverse("characters:option_create", args=[c.pk]), {"name": "Thin", "sort_order": 1})
        opt = ValueOption.objects.get(character=c, name="Thin")
        self.assertEqual(opt.created_by, self.bob)
        self.login(self.alice)
        self.assertEqual(self.client.get(reverse("characters:option_edit", args=[opt.pk])).status_code, 403)
        r = self.client.post(reverse("characters:delete", args=[c.pk]))
        self.assertContains(r, "cannot be deleted")
        self.assertTrue(Character.objects.filter(pk=c.pk).exists())

    def test_creator_can_delete_own_unshared_character(self):
        self.login(self.alice)
        self.post_character(name="Stem Width")
        c = Character.objects.get(name="Stem Width")
        r = self.client.post(reverse("characters:delete", args=[c.pk]), {"reason": "mistake"})
        self.assertRedirects(r, reverse("characters:list"))
        self.assertFalse(Character.objects.filter(pk=c.pk).exists())
        deleted = c.history.order_by("-history_date").first()
        self.assertEqual((deleted.history_type, deleted.history_change_reason), ("-", "mistake"))
        self.assertEqual(self.client.get(reverse("characters:history", args=["character", c.pk])).status_code, 200)

    # --- admin ---

    def test_admin_can_edit_and_delete_imported_character_with_options(self):
        self.login(self.admin)
        r = self.client.post(reverse("characters:edit", args=[self.imported.pk]), {"name": "Taste", "description": "edited"})
        self.assertRedirects(r, self.imported.get_absolute_url())
        r = self.client.post(reverse("characters:delete", args=[self.imported.pk]), {"reason": "review"})
        self.assertRedirects(r, reverse("characters:list"))
        self.assertFalse(Character.objects.filter(pk=self.imported.pk).exists())
        self.assertFalse(ValueOption.objects.filter(name="Mild").exists())

    def test_value_type_in_use_cannot_be_deleted(self):
        self.login(self.admin)
        r = self.client.post(reverse("characters:value_type_delete", args=[self.radio.pk]))
        self.assertContains(r, "use this value type")
        self.assertTrue(DisplayOption.objects.filter(pk=self.radio.pk).exists())

    def test_source_create_and_duplicate_title(self):
        self.login(self.alice)
        r = self.client.post(reverse("characters:source_create"), {"title": "Mushrooms Demystified"})
        s = Source.objects.get(title="Mushrooms Demystified")
        self.assertRedirects(r, reverse("characters:source_detail", args=[s.pk]))
        r = self.client.post(reverse("characters:source_create"), {"title": "mushrooms demystified"})
        self.assertContains(r, "Already exists")

    # --- permanent IDs ---

    def test_ids_are_never_reused(self):
        self.login(self.alice)
        self.post_character(name="First")
        first = Character.objects.get(name="First").pk
        self.client.post(reverse("characters:delete", args=[first]))
        self.post_character(name="Second")
        self.assertGreater(Character.objects.get(name="Second").pk, first)

    def test_hidden_items_not_public(self):
        self.imported.is_hidden = True
        self.imported.save()
        self.assertEqual(self.client.get(self.imported.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("characters:history", args=["character", self.imported.pk])).status_code, 404)
        changes = self.client.get(reverse("characters:recent_changes"))
        self.assertNotContains(changes, "Taste")
        self.assertNotContains(changes, "Mild")  # value option of the hidden character
        opt = ValueOption.objects.get(name="Mild")
        self.assertEqual(self.client.get(reverse("characters:history", args=["option", opt.pk])).status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.client.get(self.imported.get_absolute_url()).status_code, 200)

    def test_public_pages_load(self):
        self.login(self.alice)
        for name in ["list", "value_type_list", "source_list", "recent_changes", "create", "value_type_create", "source_create"]:
            self.assertEqual(self.client.get(reverse(f"characters:{name}")).status_code, 200, name)
