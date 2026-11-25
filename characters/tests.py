"""Tests run against a database built by the migrations, which load release 1.0.0."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    CHARACTER_TYPE, Character, CharacterFungusType, CodeCounter, DisplayOption, ItemMeta, Label,
    Source, ValueOption,
)

User = get_user_model()


def label(c, label_type):
    return Label.objects.filter(labelable_type=CHARACTER_TYPE, labelable_id=c.pk, label_type=label_type,
                                language="en").values_list("text", flat=True).first()


class ReleaseDataTests(TestCase):
    def test_release_loaded_by_migration(self):
        self.assertEqual(Character.objects.count(), 747)
        self.assertEqual(ValueOption.objects.count(), 590)
        self.assertEqual(Label.objects.count(), 2681)
        self.assertEqual(CharacterFungusType.objects.count(), 194)
        self.assertEqual(CodeCounter.objects.get(prefix="FCC").last_number, 747)
        self.assertEqual(CodeCounter.objects.get(prefix="FCV").last_number, 590)

    def test_list_shows_all_characters(self):
        self.assertContains(self.client.get(reverse("characters:list")), "Showing 747 of 747 characters")

    def test_gill_attachment_has_16_value_options(self):
        r = self.client.get("/id/FCC00082")
        self.assertContains(r, "<h1>Gill Attachment</h1>", html=True)
        self.assertContains(r, "Value options (16)")

    def test_cap_width_scientific_name_and_credit(self):
        r = self.client.get("/id/FCC00019")
        self.assertContains(r, "Pileus Width")
        self.assertContains(r, "CC0 1.0")
        self.assertContains(r, "Please cite as: Fungal Characters, release 1.0.0, https://fungalcharacters.org/")

    def test_value_code_redirects_to_its_character(self):
        v = ValueOption.objects.get(code="FCV00001")
        self.assertRedirects(self.client.get("/id/FCV00001"), f"/id/{v.character.code}#FCV00001")

    def test_scientific_names_toggle(self):
        self.client.get(reverse("characters:set_name_mode", args=["scientific"]))
        self.assertContains(self.client.get("/id/FCC00019"), "<h1>Pileus Width</h1>", html=True)


class EditingRulesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("will", password="pw-admin-123")
        self.alice = User.objects.create_user("alice", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", password="pw-bob-123")
        self.cap_width = Character.objects.get(code="FCC00019")

    def login(self, user):
        self.client.force_login(user)

    def post_character(self, **data):
        return self.client.post(reverse("characters:create"), {"name": "", **data})

    def test_anonymous_can_read_but_not_create(self):
        r = self.client.get(reverse("characters:create"))
        self.assertRedirects(r, reverse("login") + "?next=" + reverse("characters:create"))

    def test_signup_rejects_case_variant_username(self):
        r = self.client.post(reverse("characters:signup"), {
            "username": "ALICE", "password1": "a-long-pass-987", "password2": "a-long-pass-987"})
        self.assertContains(r, "That username is taken.")

    def test_new_character_gets_next_code_labels_and_history(self):
        self.login(self.alice)
        r = self.post_character(name="Stem Zone Test", name_scientific="Stipes Zona Test",
                                description="A test.", unit="mm", reason="testing")
        c = Character.objects.get(name="Stem Zone Test")
        self.assertEqual(c.code, "FCC00748")
        self.assertRedirects(r, "/id/FCC00748")
        self.assertEqual(label(c, "name"), "Stem Zone Test")
        self.assertEqual(label(c, "scientific_name"), "Stipes Zona Test")
        self.assertEqual(label(c, "definition"), "A test.")
        self.assertEqual(c.props, {"name_scientific": "Stipes Zona Test", "unit": "mm"})
        self.assertEqual(ItemMeta.objects.get(item_type=CHARACTER_TYPE, item_id=c.pk).created_by, self.alice)
        h = c.history.get()
        self.assertEqual((h.history_user, h.history_change_reason), (self.alice, "testing"))

    def test_codes_never_reused(self):
        self.login(self.alice)
        self.post_character(name="First Test Character")
        first = Character.objects.get(name="First Test Character")
        self.client.post(reverse("characters:delete", args=[first.code]))
        self.assertEqual(self.client.get(f"/id/{first.code}").status_code, 410)  # retired
        self.post_character(name="Second Test Character")
        second = Character.objects.get(name="Second Test Character")
        self.assertGreater(second.code, first.code)

    def test_exact_and_near_exact_duplicates_blocked(self):
        self.login(self.alice)
        for name in ["Cap Width", "cap width", " CAP-WIDTH "]:
            self.assertContains(self.post_character(name=name), "Already exists", msg_prefix=name)

    def test_similar_name_needs_confirmation(self):
        self.login(self.alice)
        self.assertContains(self.post_character(name="Cap Widths"), "Similar names already exist")
        self.assertFalse(Character.objects.filter(name="Cap Widths").exists())
        self.post_character(name="Cap Widths", confirm_similar="on")
        self.assertTrue(Character.objects.filter(name="Cap Widths").exists())

    def test_release_items_editable_only_by_admin(self):
        self.login(self.alice)
        self.assertEqual(self.client.get(reverse("characters:edit", args=["FCC00019"])).status_code, 403)
        self.login(self.admin)
        r = self.client.post(reverse("characters:edit", args=["FCC00019"]), {
            "name": "Cap Width", "name_scientific": "Pileus Latitudo", "unit": "mm",
            "part": self.cap_width.part_id, "reason": "admin review"})
        self.assertRedirects(r, "/id/FCC00019")
        c = Character.objects.get(code="FCC00019")
        self.assertEqual(label(c, "scientific_name"), "Pileus Latitudo")
        self.assertEqual(c.props["name_scientific"], "Pileus Latitudo")
        self.assertEqual(c.props["xde_lines"], [13])  # other properties kept
        r = self.client.get(reverse("characters:history_by_code", args=["FCC00019"]))
        self.assertContains(r, "Pileus Width")
        self.assertContains(r, "Pileus Latitudo")
        self.assertContains(r, "admin review")

    def test_applies_to_tags_saved(self):
        self.login(self.alice)
        tagged = CharacterFungusType.objects.values_list("fungus_type_id", flat=True).first()
        self.post_character(name="Tag Test Character", applies_to=[tagged])
        c = Character.objects.get(name="Tag Test Character")
        self.assertEqual(list(c.applies_to.values_list("pk", flat=True)), [tagged])

    def test_others_add_values_then_creator_cannot_delete(self):
        self.login(self.alice)
        self.post_character(name="Shared Test Character")
        c = Character.objects.get(name="Shared Test Character")
        self.login(self.bob)
        self.client.post(reverse("characters:value_create", args=[c.code]), {"name": "Thin"})
        v = ValueOption.objects.get(character=c, name="Thin")
        self.assertEqual(v.code, "FCV00591")
        self.login(self.alice)
        self.assertEqual(self.client.get(reverse("characters:edit", args=[v.code])).status_code, 403)
        self.assertContains(self.client.post(reverse("characters:delete", args=[c.code])), "cannot be deleted")

    def test_admin_deletes_release_character_with_values_and_labels(self):
        c = Character.objects.get(code="FCC00082")
        value_ids = list(c.value_options.values_list("pk", flat=True))
        self.login(self.admin)
        r = self.client.post(reverse("characters:delete", args=["FCC00082"]), {"reason": "test"})
        self.assertRedirects(r, reverse("characters:list"))
        self.assertFalse(Character.objects.filter(code="FCC00082").exists())
        self.assertFalse(ValueOption.objects.filter(pk__in=value_ids).exists())
        self.assertFalse(Label.objects.filter(labelable_type=CHARACTER_TYPE, labelable_id=c.pk).exists())
        self.assertFalse(Label.objects.filter(labelable_type="LookupItem", labelable_id__in=value_ids).exists())

    def test_value_type_in_use_cannot_be_deleted(self):
        self.login(self.admin)
        vt = DisplayOption.objects.get(name="radio")
        self.assertContains(self.client.post(reverse("characters:value_type_delete", args=[vt.pk])), "use this value type")

    def test_source_duplicate_title_blocked(self):
        self.login(self.alice)
        title = Source.objects.exclude(title="").first().title
        self.assertContains(self.client.post(reverse("characters:source_create"), {"title": title.upper()}), "Already exists")

    def test_admin_hides_item(self):
        self.login(self.admin)
        self.client.post(reverse("characters:toggle_hidden", args=["character", self.cap_width.pk]))
        self.client.logout()
        self.assertEqual(self.client.get("/id/FCC00019").status_code, 404)
        self.assertNotContains(self.client.get(reverse("characters:list")), "FCC00019")
        self.login(self.alice)
        self.assertEqual(self.client.get("/id/FCC00019").status_code, 404)
        self.login(self.admin)
        self.assertEqual(self.client.get("/id/FCC00019").status_code, 200)

    def test_pages_load(self):
        self.login(self.alice)
        for name in ["list", "value_type_list", "source_list", "recent_changes", "create", "value_type_create", "source_create"]:
            self.assertEqual(self.client.get(reverse(f"characters:{name}")).status_code, 200, name)


class SitePagesTests(TestCase):
    def test_home_explains_site_and_links(self):
        r = self.client.get("/")
        self.assertContains(r, "publicly maintained")
        self.assertContains(r, "747 characters")
        self.assertContains(r, "Where people disagree")
        self.assertContains(r, "No advice about consumption")
        self.assertContains(r, 'href="/characters/"')

    def test_characters_list_moved_and_menu_marks_current_page(self):
        r = self.client.get("/characters/")
        self.assertContains(r, "Showing 747 of 747 characters")
        self.assertContains(r, '<a href="/characters/" aria-current="page">Characters</a>', html=True)

    def test_thanks_page(self):
        r = self.client.get("/thanks/")
        self.assertContains(r, "<h1>Thanks!</h1>", html=True)
        self.assertContains(r, "Gastón Guzmán (1932–2016)")

    def test_downloads_list_and_serve_release_files(self):
        r = self.client.get("/downloads/")
        self.assertContains(r, "Release 1.0.0")
        self.assertContains(r, "fungal_characters_v1.0.0.xlsx")
        self.assertContains(r, "csv/characters_flat.csv")
        f = self.client.get("/downloads/1.0.0/csv/characters_flat.csv")
        self.assertEqual(f.status_code, 200)
        self.assertIn("attachment", f["Content-Disposition"])
        self.assertIn(b"FCC00019", b"".join(f.streaming_content))

    def test_downloads_reject_other_paths(self):
        for bad in ["/downloads/1.0.0/../../../config/settings.py", "/downloads/1.0.0/nothing.txt", "/downloads/9.9.9/README.md"]:
            self.assertEqual(self.client.get(bad).status_code, 404, bad)

    def test_theme_assets_linked(self):
        r = self.client.get("/")
        for asset in ["site.css", "favicon.ico", "favicon.svg", "apple-touch-icon.png"]:
            self.assertContains(r, asset)
        self.assertContains(r, 'class="skip" href="#main"')
