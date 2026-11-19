def login_legal_notice(request):
    """Expose the post-login legal notice once, on the first rendered page."""
    return {"show_supreme_court_notice": request.session.pop("show_supreme_court_notice", False)}
