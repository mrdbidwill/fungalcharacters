"""Error reports to the admin never contain passwords, one-time codes or keys (privacy page, "Where it is kept").

Django hides submitted fields only on views marked with sensitive_post_parameters; this filter hides any field whose
name looks secret, on every page.
"""
import re

from django.views.debug import SafeExceptionReporterFilter

SECRET_FIELD = re.compile(r"pass|code|token|secret|key|otp|recovery", re.IGNORECASE)


class HideSecretsFilter(SafeExceptionReporterFilter):
    def get_post_parameters(self, request):
        params = super().get_post_parameters(request)
        if request is None or not params:
            return params
        cleansed = params.copy()
        for name in list(cleansed.keys()):
            if SECRET_FIELD.search(name):
                cleansed[name] = self.cleansed_substitute
        return cleansed
