"""Tests run against a database built by the migrations, which load release 1.0.0."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Consent, CHARACTER_TYPE, Character, CharacterFungusType, CodeCounter, DisplayOption, ItemMeta, Label,
    Source, ValueOption,
)

User = get_user_model()


def make_admin(username="will"):
    """A superuser with two-factor sign-in on (the site requires it for the admin)."""
    from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
    admin = User.objects.create_superuser(username, email=f"{username}@example.org", password="pw-admin-123")
    TOTP.activate(admin, generate_totp_secret())
    Consent.record(admin)
    return admin


def contributor(username):
    """A user who has agreed to the contribution terms."""
    u = User.objects.create_user(username, email=f"{username}@example.org", password=f"pw-{username}-123")
    Consent.record(u)
    return u


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
        self.alice = contributor("alice")
        self.bob = contributor("bob")
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
            "password1": "a-long-pass-987", "password2": "a-long-pass-987", "agree": "on"})

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
        u = contributor("erin")
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
        self.alice = contributor("alice")
        self.bob = contributor("bob")

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


class HostedPageTests(TestCase):
    """Brian Hunt's page, kept at the same path it had on mrdbid.com (characters/hosted.py)."""

    def test_page_served_unchanged_with_bar_and_disclaimer(self):
        from django.conf import settings
        r = self.client.get("/documents/lumen-granuli-praecisi/")
        self.assertEqual(r.status_code, 200)
        body = r.content
        original = (settings.BASE_DIR / "hosted" / "lumen_granuli_praecisi_v1_0" / "lumen_granuli_praecisi_v1_0.html").read_bytes()
        inner = original[original.index(b">", original.index(b"<body")) + 1:original.rindex(b"</body")]
        self.assertIn(inner, body)                                  # author's content byte for byte
        self.assertEqual(body.count(b"No advice about consumption."), 2)  # top and bottom

    def test_images_and_safety(self):
        self.assertEqual(self.client.get("/documents/lumen-granuli-praecisi/images_web/parts.jpg").status_code, 200)
        self.assertEqual(self.client.get("/documents/lumen-granuli-praecisi/images_web/missing.jpg").status_code, 404)
        self.assertEqual(self.client.get("/documents/lumen-granuli-praecisi/images_web/settings.py").status_code, 404)
        self.assertEqual(self.client.get("/documents/other/").status_code, 404)

    def test_thanks_card_links_to_page(self):
        r = self.client.get("/thanks/")
        self.assertContains(r, 'href="/documents/lumen-granuli-praecisi/"')
        self.assertContains(r, "Brian Hunt")


def recently_signed_in(client, user):
    """Mark the session as having just confirmed the password again (allauth requires it before deleting an account)."""
    import time
    session = client.session
    session["account_authentication_methods"] = [{"method": "password", "at": time.time(), "username": user.username,
                                                   "reauthenticated": True}]
    session["account_authentication_methods_user"] = str(user.pk)
    session.save()


class ContributionsAndPrivacyTests(TestCase):
    def test_signup_requires_agreement_and_records_it(self):
        data = {"username": "fay", "email": "fay@example.org", "password1": "a-long-pass-987", "password2": "a-long-pass-987"}
        r = self.client.post(reverse("account_signup"), data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="fay").exists())
        self.client.post(reverse("account_signup"), {**data, "agree": "on"})
        fay = User.objects.get(username="fay")
        self.assertTrue(Consent.has_current(fay))

    def test_existing_user_agrees_once_before_adding(self):
        u = User.objects.create_user("gus", email="gus@example.org", password="pw-gus-12345")
        self.client.force_login(u)
        r = self.client.get(reverse("characters:create"))
        self.assertRedirects(r, reverse("characters:agree") + "?next=" + reverse("characters:create"))
        self.assertContains(self.client.post(reverse("characters:agree"), {"next": "/characters/new/"}), "This field is required")
        r = self.client.post(reverse("characters:agree"), {"agree": "on", "next": "/characters/new/"})
        self.assertRedirects(r, "/characters/new/")
        self.assertEqual(self.client.get(reverse("characters:create")).status_code, 200)

    def test_privacy_page_and_links(self):
        r = self.client.get(reverse("characters:privacy"))
        self.assertContains(r, "contact@fungalcharacters.org")
        self.assertContains(r, "14 days")
        self.assertContains(self.client.get("/"), 'href="/privacy/"')

    def test_delete_account_keeps_contributions(self):
        from allauth.account.models import EmailAddress
        u = contributor("hal")
        EmailAddress.objects.create(user=u, email="hal@example.org", verified=True, primary=True)
        self.client.force_login(u)
        self.client.post(reverse("characters:create"), {"name": "Hal Test Character"})
        c = Character.objects.get(name="Hal Test Character")
        recently_signed_in(self.client, u)
        r = self.client.post(reverse("characters:delete_account"), {"confirm": "delete"})
        self.assertRedirects(r, reverse("characters:home"))
        u.refresh_from_db()
        self.assertEqual(u.username, f"former-contributor-{u.pk}")
        self.assertEqual(u.email, "")
        self.assertFalse(u.is_active or u.has_usable_password())
        self.assertFalse(EmailAddress.objects.filter(user=u).exists())
        self.assertEqual(ItemMeta.objects.get(item_type=CHARACTER_TYPE, item_id=c.pk).created_by, u)
        self.assertContains(self.client.get(c.get_absolute_url()), f"former-contributor-{u.pk}")

    def test_admin_cannot_delete_own_account_here(self):
        admin = make_admin("root2")
        self.client.force_login(admin)
        recently_signed_in(self.client, admin)
        self.client.post(reverse("characters:delete_account"), {"confirm": "delete"})
        admin.refresh_from_db()
        self.assertEqual(admin.username, "root2")


class ErrorReportTests(TestCase):
    def test_secret_fields_hidden_in_error_reports(self):
        from django.test import RequestFactory
        from .reporting import HideSecretsFilter
        req = RequestFactory().post("/accounts/password/reset/key/x/", {"password1": "hunter2", "code": "123456", "name": "Cap"})
        params = HideSecretsFilter().get_post_parameters(req)
        self.assertNotEqual(params["password1"], "hunter2")
        self.assertNotEqual(params["code"], "123456")
        self.assertEqual(params["name"], "Cap")


class NeedsReviewTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def report(self, kind="character", pk=None, note="Definition is wrong", **extra):
        pk = pk or Character.objects.get(code="FCC00019").pk
        return self.client.post(reverse("characters:review_request", args=[kind, pk]), {"note": note}, **extra)

    def test_anyone_can_report(self):
        from .models import ReviewRequest
        r = self.report()
        self.assertRedirects(r, "/id/FCC00019")
        rr = ReviewRequest.objects.get()
        self.assertEqual((rr.note, rr.reporter, rr.resolved, rr.page), ("Definition is wrong", None, False, "/id/FCC00019"))
        self.assertIn("FCC00019", rr.item_label)
        self.assertContains(self.client.get("/id/FCC00019"), "Needs review")

    def test_hidden_rate_limit(self):
        from .models import ReviewRequest
        for i in range(7):
            r = self.report(note=f"report {i}", REMOTE_ADDR="198.51.100.9")
            self.assertEqual(r.status_code, 302)
        self.assertEqual(ReviewRequest.objects.count(), 5)          # 6th and 7th silently dropped
        self.report(note="other visitor", REMOTE_ADDR="198.51.100.10")
        self.assertEqual(ReviewRequest.objects.count(), 6)

    def test_signed_in_report_records_user_and_admin_sees_list(self):
        from .models import ReviewRequest
        u = contributor("ivy")
        self.client.force_login(u)
        self.report(kind="source", pk=Source.objects.first().pk)
        self.assertEqual(ReviewRequest.objects.get().reporter, u)
        self.client.force_login(make_admin())
        self.assertContains(self.client.get(reverse("characters:account")), "1 open “Needs review” report")
        r = self.client.get(reverse("admin:characters_reviewrequest_changelist"))
        self.assertContains(r, "Definition is wrong")

    def test_hidden_items_cannot_be_reported(self):
        c = Character.objects.get(code="FCC00019")
        ItemMeta.objects.create(item_type=CHARACTER_TYPE, item_id=c.pk, is_hidden=True)
        self.assertEqual(self.report().status_code, 404)


class ReleaseBuildTests(TestCase):
    """make_release: dated releases from the live tables (characters/release.py, docs/RELEASING.md)."""

    def build(self, version="9.9.9"):
        import tempfile
        from pathlib import Path
        from .release import build_release
        out = Path(tempfile.mkdtemp())
        summary = build_release(version, "2026-11-26", "Test notes.", out_root=out)
        return out / version, summary

    def test_release_has_every_format_and_the_same_structure(self):
        import json
        from django.conf import settings
        folder, summary = self.build()
        for name in ["fungal_characters_v9.9.9.xlsx", "fungal_characters_v9.9.9.json", "fungal_characters_v9.9.9.sql",
                     "fungal_characters_v9.9.9_postgresql.sql", "fungal_characters_v9.9.9_skos.ttl",
                     "fungal_characters_v9.9.9_sdd.xml", "README.md", "CHANGELOG.md",
                     "csv/characters_flat.csv", "csv/value_options_flat.csv", "csv/mr_characters.csv"]:
            self.assertTrue((folder / name).exists(), name)
        self.assertEqual((summary["characters"], summary["value_options"]), (747, 590))
        doc = json.loads((folder / "fungal_characters_v9.9.9.json").read_text())
        self.assertEqual(doc["license"], "CC0 1.0")
        self.assertIn("value_options", doc["characters"][0])
        # Table definitions copied word for word from the previous release.
        old = (settings.BASE_DIR / "data/releases/1.0.0/fungal_characters_v1.0.0_postgresql.sql").read_text()
        new = (folder / "fungal_characters_v9.9.9_postgresql.sql").read_text()
        ddl = lambda s: [l for l in s.split("\n") if l.startswith(("CREATE", "COMMENT", "  ", ");")) and not l.startswith("  (")]
        self.assertEqual(ddl(new), ddl(old))
        self.assertIn("INSERT INTO releases", new)
        self.assertIn("'9.9.9'", new)
        changelog = (folder / "CHANGELOG.md").read_text()
        self.assertIn("## 9.9.9 — 2026-11-26", changelog)
        self.assertIn("## 1.0.0", changelog)
        self.assertIn("value_options_flat.csv (was values_flat.csv)", changelog)

    def test_hidden_items_are_left_out(self):
        c = Character.objects.get(code="FCC00082")
        n_values = c.value_options.count()
        ItemMeta.objects.create(item_type=CHARACTER_TYPE, item_id=c.pk, is_hidden=True)
        folder, summary = self.build()
        self.assertEqual(summary["characters"], 746)
        self.assertEqual(summary["value_options"], 590 - n_values)
        self.assertNotIn("FCC00082", (folder / "fungal_characters_v9.9.9_postgresql.sql").read_text())
        self.assertEqual(summary["diff"]["chars_removed"], ["FCC00082"])

    def test_translations_and_new_items_are_included(self):
        u = contributor("jo")
        self.client.force_login(u)
        self.client.post(reverse("characters:create"), {"name": "Release Test Character"})
        c = Character.objects.get(code="FCC00019")
        self.client.post(reverse("characters:translate", args=["FCC00019"]), {
            "lang": "es", f"MrCharacter-{c.pk}-name": "Anchura del sombrero", f"MrCharacter-{c.pk}-definition": "", "then": "stay"})
        folder, summary = self.build()
        self.assertEqual(summary["diff"]["chars_added"], ["FCC00748"])
        self.assertEqual(summary["diff"]["translated_names"], {"es": 1})
        self.assertIn("Anchura del sombrero", (folder / "fungal_characters_v9.9.9.json").read_text())

    def test_command_records_only_when_asked(self):
        import tempfile
        from django.core.management import call_command
        from .models import Release
        call_command("make_release", "9.9.8", "--date", "2026-11-26", "--out", tempfile.mkdtemp(), stdout=__import__("io").StringIO())
        self.assertFalse(Release.objects.filter(version="9.9.8").exists())
        call_command("make_release", "9.9.8", "--date", "2026-11-26", "--record-only", stdout=__import__("io").StringIO())
        self.assertTrue(Release.objects.filter(version="9.9.8").exists())


class ApiTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_character_list_and_paging(self):
        r = self.client.get("/api/v1/characters/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        d = r.json()
        self.assertEqual((d["count"], d["license"], len(d["results"])), (747, "CC0 1.0", 100))
        self.assertIn("page=2", d["next"])
        self.assertEqual(self.client.get("/api/v1/characters/?q=pileus width").json()["results"][0]["code"], "FCC00019")

    def test_one_character_with_value_options(self):
        d = self.client.get("/api/v1/characters/FCC00082").json()
        self.assertEqual((d["name"], d["scientific_name"], len(d["value_options"])), ("Gill Attachment", "Lamellae Attachment", 16))
        self.assertTrue(d["value_options"][0]["code"].startswith("FCV"))
        v = self.client.get(f"/api/v1/value-options/{d['value_options'][0]['code']}").json()
        self.assertEqual(v["character"]["code"], "FCC00082")

    def test_hidden_items_absent_and_errors(self):
        c = Character.objects.get(code="FCC00019")
        ItemMeta.objects.create(item_type=CHARACTER_TYPE, item_id=c.pk, is_hidden=True)
        self.assertEqual(self.client.get("/api/v1/characters/FCC00019").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/characters/").json()["count"], 746)
        self.assertEqual(self.client.get("/api/v1/characters/?updated_since=yesterday").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/characters/").status_code, 405)

    def test_fair_use_limit(self):
        from . import api
        old = api.API_LIMIT_PER_MINUTE
        api.API_LIMIT_PER_MINUTE = 3
        try:
            codes = [self.client.get("/api/v1/releases/").status_code for _ in range(5)]
        finally:
            api.API_LIMIT_PER_MINUTE = old
        self.assertEqual(codes, [200, 200, 200, 429, 429])

    def test_api_page(self):
        self.assertContains(self.client.get("/api/"), "/api/v1/characters/FCC00019")


class AntiBotTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def data(self, n, **extra):
        return {"username": f"user{n}", "email": f"user{n}@example.org", "password1": "a-long-pass-987",
                "password2": "a-long-pass-987", "agree": "on", **extra}

    def test_honeypot_fakes_success_without_account_or_email(self):
        from django.core import mail
        r = self.client.post(reverse("account_signup"), self.data(1, website="http://spam.example"))
        self.assertEqual(r.status_code, 302)                     # looks like "check your email"
        self.assertFalse(User.objects.filter(username="user1").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_honeypot_hidden_from_people(self):
        r = self.client.get(reverse("account_signup"))
        self.assertContains(r, 'name="website"')
        css = (__import__("django.conf", fromlist=["settings"]).settings.BASE_DIR / "characters/static/characters/site.css").read_text()
        self.assertIn('#id_website, label[for="id_website"], p:has(> #id_website) { display: none !important; }', css)
        r = self.client.post(reverse("account_signup"), self.data(2))   # a person leaves it empty
        self.assertTrue(User.objects.filter(username="user2").exists())

    def test_signup_rate_limit(self):
        codes = [self.client.post(reverse("account_signup"), self.data(10 + i)).status_code for i in range(6)]
        self.assertEqual(codes[:5], [302] * 5)
        self.assertEqual(codes[5], 429)

    def test_password_reset_rate_limit_per_email(self):
        codes = [self.client.post(reverse("account_reset_password"), {"email": "someone@example.org"}).status_code for _ in range(4)]
        self.assertEqual(codes[3], 429)


class RobotsTests(TestCase):
    def test_robots_txt(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r["Content-Type"], "text/plain; charset=utf-8")
        body = r.content.decode()
        for path in ["/accounts/", "/names/", "/review/", "/api/v1/", "/*/edit/"]:
            self.assertIn(f"Disallow: {path}", body)
        for open_path in ["/characters/\n", "/id/", "/downloads/", "/api/\n"]:
            self.assertNotIn(f"Disallow: {open_path}", body)


class HomeAndListTweaksTests(TestCase):
    def test_home_wording_and_single_disclaimer_pair(self):
        r = self.client.get("/")
        self.assertContains(r, "Mention on the")
        self.assertNotContains(r, "Thanks on the")
        self.assertEqual(r.content.decode().count("No advice about consumption"), 2)   # top and bottom only

    def test_list_intro_and_page_size(self):
        r = self.client.get("/characters/")
        self.assertContains(r, "be alarmed by the chemical names")
        self.assertContains(r, "Page 1 of 15")

    def test_agreement_checkbox_comes_last(self):
        body = self.client.get(reverse("account_signup")).content.decode()
        self.assertGreater(body.index('name="agree"'), body.index('name="password2"'))

    def test_visited_buttons_keep_light_text(self):
        from django.conf import settings
        css = (settings.BASE_DIR / "characters/static/characters/site.css").read_text()
        self.assertIn(".button:link, .button:visited { color: var(--on-primary); }", css)


class AccessibilityPageTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_page_and_links_everywhere(self):
        r = self.client.get("/accessibility/?from=/characters/")
        self.assertContains(r, 'value="/characters/"')
        self.assertContains(r, "contact@fungalcharacters.org")
        self.assertContains(r, "We are not accessibility experts")
        for url in ["/", "/characters/", "/id/FCC00019", "/accounts/signup/"]:
            body = self.client.get(url).content.decode()
            self.assertIn('class="skip" href="/accessibility/?from=', body, url)
            self.assertLess(body.index("Skip to content"), body.index("Accessibility help"), url)

    def test_report_saved_without_account(self):
        from .models import ReviewRequest
        r = self.client.post("/accessibility/", {"kind": "help", "page": "/id/FCC00082", "tech": "screen reader",
                                                 "note": "The table is hard to follow."})
        self.assertRedirects(r, "/accessibility/#report")
        rr = ReviewRequest.objects.get()
        self.assertEqual((rr.item_type, rr.item_label, rr.page, rr.reporter),
                         ("Accessibility", "Accessibility help (screen reader)", "/id/FCC00082", None))

    def test_empty_message_and_foreign_page_refused(self):
        from .models import ReviewRequest
        r = self.client.post("/accessibility/", {"kind": "problem", "page": "https://evil.example/", "note": ""})
        self.assertContains(r, "Please write a few words")
        self.client.post("/accessibility/", {"kind": "problem", "page": "https://evil.example/", "note": "x", "tech": "bogus"})
        rr = ReviewRequest.objects.get()
        self.assertEqual((rr.page, rr.item_label), ("/", "Accessibility problem"))


class SearchEngineTests(TestCase):
    def test_sitemap_and_robots(self):
        r = self.client.get("/sitemap.xml")
        body = r.content.decode()
        self.assertIn("<loc>https://fungalcharacters.org/id/FCC00019</loc>", body)
        self.assertIn("<loc>https://fungalcharacters.org/downloads/</loc>", body)
        self.assertNotIn("/accounts/", body)
        c = Character.objects.get(code="FCC00082")
        ItemMeta.objects.create(item_type=CHARACTER_TYPE, item_id=c.pk, is_hidden=True)
        self.assertNotIn("/id/FCC00082<", self.client.get("/sitemap.xml").content.decode())
        self.assertIn("Sitemap: https://fungalcharacters.org/sitemap.xml", self.client.get("/robots.txt").content.decode())

    def test_character_page_head(self):
        import json, re
        body = self.client.get("/id/FCC00019").content.decode()
        self.assertIn("<title>Cap Width (Pileus Width) — FCC00019 · Fungal Characters</title>", body)
        self.assertIn('<link rel="canonical" href="https://fungalcharacters.org/id/FCC00019">', body)
        desc = re.search(r'<meta name="description" content="(.*?)">', body).group(1)
        self.assertIn("pileus/pilei. Part: Cap.", desc)
        self.assertLessEqual(len(desc), 200)
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S).group(1))
        self.assertEqual((data["@type"], data["termCode"], data["alternateName"]), ("DefinedTerm", "FCC00019", "Pileus Width"))
        self.assertIn('property="og:image"', body)
        self.assertIn("More characters for Cap", body)

    def test_dataset_on_downloads_and_noindex_searches(self):
        import json, re
        body = self.client.get("/downloads/").content.decode()
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S).group(1))
        self.assertEqual((data["@type"], data["license"]), ("Dataset", "https://creativecommons.org/publicdomain/zero/1.0/"))
        self.assertTrue(data["distribution"])
        self.assertIn('content="noindex, follow"', self.client.get("/characters/?q=cap").content.decode())
        self.assertNotIn('name="robots"', self.client.get("/characters/").content.decode())

    def test_structured_data_cannot_break_out_of_script(self):
        from .seo import jsonld
        self.assertNotIn("</script><", str(jsonld({"x": "</script><script>alert(1)</script>"}))[:-9])


class ValueTypeNameTests(TestCase):
    def setUp(self):
        from django.core.management import call_command
        self.admin = make_admin()
        call_command("name_value_types", "--as", "will", stdout=__import__("io").StringIO())

    def test_display_names_shown_keys_kept(self):
        vt = DisplayOption.objects.get(name="text_box_number_mm")
        self.assertEqual(str(vt), "Number (mm)")
        self.assertTrue(DisplayOption.objects.filter(name="drop_down").exists())
        self.assertFalse(DisplayOption.objects.filter(name="drop-down").exists())
        body = self.client.get("/id/FCC00019").content.decode()
        self.assertIn(">Number (mm)</a>", body)
        self.assertIn("Value type: Number (mm).", body)
        r = self.client.get(f"/value-types/{vt.pk}/")
        self.assertContains(r, "<code>text_box_number_mm</code>", html=True)
        self.assertEqual(self.client.get("/api/v1/characters/FCC00019").json()["value_type_label"], "Number (mm)")
        h = Label.history.filter(labelable_type="DisplayOption", labelable_id=vt.pk).first()
        self.assertEqual((h.history_user, h.history_change_reason), (self.admin, "Readable value type names (Will, 2026-11-27)"))

    def test_new_value_type_gets_key_and_edits_keep_it(self):
        u = contributor("kim")
        self.client.force_login(u)
        self.client.post(reverse("characters:value_type_create"), {"label_text": "Length range (mm)"})
        vt = DisplayOption.objects.get(name="length_range_mm")
        self.assertEqual(str(vt), "Length range (mm)")
        r = self.client.post(reverse("characters:value_type_edit", args=[vt.pk]), {"label_text": "Range (mm)"})
        self.assertContains(r, "Similar names already exist")          # close to "Range (µm)"
        self.client.post(reverse("characters:value_type_edit", args=[vt.pk]), {"label_text": "Range (mm)", "confirm_similar": "on"})
        vt = DisplayOption.objects.get(pk=vt.pk)
        self.assertEqual((vt.name, str(vt)), ("length_range_mm", "Range (mm)"))
        self.assertContains(self.client.post(reverse("characters:value_type_create"), {"label_text": "number (MM)"}), "Already exists")

    def test_release_carries_key_and_display_name(self):
        import json, tempfile
        from pathlib import Path
        from .release import build_release
        out = Path(tempfile.mkdtemp())
        build_release("9.9.7", "2026-11-27", "", out_root=out)
        doc = json.loads((out / "9.9.7/fungal_characters_v9.9.7.json").read_text())
        cap = next(c for c in doc["characters"] if c["code"] == "FCC00019")
        self.assertEqual((cap["value_type"], cap["value_type_label"]), ("text_box_number_mm", "Number (mm)"))
        self.assertIn({"id": DisplayOption.objects.get(name="radio").pk, "key": "radio"}.items() <= next(v for v in doc["value_types"] if v["key"] == "radio").items(), [True])
        changelog = (out / "9.9.7/CHANGELOG.md").read_text()
        self.assertIn("Value type keys renamed: drop-down → drop_down.", changelog)
        self.assertIn("Value types now have display names", changelog)
        self.assertIn("value_type_label", (out / "9.9.7/csv/characters_flat.csv").read_text(encoding="utf-8-sig").split("\n")[0])


class SiteVerificationTests(TestCase):
    def test_bing_meta_tag_on_home_page(self):
        self.assertContains(self.client.get("/"), '<meta name="msvalidate.01" content="0C05660B5F5CD5F88D6752F9599D14B0">', html=True)

    def test_bing_xml_file(self):
        r = self.client.get("/BingSiteAuth.xml")
        self.assertEqual(r["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn("<user>0C05660B5F5CD5F88D6752F9599D14B0</user>", r.content.decode())


class ReleaseDoiTests(TestCase):
    def test_doi_shown_when_known(self):
        from django.test import override_settings
        self.assertNotContains(self.client.get("/downloads/"), "doi.org")
        with override_settings(RELEASE_DOIS={"1.0.0": "10.5281/zenodo.123"}):
            r = self.client.get("/downloads/")
            self.assertContains(r, "https://doi.org/10.5281/zenodo.123")
            self.assertContains(r, '"identifier":"https://doi.org/10.5281/zenodo.123"')
