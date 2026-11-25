"""Tests run against a database built by the migrations, which load release 1.0.0."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    CHARACTER_TYPE, Character, CharacterFungusType, CodeCounter, DisplayOption, ItemMeta, Label,
    Source, ValueOption,
)

User = get_user_model()


def make_admin(username="will"):
    """A superuser with two-factor sign-in on (the site requires it for the admin)."""
    from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
    admin = User.objects.create_superuser(username, email=f"{username}@example.org", password="pw-admin-123")
    TOTP.activate(admin, generate_totp_secret())
    return admin


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
        self.admin = make_admin()
        self.alice = User.objects.create_user("alice", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", password="pw-bob-123")
        self.cap_width = Character.objects.get(code="FCC00019")

    def login(self, user):
        self.client.force_login(user)

    def post_character(self, **data):
        return self.client.post(reverse("characters:create"), {"name": "", **data})

    def test_anonymous_can_read_but_not_create(self):
        r = self.client.get(reverse("characters:create"))
        self.assertRedirects(r, reverse("account_login") + "?next=" + reverse("characters:create"))

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
        self.assertContains(r, '<strong class="thanks-name">Gastón Guzmán</strong> (1932–2016)')
        self.assertEqual(r.content.decode().count("<strong>nolo_mode</strong>"), 5)

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


class CoreOrderHistoryTests(TestCase):
    def test_removed_core_order_entry_appears_in_history(self):
        from .forms import ensure_history_baseline
        from .models import CoreSequence
        admin = make_admin()
        seq = CoreSequence.objects.filter(character__code="FCC00082").order_by("-sequence").first()
        ensure_history_baseline(seq)
        seq._history_user = admin
        seq._change_reason = "kept the lower number"
        n = seq.sequence
        seq.delete()
        r = self.client.get(reverse("characters:history_by_code", args=["FCC00082"]))
        self.assertContains(r, f"Boletes #{n} removed")
        self.assertContains(r, "kept the lower number")


class AccountTests(TestCase):
    """Sign-up with email verification, password reset by email, two-factor rules, account page."""

    def signup(self, username="carol", email="carol@example.org"):
        return self.client.post(reverse("account_signup"), {
            "username": username, "email": email,
            "password1": "a-long-pass-987", "password2": "a-long-pass-987"})

    def test_signup_requires_email_verification(self):
        from django.core import mail
        r = self.signup()
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(username="carol")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("carol@example.org", mail.outbox[0].to)
        self.assertTrue(mail.outbox[0].subject.startswith("[Fungal Characters]"))
        # Not signed in until the email is confirmed.
        self.assertFalse(self.client.get(reverse("characters:account")).wsgi_request.user.is_authenticated)
        import re
        link = re.search(r"https?://[^/]+(/accounts/confirm-email/[^\s]+)", mail.outbox[0].body).group(1)
        self.client.post(link)
        from allauth.account.models import EmailAddress
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        r = self.client.get(reverse("characters:account"))
        self.assertContains(r, "<h1>carol</h1>", html=True)

    def test_signup_rejects_case_variant_username_and_duplicate_email(self):
        User.objects.create_user("alice", email="alice@example.org", password="pw-alice-123")
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(user=User.objects.get(username="alice"), email="alice@example.org", verified=True, primary=True)
        r = self.signup(username="ALICE", email="other@example.org")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="ALICE").exists())

    def test_password_reset_sends_email(self):
        from django.core import mail
        from allauth.account.models import EmailAddress
        u = User.objects.create_user("dave", email="dave@example.org", password="pw-dave-12345")
        EmailAddress.objects.create(user=u, email="dave@example.org", verified=True, primary=True)
        self.client.post(reverse("account_reset_password"), {"email": "dave@example.org"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/password/reset/key/", mail.outbox[0].body)

    def test_admin_without_two_factor_is_sent_to_set_it_up(self):
        admin = User.objects.create_superuser("boss", email="boss@example.org", password="pw-admin-123")
        self.client.force_login(admin)
        self.assertRedirects(self.client.get("/characters/"), reverse("mfa_activate_totp"), fetch_redirect_response=False)
        # Setting it up first asks for the password again (allauth safeguard); no redirect loop.
        r = self.client.get(reverse("mfa_activate_totp"), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.wsgi_request.path.startswith("/accounts/"))

    def test_admin_with_two_factor_can_work(self):
        self.client.force_login(make_admin())
        self.assertEqual(self.client.get("/characters/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_admin_login_page_uses_site_sign_in(self):
        r = self.client.get("/admin/login/")
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("account_login"), r["Location"])

    def test_username_in_menu_links_to_account_page_listing_contributions(self):
        u = User.objects.create_user("erin", email="erin@example.org", password="pw-erin-12345")
        self.client.force_login(u)
        self.client.post(reverse("characters:create"), {"name": "Erin Test Character"})
        r = self.client.get("/")
        self.assertContains(r, '<a href="/account/" title="Your account"><strong>erin</strong></a>', html=True)
        r = self.client.get(reverse("characters:account"))
        self.assertContains(r, "Erin Test Character")
        self.assertContains(r, "Two-factor sign-in")
        for name in ["account_email", "account_change_password", "mfa_index", "usersessions_list"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class DisclaimerTests(TestCase):
    """Shared disclaimer (Claude_AI/shared_reference/disclaimer/): top and bottom of every page, and beside
    items about eating, using or handling fungi."""

    LEAD = "<strong>No advice about consumption.</strong>"

    def test_top_and_bottom_of_every_page(self):
        for url in ["/", "/characters/", "/id/FCC00019", "/thanks/", "/downloads/", "/sources/", "/value-types/",
                    "/changes/", "/accounts/login/", "/accounts/signup/", "/no-such-page/"]:
            r = self.client.get(url)
            body = r.content.decode()
            opening = '<main id="main" class="wrap">'
            main = body[body.index(opening) + len(opening):body.index('</main>')].strip()
            self.assertTrue(main.startswith('<p class="disclaimer">' + self.LEAD), url)          # first thing on the page
            last = main.rsplit('<p class="disclaimer">', 1)[1]
            self.assertTrue(last.startswith(self.LEAD) and last.rstrip().endswith('</p>') and last.count('<') == 3, url)  # last thing
            self.assertGreaterEqual(body.count('<p class="disclaimer">'), 2, url)

    def test_note_beside_chemistry_and_toxicity_items_only(self):
        chem = Character.objects.filter(observation_method__name="Field Chemical Test").first()
        self.assertContains(self.client.get(chem.get_absolute_url()), '<p class="disclaimer near">')
        self.assertNotContains(self.client.get("/id/FCC00019"), '<p class="disclaimer near">')  # Cap Width
        toxic = Character.objects.get(name="Toxic")
        self.assertContains(self.client.get(toxic.get_absolute_url()), '<p class="disclaimer near">')

    def test_note_beside_sources_about_eating_or_medicine(self):
        s = Source.objects.get(title__startswith="The Fungal Pharmacy")
        self.assertContains(self.client.get(reverse("characters:source_detail", args=[s.pk])), '<p class="disclaimer near">')
        plain = Source.objects.get(title__startswith="Introductory Mycology")
        self.assertNotContains(self.client.get(reverse("characters:source_detail", args=[plain.pk])), '<p class="disclaimer near">')


class LanguageTests(TestCase):
    """Interface language choice and translating the character data (docs/I18N_PLAN.md)."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", email="alice@example.org", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", email="bob@example.org", password="pw-bob-123")

    def test_unpublished_language_is_not_picked_from_the_browser(self):
        r = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(r, '<html lang="en"')

    def test_visitor_can_preview_a_language_being_translated(self):
        self.client.post(reverse("set_language"), {"language": "es", "next": "/"})
        self.assertContains(self.client.get("/"), '<html lang="es"')

    def test_published_language_is_picked_from_the_browser(self):
        from django.test import override_settings
        with override_settings(PUBLISHED_LANGUAGES=["en", "es"]):
            self.assertContains(self.client.get("/", HTTP_ACCEPT_LANGUAGE="es-MX,es;q=0.9"), '<html lang="es"')

    def test_languages_page_lists_progress_and_previews(self):
        r = self.client.get(reverse("characters:languages"))
        for name in ["Español", "ไทย", "Português (Brasil)", "Français"]:
            self.assertContains(r, name)
        self.assertContains(r, "/747)")
        self.assertContains(r, 'name="language" value="th"')

    def translate_cap_width(self, user, name, definition=""):
        self.client.force_login(user)
        c = Character.objects.get(code="FCC00019")
        return self.client.post(reverse("characters:translate", args=["FCC00019"]), {
            "lang": "es", f"MrCharacter-{c.pk}-name": name, f"MrCharacter-{c.pk}-definition": definition,
            "reason": "traducción", "then": "stay"})

    def test_translating_a_character(self):
        r = self.translate_cap_width(self.alice, "Anchura del sombrero", "Diámetro del píleo")
        self.assertEqual(r.status_code, 302)
        c = Character.objects.get(code="FCC00019")
        label = Label.objects.get(labelable_type="MrCharacter", labelable_id=c.pk, language="es", label_type="name")
        self.assertEqual(label.text, "Anchura del sombrero")
        self.assertEqual(ItemMeta.objects.get(item_type="Label", item_id=label.pk).created_by, self.alice)
        self.assertEqual(label.history.first().history_user, self.alice)
        # Shown to Spanish readers, with the English name kept below.
        self.client.post(reverse("set_language"), {"language": "es", "next": "/"})
        r = self.client.get("/id/FCC00019")
        self.assertContains(r, "<h1>Anchura del sombrero</h1>", html=True)
        self.assertContains(r, '<p class="tagline" lang="en">Cap Width</p>', html=True)
        # Not shown in English.
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        self.assertContains(self.client.get("/id/FCC00019"), "<h1>Cap Width</h1>", html=True)

    def test_others_cannot_overwrite_a_translation_but_admin_can(self):
        self.translate_cap_width(self.alice, "Anchura del sombrero")
        self.translate_cap_width(self.bob, "Ancho del píleo")
        c = Character.objects.get(code="FCC00019")
        get = lambda: Label.objects.get(labelable_type="MrCharacter", labelable_id=c.pk, language="es", label_type="name").text
        self.assertEqual(get(), "Anchura del sombrero")
        self.translate_cap_width(make_admin(), "Ancho del sombrero")
        self.assertEqual(get(), "Ancho del sombrero")

    def test_next_character_to_translate(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse("characters:translate_next", args=["fr"]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/translate/?lang=fr", r["Location"])
        self.assertEqual(self.client.get(r["Location"]).status_code, 200)
        self.assertEqual(self.client.get(reverse("characters:translate_next", args=["xx"])).status_code, 404)

    def test_translation_files_cover_every_language(self):
        from django.conf import settings
        for code, _name in settings.LANGUAGES:
            if code == "en":
                continue
            d = {"pt-br": "pt_BR"}.get(code, code)
            self.assertTrue((settings.BASE_DIR / "locale" / d / "LC_MESSAGES" / "django.po").exists(), code)
