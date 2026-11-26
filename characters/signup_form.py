"""allauth's sign-up form with the agreement checkbox moved last, just above the Sign Up button.

Its own module: allauth's form imports ACCOUNT_SIGNUP_FORM_CLASS (characters.forms), so it cannot live there.
"""
from allauth.account.forms import SignupForm


class SiteSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "agree" in self.fields:
            self.order_fields([name for name in self.fields if name != "agree"] + ["agree"])
